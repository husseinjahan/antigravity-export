"""
Direct storage reader for Antigravity SQLite databases, brain transcripts, and crash dumps.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from antigravity_export.config import AntigravityConfig
from antigravity_export.models import Conversation


class StorageReader:
    """Reads Antigravity conversation data directly from disk and SQLite databases."""

    def __init__(self, config: Optional[AntigravityConfig] = None):
        self.config = config or AntigravityConfig()

    def get_summaries_from_db(self) -> dict[str, dict[str, Any]]:
        """Read all conversation summaries from conversation_summaries.db."""
        summaries: dict[str, dict[str, Any]] = {}
        db_path = self.config.summaries_db
        if not db_path.is_file():
            return summaries

        try:
            # Open in read-only URI mode to avoid locking
            uri = f"file:{db_path.as_posix()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT conversation_id, title, preview, step_count, last_modified_time,
                           workspace_uris, status, project_id, agent_name, last_user_input_time
                    FROM conversation_summaries
                """)
                for row in cursor.fetchall():
                    cid = row["conversation_id"]
                    uris_raw = row["workspace_uris"] or "[]"
                    try:
                        workspace_uris = json.loads(uris_raw)
                    except Exception:
                        workspace_uris = [uris_raw] if uris_raw else []

                    summaries[cid] = {
                        "summary": row["title"],
                        "preview": row["preview"],
                        "stepCount": row["step_count"],
                        "lastModifiedTime": row["last_modified_time"],
                        "lastUserInputTime": row["last_user_input_time"],
                        "status": row["status"],
                        "workspace_uris": workspace_uris,
                        "project_id": row["project_id"],
                        "agent_name": row["agent_name"],
                    }
        except Exception:
            pass

        return summaries

    def get_conversation_from_db(self, conversation_id: str) -> Optional[dict[str, Any]]:
        """Read specific conversation metadata from conversation_summaries.db."""
        db_path = self.config.summaries_db
        if not db_path.is_file():
            return None

        try:
            uri = f"file:{db_path.as_posix()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT conversation_id, title, preview, step_count, last_modified_time,
                           workspace_uris, status, project_id, agent_name, last_user_input_time
                    FROM conversation_summaries
                    WHERE conversation_id = ?
                """, (conversation_id,))
                row = cursor.fetchone()
                if row:
                    uris_raw = row["workspace_uris"] or "[]"
                    try:
                        workspace_uris = json.loads(uris_raw)
                    except Exception:
                        workspace_uris = [uris_raw] if uris_raw else []

                    return {
                        "conversation_id": row["conversation_id"],
                        "summary": row["title"],
                        "preview": row["preview"],
                        "stepCount": row["step_count"],
                        "lastModifiedTime": row["last_modified_time"],
                        "lastUserInputTime": row["last_user_input_time"],
                        "status": row["status"],
                        "workspace_uris": workspace_uris,
                        "project_id": row["project_id"],
                        "agent_name": row["agent_name"],
                    }
        except Exception:
            pass
        return None

    def read_brain_transcript(self, conversation_id: str) -> list[dict[str, Any]]:
        """Read conversation steps directly from the brain transcript JSONL log."""
        steps: list[dict[str, Any]] = []
        brain_conv_dir = self.config.brain_dir / conversation_id / ".system_generated" / "logs"

        full_log = brain_conv_dir / "transcript_full.jsonl"
        compact_log = brain_conv_dir / "transcript.jsonl"

        target_file = full_log if full_log.is_file() else (compact_log if compact_log.is_file() else None)
        if not target_file:
            return steps

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            steps.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            pass

        return steps

    def get_crashed_conversation_ids(self) -> list[dict[str, Any]]:
        """Parse crash logs in ~/.gemini/antigravity/crashes to identify interrupted sessions."""
        crashes: list[dict[str, Any]] = []
        if not self.config.crashes_dir.is_dir():
            return crashes

        for crash_file in self.config.crashes_dir.glob("crash_*.log"):
            name = crash_file.stem  # crash_<pid>_<uuid>
            parts = name.split("_")
            if len(parts) >= 3:
                pid = parts[1]
                uuid = parts[2]
                crashes.append({
                    "file": crash_file.name,
                    "path": str(crash_file),
                    "pid": pid,
                    "conversation_id": uuid,
                    "modified_time": crash_file.stat().st_mtime,
                })
        return crashes

    def get_all_storage_conversation_ids(self) -> set[str]:
        """Collect all conversation IDs found anywhere across disk (conversations db/pb and brain dirs)."""
        ids: set[str] = set()

        # From conversation_summaries.db
        for cid in self.get_summaries_from_db().keys():
            ids.add(cid)

        # From conversations/*.db and *.pb
        if self.config.conversations_dir.is_dir():
            for f in self.config.conversations_dir.iterdir():
                if f.suffix in (".db", ".pb") and not f.name.endswith("-shm") and not f.name.endswith("-wal"):
                    ids.add(f.stem)

        # From brain/*
        if self.config.brain_dir.is_dir():
            for d in self.config.brain_dir.iterdir():
                if d.is_dir() and d.name != "tempmediaStorage":
                    ids.add(d.name)

        return ids
