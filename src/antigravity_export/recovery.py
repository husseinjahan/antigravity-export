"""
Engine for recovering lost, interrupted, or unindexed Antigravity conversations after crashes/updates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from antigravity_export.api_client import LanguageServerClient
from antigravity_export.config import AntigravityConfig
from antigravity_export.models import Conversation
from antigravity_export.parser import StepParser
from antigravity_export.storage import StorageReader

logger = logging.getLogger(__name__)


@dataclass
class RecoveryReport:
    """Diagnostic report of the recovery operation."""

    crash_logs_found: list[dict[str, Any]] = field(default_factory=list)
    unindexed_conversations: list[str] = field(default_factory=list)
    recovered_conversations: list[Conversation] = field(default_factory=list)
    failed_conversations: list[tuple[str, str]] = field(default_factory=list)
    ls_reloads_triggered: int = 0
    offline_recoveries: int = 0

    def summary(self) -> str:
        lines = [
            "========================================",
            "   CONVERSATION RECOVERY SUMMARY",
            "========================================",
            f"Crash logs analyzed:         {len(self.crash_logs_found)}",
            f"Unindexed sessions detected: {len(self.unindexed_conversations)}",
            f"Successfully recovered:      {len(self.recovered_conversations)}",
            f"  - via Language Server:     {self.ls_reloads_triggered}",
            f"  - via Offline Transcripts: {self.offline_recoveries}",
        ]
        if self.failed_conversations:
            lines.append(f"Incomplete/Dump-only files:  {len(self.failed_conversations)}")
        lines.append("========================================")
        return "\n".join(lines)


class ConversationRecovery:
    """Recovers conversations lost or corrupted after IDE/LanguageServer crashes or software updates."""

    def __init__(
        self,
        config: Optional[AntigravityConfig] = None,
        client: Optional[LanguageServerClient] = None,
    ):
        self.config = config or AntigravityConfig()
        self.storage = StorageReader(self.config)
        self.client = client or LanguageServerClient(config=self.config)
        self.parser = StepParser(include_thinking=True, include_full=True)

    def scan_lost_conversations(
        self,
        active_ids: Optional[set[str]] = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Identify conversations that exist on disk but are not currently active/indexed in the Language Server.

        Returns:
            (crash_logs, lost_conversation_ids)
        """
        crashes = self.storage.get_crashed_conversation_ids()
        all_disk_ids = self.storage.get_all_storage_conversation_ids()

        active = active_ids or set()
        lost_ids = []

        # Any valid conversation on disk that is not currently active
        for cid in sorted(all_disk_ids):
            if cid not in active and cid not in lost_ids:
                lost_ids.append(cid)

        return crashes, lost_ids

    def recover_conversation(
        self,
        conversation_id: str,
        endpoint: Optional[dict[str, Any]] = None,
        force_offline: bool = False,
    ) -> Optional[Conversation]:
        """Recover a conversation by requesting it from the LS or reading directly from disk logs."""
        raw_steps: list[dict[str, Any]] = []
        source_mode = "offline"

        # 1. Attempt recovery via Language Server API (if endpoint is provided and not forced offline)
        if endpoint and not force_offline:
            try:
                p, token = endpoint["port"], endpoint["csrf_token"]
                steps = self.client.get_trajectory_steps(conversation_id, step_count=2000, port=p, csrf_token=token)
                if steps:
                    raw_steps = steps
                    source_mode = "ls"
            except Exception as e:
                logger.debug(f"LS recovery failed for {conversation_id}: {e}")

        # 2. Fallback to direct offline storage reading (transcripts & brain logs)
        if not raw_steps:
            raw_steps = self.storage.read_brain_transcript(conversation_id)
            source_mode = "offline"

        if not raw_steps:
            return None

        # Parse messages and file changes
        messages = self.parser.parse_steps(raw_steps)
        if not messages:
            return None

        # Fetch metadata from SQLite if available
        meta = self.storage.get_conversation_from_db(conversation_id) or {}
        title = meta.get("summary") or f"Recovered Conversation ({conversation_id[:8]})"
        workspace_uris = meta.get("workspace_uris") or []
        created_time = meta.get("createdTime") or (messages[0].timestamp if messages else None)
        last_modified = meta.get("lastModifiedTime") or (messages[-1].timestamp if messages else None)
        status = meta.get("status") or "RECOVERED"
        step_count = len(raw_steps)

        conv = Conversation(
            conversation_id=conversation_id,
            title=title,
            project_name=Conversation.extract_project_name(workspace_uris),
            workspace_uris=workspace_uris,
            created_time=created_time,
            last_modified_time=last_modified,
            status=status,
            step_count=step_count,
            messages=messages,
            is_recovered=True,
            raw_metadata={"source_mode": source_mode, **meta},
        )
        conv.aggregate_file_changes()
        return conv

    def run_recovery(
        self,
        endpoints: Optional[list[dict[str, Any]]] = None,
        dry_run: bool = False,
        force_offline: bool = False,
    ) -> RecoveryReport:
        """Execute full recovery scanning, re-indexing, and restoration."""
        report = RecoveryReport()

        active_ids = set()
        primary_endpoint = None

        if endpoints and not force_offline:
            primary_endpoint = endpoints[0]
            summaries, _, _ = self.client.get_all_trajectories_merged(endpoints)
            active_ids = set(summaries.keys())

        crash_logs, lost_ids = self.scan_lost_conversations(active_ids)
        report.crash_logs_found = crash_logs
        report.unindexed_conversations = lost_ids

        if dry_run:
            return report

        for cid in lost_ids:
            try:
                conv = self.recover_conversation(
                    cid,
                    endpoint=primary_endpoint,
                    force_offline=force_offline,
                )
                if conv:
                    report.recovered_conversations.append(conv)
                    if conv.raw_metadata.get("source_mode") == "ls":
                        report.ls_reloads_triggered += 1
                    else:
                        report.offline_recoveries += 1
                else:
                    report.failed_conversations.append((cid, "No recoverable steps or transcript found"))
            except Exception as e:
                report.failed_conversations.append((cid, str(e)))

        return report
