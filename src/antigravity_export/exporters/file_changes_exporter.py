"""
Dedicated exporter for tracking, summarizing, and generating patches for file changes.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Sequence

from antigravity_export.exporters.markdown_exporter import sanitize_filename
from antigravity_export.models import Conversation, FileChange


class FileChangesExporter:
    """Specialized exporter that focuses on code edits, unified diffs, and file modifications."""

    def export_markdown(self, conv: Conversation) -> str:
        """Generate a dedicated Markdown report of all file changes in a conversation."""
        changes = conv.aggregate_file_changes()
        lines = [
            f"# File Changes Report: {conv.title}",
            "",
            f"- **Conversation ID**: `{conv.conversation_id}`",
            f"- **Project**: `{conv.project_name}`",
            f"- **Total Changes Recorded**: {len(changes)}",
            f"- **Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ]

        if not changes:
            lines.append("*(No code or file modifications were recorded in this conversation)*")
            return "\n".join(lines)

        # Group by file path
        by_file: dict[str, list[FileChange]] = defaultdict(list)
        total_adds = 0
        total_dels = 0
        for fc in changes:
            fc.compute_stats()
            by_file[str(fc.path or "")].append(fc)
            total_adds += fc.additions
            total_dels += fc.deletions

        lines.extend([
            "## 📊 Summary",
            "",
            f"- **Unique Files Touched**: {len(by_file)}",
            f"- **Total Insertions**: +{total_adds}",
            f"- **Total Deletions**: -{total_dels}",
            "",
            "| File | Changes Count | Added | Deleted |",
            "| :--- | :---: | :---: | :---: |",
        ])

        for path, file_changes in by_file.items():
            f_adds = sum(c.additions for c in file_changes)
            f_dels = sum(c.deletions for c in file_changes)
            lines.append(f"| `{path}` | {len(file_changes)} | +{f_adds} | -{f_dels} |")

        lines.extend(["", "---", "", "## 🔍 Detailed File Edits", ""])

        for path, file_changes in by_file.items():
            lines.append(f"### 📄 `{path}`")
            lines.append("")
            for idx, fc in enumerate(file_changes, start=1):
                ts = f" at `{fc.timestamp[:19]}`" if fc.timestamp else ""
                lines.append(f"#### Change #{idx} ({fc.change_type}){ts} `+{fc.additions}/-{fc.deletions}`")
                if fc.artifact_summary:
                    lines.append(f"> {fc.artifact_summary}")
                if fc.unified_diff:
                    lines.append("```diff")
                    lines.append(fc.unified_diff.strip())
                    lines.append("```")
                elif fc.content:
                    lines.append("```")
                    lines.append(fc.content.strip()[:2000])
                    lines.append("```")
                lines.append("")

        return "\n".join(lines)

    def export_unified_patch(self, conv: Conversation) -> str:
        """Create a standard git-apply compatible patch file from all changes."""
        changes = conv.aggregate_file_changes()
        patch_blocks: list[str] = []
        for fc in changes:
            if fc.unified_diff:
                patch_blocks.append(fc.unified_diff.strip())
        return "\n\n".join(patch_blocks) + "\n"

    def save(self, conv: Conversation, output_dir: Path) -> tuple[Path, Path]:
        """Save both Markdown report and patch file for a conversation."""
        output_dir.mkdir(parents=True, exist_ok=True)
        base = f"{sanitize_filename(conv.title)}_{conv.conversation_id[:8]}"
        md_path = output_dir / f"{base}_file_changes.md"
        patch_path = output_dir / f"{base}.patch"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.export_markdown(conv))

        patch_content = self.export_unified_patch(conv)
        if patch_content.strip():
            with open(patch_path, "w", encoding="utf-8") as f:
                f.write(patch_content)

        return md_path, patch_path

    def save_project_summary(self, project_name: str, convs: Sequence[Conversation], output_dir: Path) -> Path:
        """Save an aggregated file changes summary across an entire project."""
        output_dir.mkdir(parents=True, exist_ok=True)
        all_changes: list[FileChange] = []
        for c in convs:
            all_changes.extend(c.aggregate_file_changes())

        by_file: dict[str, list[FileChange]] = defaultdict(list)
        total_adds = 0
        total_dels = 0
        for fc in all_changes:
            by_file[str(fc.path or "")].append(fc)
            total_adds += fc.additions
            total_dels += fc.deletions

        lines = [
            f"# Project File Changes Summary: {project_name}",
            "",
            f"- **Conversations Count**: {len(convs)}",
            f"- **Total File Modifications**: {len(all_changes)}",
            f"- **Total Lines Added**: +{total_adds}",
            f"- **Total Lines Deleted**: -{total_dels}",
            f"- **Exported At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📁 Modified Files",
            "",
            "| File Path | Modifications | Additions | Deletions |",
            "| :--- | :---: | :---: | :---: |",
        ]

        for path, changes in by_file.items():
            f_adds = sum(c.additions for c in changes)
            f_dels = sum(c.deletions for c in changes)
            lines.append(f"| `{path}` | {len(changes)} | +{f_adds} | -{f_dels} |")

        out_path = output_dir / f"{sanitize_filename(project_name)}_project_file_changes.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return out_path
