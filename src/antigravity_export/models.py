"""
Domain data models for Antigravity conversations, messages, file changes, and status.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname


def normalize_file_path(path_val: Any) -> str:
    """Normalize a raw file path or URI (str or dict wrapper) into a clean, platform-friendly file path string."""
    if not path_val:
        return ""

    while isinstance(path_val, dict):
        next_val = (
            path_val.get("absoluteUri")
            or path_val.get("uri")
            or path_val.get("filePath")
            or path_val.get("path")
            or path_val.get("filename")
            or path_val.get("file")
            or path_val.get("createFile")
        )
        if not next_val:
            for v in path_val.values():
                if isinstance(v, (dict, str)):
                    res = normalize_file_path(v)
                    if res:
                        return res
            break
        path_val = next_val

    if not isinstance(path_val, str):
        path_val = str(path_val) if path_val is not None else ""

    path_val = path_val.strip()
    if not path_val:
        return ""

    # Handle file:// URIs (e.g. file:///d:/w/pay/... or file:///C:/...)
    if path_val.startswith("file://"):
        parsed = urlparse(path_val)
        raw_path = unquote(parsed.path)
        if parsed.netloc:
            raw_path = f"{parsed.netloc}{raw_path}"
        try:
            return url2pathname(raw_path)
        except Exception:
            if len(raw_path) >= 3 and raw_path[0] == "/" and raw_path[2] == ":":
                raw_path = raw_path[1:]
            return raw_path

    return path_val


@dataclass
class FileChange:
    """Represents a file addition, modification, or deletion tracked during agent execution."""

    path: str
    change_type: str = "modify"  # "create", "modify", "delete"
    unified_diff: Optional[str] = None
    target: Optional[str] = None
    replacement: Optional[str] = None
    content: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    timestamp: Optional[str] = None
    step_index: Optional[int] = None
    artifact_summary: Optional[str] = None

    def __post_init__(self) -> None:
        self.path = normalize_file_path(self.path)
        if not isinstance(self.change_type, str):
            self.change_type = str(self.change_type) if self.change_type is not None else "modify"

    def compute_stats(self) -> None:
        """Calculate additions and deletions from the unified diff if not set."""
        if self.unified_diff and (self.additions == 0 and self.deletions == 0):
            adds = 0
            dels = 0
            for line in str(self.unified_diff).splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    adds += 1
                elif line.startswith("-") and not line.startswith("---"):
                    dels += 1
            self.additions = adds
            self.deletions = dels

    def to_dict(self) -> dict[str, Any]:
        self.compute_stats()
        return dataclasses.asdict(self)


@dataclass
class ToolCall:
    """Represents an agent tool execution (file edits, bash commands, searches)."""

    name: str
    call_id: Optional[str] = None
    args: dict[str, Any] = field(default_factory=dict)
    output: Optional[str] = None
    status: Optional[str] = None
    exit_code: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class Message:
    """Represents a conversation turn (user prompt, assistant response, tool call, thinking)."""

    role: str  # "user", "assistant", "tool", "system"
    content: str = ""
    thinking: Optional[str] = None
    timestamp: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)
    step_index: Optional[int] = None
    model: Optional[str] = None
    stop_reason: Optional[str] = None
    thinking_duration: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "thinking": self.thinking,
            "timestamp": self.timestamp,
            "step_index": self.step_index,
            "model": self.model,
            "stop_reason": self.stop_reason,
            "thinking_duration": self.thinking_duration,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "file_changes": [fc.to_dict() for fc in self.file_changes],
        }


@dataclass
class Conversation:
    """Represents a complete conversation session within a workspace/project."""

    conversation_id: str
    title: str = "Untitled Conversation"
    project_name: str = "default"
    workspace_uris: list[str] = field(default_factory=list)
    created_time: Optional[str] = None
    last_modified_time: Optional[str] = None
    status: str = "UNKNOWN"
    step_count: int = 0
    messages: list[Message] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)
    is_recovered: bool = False
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def extract_project_name(cls, workspace_uris: list[str]) -> str:
        """Extract a readable project name from workspace URIs."""
        if not workspace_uris:
            return "default"
        uri = workspace_uris[0]
        # Decode URI (e.g. file:///c%3A/Projects/antigravity-export -> c:/Projects/antigravity-export)
        parsed = urlparse(uri)
        path = unquote(parsed.path)
        if parsed.netloc:
            # handle UNC or hostname
            path = f"{parsed.netloc}{path}"
        # Strip trailing slashes
        path = path.rstrip("/\\")
        if not path:
            return "default"
        # Take basename
        basename = path.replace("\\", "/").split("/")[-1]
        return basename or "default"

    def aggregate_file_changes(self) -> list[FileChange]:
        """Collect all file changes across messages into a unified list."""
        all_changes: list[FileChange] = []
        for msg in self.messages:
            for change in msg.file_changes:
                change.compute_stats()
                all_changes.append(change)
        self.file_changes = all_changes
        return all_changes

    def to_dict(self) -> dict[str, Any]:
        self.aggregate_file_changes()
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "project_name": self.project_name,
            "workspace_uris": self.workspace_uris,
            "created_time": self.created_time,
            "last_modified_time": self.last_modified_time,
            "status": self.status,
            "step_count": self.step_count,
            "is_recovered": self.is_recovered,
            "total_file_changes": len(self.file_changes),
            "file_changes": [fc.to_dict() for fc in self.file_changes],
            "messages": [m.to_dict() for m in self.messages],
        }


@dataclass
class ConnectionStatus:
    """Represents the current connection state of the Antigravity Language Server."""

    is_running: bool = False
    is_reachable: bool = False
    process_id: Optional[int] = None
    executable_path: Optional[str] = None
    csrf_token: Optional[str] = None
    port: Optional[int] = None
    ide_name: Optional[str] = None
    ide_version: Optional[str] = None
    endpoints: list[dict[str, Any]] = field(default_factory=list)
    active_conversations_count: int = 0
    total_stored_conversations: int = 0
    crashes_detected: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
