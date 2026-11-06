"""
Configuration and system path discovery for Antigravity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class AntigravityConfig:
    """Manages paths and configuration for Antigravity environment."""

    BASE_SERVICE_PATH = "exa.language_server_pb.LanguageServerService"
    CONNECT_PROTOCOL_VERSION = "1"
    CSRF_HEADER_NAME = "X-Codeium-Csrf-Token"

    def __init__(self, app_data_dir: Optional[str | Path] = None):
        if app_data_dir:
            self.root = Path(app_data_dir).resolve()
        else:
            self.root = self._default_app_data_dir()

    @staticmethod
    def _default_app_data_dir() -> Path:
        """Resolve default ~/.gemini/antigravity directory."""
        return Path.home() / ".gemini" / "antigravity"

    @property
    def conversations_dir(self) -> Path:
        """Directory where individual conversation databases and state are stored."""
        return self.root / "conversations"

    @property
    def brain_dir(self) -> Path:
        """Directory where transcripts, artifacts, and execution logs reside."""
        return self.root / "brain"

    @property
    def crashes_dir(self) -> Path:
        """Directory where crash logs and memory dumps are recorded."""
        return self.root / "crashes"

    @property
    def presence_dir(self) -> Path:
        """Directory holding active process and conversation lock files."""
        return self.root / "presence"

    @property
    def log_dir(self) -> Path:
        """Directory for general logs."""
        return self.root / "log"

    @property
    def summaries_db(self) -> Path:
        """Path to conversation_summaries.db SQLite database."""
        return self.root / "conversation_summaries.db"

    @property
    def default_export_dir(self) -> Path:
        """Default export directory in the current working directory."""
        return Path.cwd() / "antigravity_export"

    def exists(self) -> bool:
        """Check if the Antigravity data directory exists."""
        return self.root.is_dir()
