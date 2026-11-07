"""
Markdown exporter for Antigravity conversations.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from antigravity_export.models import Conversation, Message


def sanitize_filename(name: str) -> str:
    """Turn a title or string into a safe filesystem filename."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip().replace(" ", "_")
    return name[:80] or "conversation"


class MarkdownExporter:
    """Exports conversations to clean, GitHub-flavored Markdown."""

    def __init__(self, include_thinking: bool = True):
        self.include_thinking = include_thinking

    def export(self, conv: Conversation) -> str:
        """Convert Conversation model into Markdown string."""
        conv.aggregate_file_changes()
        lines = [
            f"# {conv.title}",
            "",
            f"- **Conversation ID**: `{conv.conversation_id}`",
            f"- **Project**: `{conv.project_name}`",
            f"- **Status**: `{conv.status}`",
            f"- **Steps**: {conv.step_count}",
            f"- **Files Changed**: {len(conv.file_changes)}",
            f"- **Created**: {conv.created_time or 'N/A'}",
            f"- **Last Modified**: {conv.last_modified_time or 'N/A'}",
            f"- **Exported At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if conv.is_recovered:
            lines.append("- **Recovery**: ⚠️ *Recovered after crash or state desynchronization*")

        if conv.workspace_uris:
            lines.append(f"- **Workspace URIs**: {', '.join(conv.workspace_uris)}")

        lines.extend(["", "---", ""])

        # Table of modified files if any
        if conv.file_changes:
            lines.append("## 📦 Modified Files Summary")
            lines.append("")
            lines.append("| File Path | Type | Added | Deleted |")
            lines.append("| :--- | :---: | :---: | :---: |")
            for fc in conv.file_changes:
                lines.append(f"| `{str(fc.path or '')}` | `{str(fc.change_type or '')}` | +{fc.additions} | -{fc.deletions} |")
            lines.extend(["", "---", ""])

        # Conversation turns
        for msg in conv.messages:
            lines.extend(self._format_message(msg))

        return "\n".join(lines)

    def _format_message(self, msg: Message) -> list[str]:
        lines: list[str] = []
        ts_badge = f"  `{msg.timestamp[:19]}`" if msg.timestamp else ""

        if msg.role == "user":
            lines.append(f"## 👤 User{ts_badge}")
            lines.append("")
            lines.append(msg.content.strip())
            lines.append("")

        elif msg.role == "assistant":
            lines.append(f"## 🤖 Assistant{ts_badge}")
            lines.append("")

            if self.include_thinking and msg.thinking:
                lines.append("<details>")
                lines.append("<summary>💭 <strong>Thinking Process</strong> (click to expand)</summary>")
                lines.append("")
                lines.append(msg.thinking.strip())
                lines.append("")
                lines.append("</details>")
                lines.append("")

            if msg.content.strip():
                lines.append(msg.content.strip())
                lines.append("")

            meta_items = []
            if msg.model:
                meta_items.append(f"Model: `{msg.model}`")
            if msg.stop_reason:
                meta_items.append(f"Stop: `{msg.stop_reason}`")
            if msg.thinking_duration:
                meta_items.append(f"Thinking Duration: `{msg.thinking_duration}`")
            if meta_items:
                lines.append(f"*{' | '.join(meta_items)}*")
                lines.append("")

            # Inline tool calls or file changes made during this turn
            for fc in msg.file_changes:
                lines.extend(self._format_file_change(fc))

        elif msg.role == "tool":
            lines.append(f"### 🔧 Tool Execution{ts_badge}")
            lines.append("")
            if msg.content.strip():
                lines.append(msg.content.strip())
                lines.append("")
            for fc in msg.file_changes:
                lines.extend(self._format_file_change(fc))

        elif msg.role == "system":
            lines.append(f"> ⚙️ **System Note**{ts_badge}: {msg.content.strip()}")
            lines.append("")

        return lines

    def _format_file_change(self, fc) -> list[str]:
        lines = []
        stats = f"(+{fc.additions} / -{fc.deletions})"
        path_str = str(fc.path or "")
        lines.append(f"#### 📝 File Edit: `{path_str}` {stats}")
        if fc.artifact_summary:
            lines.append(f"> {fc.artifact_summary}")
        if fc.unified_diff:
            lines.append("```diff")
            lines.append(fc.unified_diff.strip())
            lines.append("```")
        lines.append("")
        return lines

    def save(self, conv: Conversation, output_dir: Path) -> Path:
        """Save formatted markdown to directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{sanitize_filename(conv.title)}_{conv.conversation_id[:8]}.md"
        out_path = output_dir / fname
        content = self.export(conv)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        return out_path
