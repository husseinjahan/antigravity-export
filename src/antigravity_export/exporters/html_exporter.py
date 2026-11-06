"""
Interactive, self-contained HTML exporter for Antigravity conversations.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from antigravity_export.exporters.markdown_exporter import sanitize_filename
from antigravity_export.models import Conversation, Message


class HTMLExporter:
    """Exports conversations into rich, portable, self-contained HTML files."""

    def __init__(self, include_thinking: bool = True):
        self.include_thinking = include_thinking

    def export(self, conv: Conversation) -> str:
        conv.aggregate_file_changes()
        safe_title = html.escape(conv.title)
        safe_id = html.escape(conv.conversation_id)
        safe_project = html.escape(conv.project_name)

        messages_html = "\n".join(self._render_message(m) for m in conv.messages)

        # File changes table if present
        file_changes_html = ""
        if conv.file_changes:
            rows = []
            for fc in conv.file_changes:
                rows.append(f"""
                <tr>
                    <td class="file-path"><code>{html.escape(fc.path)}</code></td>
                    <td><span class="badge badge-info">{html.escape(fc.change_type)}</span></td>
                    <td class="diff-add">+{fc.additions}</td>
                    <td class="diff-del">-{fc.deletions}</td>
                </tr>
                """)
            file_changes_html = f"""
            <section class="card mb-4">
                <h2>📦 Modified Files Summary ({len(conv.file_changes)})</h2>
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>File</th>
                                <th>Type</th>
                                <th>Added</th>
                                <th>Deleted</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows)}
                        </tbody>
                    </table>
                </div>
            </section>
            """

        recovery_badge = (
            '<span class="badge badge-warning">⚠️ Recovered Session</span>'
            if conv.is_recovered else ""
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} - Antigravity Export</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --surface-color: #1e293b;
            --surface-hover: #334155;
            --border-color: #334155;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --accent-color: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            --user-bubble: #1e293b;
            --assistant-bubble: #0f172a;
            --success-color: #4ade80;
            --danger-color: #f87171;
            --warning-color: #fbbf24;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            --mono-font: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: var(--font-family);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}

        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}

        header.header-card {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}

        h1 {{
            font-size: 1.85rem;
            margin-bottom: 0.75rem;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1.25rem;
            padding-top: 1.25rem;
            border-top: 1px solid var(--border-color);
            font-size: 0.9rem;
            color: var(--text-muted);
        }}

        .meta-item strong {{
            color: var(--text-color);
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-info {{ background: rgba(56, 189, 248, 0.2); color: var(--accent-color); }}
        .badge-warning {{ background: rgba(251, 191, 36, 0.2); color: var(--warning-color); }}
        .badge-success {{ background: rgba(74, 222, 128, 0.2); color: var(--success-color); }}

        .card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .table-container {{
            overflow-x: auto;
            margin-top: 1rem;
        }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}

        .data-table th, .data-table td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        .data-table th {{
            background-color: rgba(15, 23, 42, 0.6);
            color: var(--text-muted);
            font-weight: 600;
        }}

        .diff-add {{ color: var(--success-color); font-weight: 600; }}
        .diff-del {{ color: var(--danger-color); font-weight: 600; }}

        /* Messages */
        .message-thread {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .message {{
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            transition: transform 0.1s ease;
        }}

        .message-user {{
            background-color: var(--user-bubble);
            border-left: 4px solid var(--accent-color);
        }}

        .message-assistant {{
            background-color: var(--surface-color);
            border-left: 4px solid #a855f7;
        }}

        .message-tool {{
            background-color: rgba(30, 41, 59, 0.7);
            border-left: 4px solid var(--warning-color);
            font-size: 0.92rem;
        }}

        .message-system {{
            background-color: rgba(15, 23, 42, 0.5);
            border-left: 4px solid var(--text-muted);
            font-size: 0.88rem;
            font-style: italic;
        }}

        .message-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1.25rem;
            background-color: rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
        }}

        .message-body {{
            padding: 1.25rem;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: inherit;
        }}

        /* Accordion for thinking and tools */
        details {{
            margin: 0.75rem 0;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background-color: rgba(15, 23, 42, 0.7);
        }}

        summary {{
            padding: 0.75rem 1rem;
            cursor: pointer;
            font-weight: 600;
            color: var(--accent-color);
            user-select: none;
        }}

        summary:hover {{
            background-color: rgba(56, 189, 248, 0.05);
        }}

        .details-content {{
            padding: 1rem;
            border-top: 1px solid var(--border-color);
            font-family: var(--mono-font);
            font-size: 0.85rem;
            color: #cbd5e1;
            overflow-x: auto;
        }}

        /* Code & Diff highlighting */
        pre, code {{
            font-family: var(--mono-font);
        }}

        pre.diff-block {{
            background-color: #090d16;
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 0.85rem;
            border: 1px solid #1e293b;
        }}

        .diff-line-add {{ color: var(--success-color); background: rgba(74, 222, 128, 0.1); }}
        .diff-line-del {{ color: var(--danger-color); background: rgba(248, 113, 113, 0.1); }}
        .diff-line-hdr {{ color: var(--accent-color); }}

        footer {{
            text-align: center;
            margin-top: 3rem;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header-card">
            <h1>{safe_title} {recovery_badge}</h1>
            <p style="color: var(--text-muted);">Conversation ID: <code>{safe_id}</code></p>
            <div class="meta-grid">
                <div class="meta-item"><strong>Project:</strong> {safe_project}</div>
                <div class="meta-item"><strong>Steps:</strong> {conv.step_count}</div>
                <div class="meta-item"><strong>Files Changed:</strong> {len(conv.file_changes)}</div>
                <div class="meta-item"><strong>Created:</strong> {conv.created_time or 'N/A'}</div>
                <div class="meta-item"><strong>Last Modified:</strong> {conv.last_modified_time or 'N/A'}</div>
                <div class="meta-item"><strong>Exported:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
        </header>

        {file_changes_html}

        <main class="message-thread">
            {messages_html}
        </main>

        <footer>
            Exported with <strong>Antigravity Export CLI</strong> • Clean, self-contained, offline-compatible HTML
        </footer>
    </div>
</body>
</html>"""

    def _render_message(self, msg: Message) -> str:
        role_classes = {
            "user": "message-user",
            "assistant": "message-assistant",
            "tool": "message-tool",
            "system": "message-system",
        }
        role_icons = {
            "user": "👤 User",
            "assistant": "🤖 Assistant",
            "tool": "🔧 Tool Execution",
            "system": "⚙️ System",
        }
        cls_name = role_classes.get(msg.role, "message-system")
        icon = role_icons.get(msg.role, msg.role.title())
        ts = f'<span style="font-size: 0.8rem; color: var(--text-muted); font-weight: normal;">{html.escape(msg.timestamp or "")}</span>'

        body_html = ""

        # Thinking section
        if self.include_thinking and msg.thinking:
            safe_thinking = html.escape(msg.thinking.strip())
            body_html += f"""
            <details>
                <summary>💭 Thinking Process ({len(msg.thinking)} chars)</summary>
                <div class="details-content">{safe_thinking}</div>
            </details>
            """

        if msg.content.strip():
            body_html += f'<div class="message-body">{html.escape(msg.content.strip())}</div>'

        # File changes
        for fc in msg.file_changes:
            diff_lines_html = []
            if fc.unified_diff:
                for line in fc.unified_diff.splitlines():
                    esc_line = html.escape(line)
                    if line.startswith("+") and not line.startswith("+++"):
                        diff_lines_html.append(f'<span class="diff-line-add">{esc_line}</span>')
                    elif line.startswith("-") and not line.startswith("---"):
                        diff_lines_html.append(f'<span class="diff-line-del">{esc_line}</span>')
                    elif line.startswith("@@"):
                        diff_lines_html.append(f'<span class="diff-line-hdr">{esc_line}</span>')
                    else:
                        diff_lines_html.append(esc_line)

            diff_content = "\n".join(diff_lines_html)
            body_html += f"""
            <details open style="margin: 0.75rem 1.25rem;">
                <summary>📝 File Change: <code>{html.escape(fc.path)}</code> (+{fc.additions} / -{fc.deletions})</summary>
                <div class="details-content">
                    <pre class="diff-block"><code>{diff_content}</code></pre>
                </div>
            </details>
            """

        return f"""
        <article class="message {cls_name}">
            <div class="message-header">
                <span>{icon}</span>
                {ts}
            </div>
            {body_html}
        </article>
        """

    def save(self, conv: Conversation, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{sanitize_filename(conv.title)}_{conv.conversation_id[:8]}.html"
        out_path = output_dir / fname
        content = self.export(conv)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        return out_path

    def generate_index(
        self,
        convs: list[Conversation],
        is_multi_project: bool = True,
        title: str = "Antigravity Conversations Archive",
    ) -> str:
        """Generate a master Table of Contents (index.html) with search, filters, and stats."""
        safe_main_title = html.escape(title)
        total_convs = len(convs)
        total_steps = sum(c.step_count for c in convs)

        # Calculate file stats
        all_changes = []
        for c in convs:
            all_changes.extend(c.aggregate_file_changes())
        total_adds = sum(fc.additions for fc in all_changes)
        total_dels = sum(fc.deletions for fc in all_changes)

        # Projects list and counts
        project_counts: dict[str, int] = {}
        for c in convs:
            project_counts[c.project_name] = project_counts.get(c.project_name, 0) + 1

        # Project filter pills HTML
        project_pills = [
            f'<button class="filter-pill active" onclick="filterProject(\'all\', this)">All ({total_convs})</button>'
        ]
        for proj, count in sorted(project_counts.items()):
            safe_p = html.escape(proj)
            project_pills.append(
                f'<button class="filter-pill" onclick="filterProject(\'{safe_p}\', this)">{safe_p} ({count})</button>'
            )

        # Generate conversation rows
        rows_html = []
        for idx, conv in enumerate(convs, start=1):
            base_fname = f"{sanitize_filename(conv.title)}_{conv.conversation_id[:8]}"
            rel_prefix = f"{conv.project_name}/" if is_multi_project else ""

            html_link = f"{rel_prefix}{base_fname}.html"
            md_link = f"{rel_prefix}{base_fname}.md"
            json_link = f"{rel_prefix}{base_fname}.json"
            changes_link = f"{rel_prefix}{base_fname}_file_changes.md"

            safe_t = html.escape(conv.title)
            safe_proj = html.escape(conv.project_name)
            safe_cid = html.escape(conv.conversation_id)
            cid_short = safe_cid[:8] + "..."

            num_changes = len(conv.file_changes)
            c_adds = sum(fc.additions for fc in conv.file_changes)
            c_dels = sum(fc.deletions for fc in conv.file_changes)

            changes_badge = (
                f'<span class="badge badge-info" title="+{c_adds} / -{c_dels}">{num_changes} edits (+{c_adds}/-{c_dels})</span>'
                if num_changes else '<span class="text-muted" style="font-size:0.8rem;">None</span>'
            )

            recovery_badge = '<span class="badge badge-warning" style="margin-left:0.4rem;">Recovered</span>' if conv.is_recovered else ""

            # Format action links
            links = [f'<a href="{html_link}" class="link-btn link-html" target="_blank">HTML</a>']
            links.append(f'<a href="{md_link}" class="link-btn" target="_blank">MD</a>')
            links.append(f'<a href="{json_link}" class="link-btn" target="_blank">JSON</a>')
            if num_changes:
                links.append(f'<a href="{changes_link}" class="link-btn link-diff" target="_blank">Diffs</a>')

            ts = (conv.last_modified_time or conv.created_time or "N/A")[:19].replace("T", " ")

            rows_html.append(f"""
            <tr class="conv-row" data-project="{safe_proj}" data-title="{safe_t.lower()}" data-id="{safe_cid.lower()}">
                <td style="color: var(--text-muted); font-size: 0.85rem;">{idx}</td>
                <td><span class="badge badge-project">{safe_proj}</span></td>
                <td>
                    <a href="{html_link}" class="conv-title" target="_blank">{safe_t}</a>
                    {recovery_badge}
                </td>
                <td style="text-align: center;"><span class="badge badge-step">{conv.step_count}</span></td>
                <td>{changes_badge}</td>
                <td><div class="btn-group">{''.join(links)}</div></td>
                <td style="font-size: 0.82rem; color: var(--text-muted); white-space: nowrap;">{ts}</td>
                <td><code class="cid-badge" title="{safe_cid}">{cid_short}</code></td>
            </tr>
            """)

        export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_main_title}</title>
    <style>
        :root {{
            --bg-color: #0b1120;
            --surface-color: #1e293b;
            --surface-hover: #334155;
            --border-color: #334155;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --accent-color: #38bdf8;
            --accent-gradient: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            --success-color: #4ade80;
            --danger-color: #f87171;
            --warning-color: #fbbf24;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            --mono-font: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: var(--font-family);
            line-height: 1.6;
            padding: 2.5rem 1.5rem;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header.hero {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.4);
            position: relative;
            overflow: hidden;
        }}

        header.hero::after {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
            background: var(--accent-gradient);
        }}

        .hero-title {{
            font-size: 2.2rem;
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .hero-subtitle {{
            color: var(--text-muted);
            font-size: 1.05rem;
            margin-bottom: 2rem;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1.25rem;
        }}

        .stat-card {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
        }}

        .stat-num {{
            font-size: 1.85rem;
            font-weight: 800;
            color: #ffffff;
            font-family: var(--mono-font);
        }}

        .stat-label {{
            color: var(--text-muted);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.25rem;
        }}

        /* Controls Section */
        .controls-card {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }}

        .search-box {{
            width: 100%;
            padding: 0.85rem 1.25rem;
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #ffffff;
            font-size: 0.95rem;
            font-family: inherit;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .search-box:focus {{
            border-color: var(--accent-color);
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
        }}

        .filter-pills {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            align-items: center;
        }}

        .filter-label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-right: 0.5rem;
            font-weight: 600;
        }}

        .filter-pill {{
            background: #0f172a;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 0.4rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .filter-pill:hover {{
            background: var(--surface-hover);
            color: #ffffff;
        }}

        .filter-pill.active {{
            background: rgba(56, 189, 248, 0.15);
            border-color: var(--accent-color);
            color: var(--accent-color);
            font-weight: 600;
        }}

        .results-meta {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-left: auto;
        }}

        /* Table of Contents */
        .table-card {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}

        .table-responsive {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th {{
            background: #0f172a;
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-color);
        }}

        td {{
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
            font-size: 0.9rem;
        }}

        tr.conv-row:hover {{
            background: rgba(51, 65, 85, 0.3);
        }}

        a.conv-title {{
            color: #ffffff;
            text-decoration: none;
            font-weight: 600;
            display: inline-block;
            transition: color 0.15s;
        }}

        a.conv-title:hover {{
            color: var(--accent-color);
            text-decoration: underline;
        }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge-project {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
        .badge-step {{ background: rgba(251, 191, 36, 0.15); color: var(--warning-color); }}
        .badge-info {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-color); }}
        .badge-warning {{ background: rgba(248, 113, 113, 0.15); color: var(--danger-color); }}

        .cid-badge {{
            background: #0f172a;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            color: #94a3b8;
            border: 1px solid #1e293b;
        }}

        /* Button group */
        .btn-group {{
            display: flex;
            gap: 0.35rem;
        }}

        .link-btn {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            background: #0f172a;
            border: 1px solid var(--border-color);
            color: var(--text-color);
            text-decoration: none;
            font-size: 0.75rem;
            font-weight: 600;
            transition: all 0.15s;
        }}

        .link-btn:hover {{
            background: var(--surface-hover);
            border-color: var(--accent-color);
            color: #ffffff;
        }}

        .link-html {{
            background: rgba(56, 189, 248, 0.1);
            border-color: rgba(56, 189, 248, 0.3);
            color: var(--accent-color);
        }}

        .link-html:hover {{
            background: var(--accent-color);
            color: #0f172a;
        }}

        .link-diff {{
            background: rgba(74, 222, 128, 0.1);
            border-color: rgba(74, 222, 128, 0.3);
            color: var(--success-color);
        }}

        footer {{
            text-align: center;
            margin-top: 3rem;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="hero">
            <h1 class="hero-title">{safe_main_title}</h1>
            <p class="hero-subtitle">Master Table of Contents • Exported on {export_time}</p>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-num">{total_convs}</div>
                    <div class="stat-label">Conversations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-num">{len(project_counts)}</div>
                    <div class="stat-label">Projects</div>
                </div>
                <div class="stat-card">
                    <div class="stat-num">{total_steps:,}</div>
                    <div class="stat-label">Total Steps</div>
                </div>
                <div class="stat-card">
                    <div class="stat-num">{len(all_changes)}</div>
                    <div class="stat-label">File Edits</div>
                </div>
                <div class="stat-card">
                    <div class="stat-num" style="color: var(--success-color);">+{total_adds:,} / -{total_dels:,}</div>
                    <div class="stat-label">Lines Modified</div>
                </div>
            </div>
        </header>

        <section class="controls-card">
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search conversations by title, ID, project name..." oninput="filterConversations()">
            <div class="filter-pills">
                <span class="filter-label">Projects:</span>
                {''.join(project_pills)}
                <span class="results-meta" id="resultsCount">Showing {total_convs} of {total_convs} conversations</span>
            </div>
        </section>

        <section class="table-card">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 40px;">#</th>
                            <th style="width: 140px;">Project</th>
                            <th>Conversation Title</th>
                            <th style="text-align: center; width: 80px;">Steps</th>
                            <th style="width: 170px;">File Changes</th>
                            <th style="width: 190px;">Formats</th>
                            <th style="width: 160px;">Last Modified</th>
                            <th style="width: 110px;">ID</th>
                        </tr>
                    </thead>
                    <tbody id="convTableBody">
                        {''.join(rows_html)}
                    </tbody>
                </table>
            </div>
        </section>

        <footer>
            Generated automatically by <strong>Antigravity Export CLI</strong> (<code>agexport</code>) • Offline Master Index
        </footer>
    </div>

    <script>
        let currentProject = 'all';

        function filterProject(proj, btn) {{
            currentProject = proj.toLowerCase();
            document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filterConversations();
        }}

        function filterConversations() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const rows = document.querySelectorAll('.conv-row');
            let visibleCount = 0;

            rows.forEach(row => {{
                const p = row.getAttribute('data-project').toLowerCase();
                const title = row.getAttribute('data-title');
                const id = row.getAttribute('data-id');

                const matchesProject = (currentProject === 'all' || p === currentProject);
                const matchesQuery = !query || title.includes(query) || id.includes(query) || p.includes(query);

                if (matchesProject && matchesQuery) {{
                    row.style.display = '';
                    visibleCount++;
                }} else {{
                    row.style.display = 'none';
                }}
            }});

            const total = rows.length;
            document.getElementById('resultsCount').innerText = `Showing ${{visibleCount}} of ${{total}} conversations`;
        }}
    </script>
</body>
</html>"""

    def save_index(
        self,
        convs: list[Conversation],
        output_dir: Path,
        is_multi_project: bool = True,
        title: str = "Antigravity Conversations Archive",
        filename: str = "index.html",
    ) -> Path:
        """Save Table of Contents (index.html) to output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / filename
        content = self.generate_index(convs, is_multi_project=is_multi_project, title=title)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        return out_path

