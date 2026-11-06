"""
JSON exporter for Antigravity conversations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from antigravity_export.exporters.markdown_exporter import sanitize_filename
from antigravity_export.models import Conversation


class JSONExporter:
    """Exports conversation data into structured, machine-readable JSON."""

    def export(self, conv: Conversation) -> str:
        """Serialize a single conversation to JSON."""
        return json.dumps(conv.to_dict(), indent=2, ensure_ascii=False)

    def export_many(self, convs: Sequence[Conversation]) -> str:
        """Serialize multiple conversations into a single JSON array."""
        data = [c.to_dict() for c in convs]
        return json.dumps(data, indent=2, ensure_ascii=False)

    def save(self, conv: Conversation, output_dir: Path) -> Path:
        """Save a single conversation to a JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{sanitize_filename(conv.title)}_{conv.conversation_id[:8]}.json"
        out_path = output_dir / fname
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(self.export(conv))
        return out_path

    def save_many(self, convs: Sequence[Conversation], output_dir: Path, filename: str = "conversations_export.json") -> Path:
        """Save multiple conversations to a single JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(self.export_many(convs))
        return out_path
