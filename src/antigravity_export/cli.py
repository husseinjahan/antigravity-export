"""
Command Line Interface for Antigravity Export using Typer and Rich.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

# Ensure standard output and error use UTF-8 on Windows
if sys.platform == "win32":
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from antigravity_export import __version__
from antigravity_export.api_client import LanguageServerClient
from antigravity_export.config import AntigravityConfig
from antigravity_export.connection import LanguageServerManager
from antigravity_export.exporters.file_changes_exporter import FileChangesExporter
from antigravity_export.exporters.html_exporter import HTMLExporter
from antigravity_export.exporters.json_exporter import JSONExporter
from antigravity_export.exporters.markdown_exporter import MarkdownExporter
from antigravity_export.models import Conversation
from antigravity_export.parser import StepParser
from antigravity_export.recovery import ConversationRecovery
from antigravity_export.storage import StorageReader

app = typer.Typer(
    name="agexport",
    help="Export Antigravity conversations, file changes, diffs, and recover lost sessions.",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


def _get_endpoints_or_exit(
    mgr: LanguageServerManager,
    port: Optional[int] = None,
    token: Optional[str] = None,
    allow_offline: bool = False,
) -> list[dict]:
    """Discover active Language Server endpoints or return empty if offline is allowed."""
    endpoints = mgr.find_all_endpoints(manual_port=port, manual_token=token)
    if not endpoints and not allow_offline:
        err_console.print(
            Panel.fit(
                "[bold red]Cannot connect to Antigravity Language Server[/bold red]\n"
                "[yellow]Make sure Antigravity is running with an open workspace.[/yellow]\n"
                "[dim]Use --offline to export/recover directly from local database & brain logs.[/dim]",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    return endpoints


def _load_all_conversations(
    config: AntigravityConfig,
    client: LanguageServerClient,
    endpoints: list[dict],
    storage: StorageReader,
    include_thinking: bool = True,
    project_filter: Optional[str] = None,
    today_only: bool = False,
    selected_ids: Optional[list[str]] = None,
) -> list[Conversation]:
    """Fetch and parse conversations across Language Server and local storage."""
    parser = StepParser(include_thinking=include_thinking, include_full=True)
    all_convs: list[Conversation] = []

    # 1. Trajectories from LS
    summaries, cascade_ep, _ = client.get_all_trajectories_merged(endpoints) if endpoints else ({}, {}, [])

    # 2. Add storage summaries for full project coverage
    db_summaries = storage.get_summaries_from_db()
    for cid, s_info in db_summaries.items():
        if cid not in summaries:
            summaries[cid] = s_info

    # Filter IDs if specified
    if selected_ids:
        summaries = {k: v for k, v in summaries.items() if k in selected_ids}

    # Filter today's conversations
    if today_only:
        today_str = date.today().isoformat()
        summaries = {
            k: v for k, v in summaries.items()
            if (v.get("lastModifiedTime") or "").startswith(today_str)
        }

    default_ep = endpoints[0] if endpoints else None

    # Load conversations
    for cid, info in summaries.items():
        title = info.get("summary") or info.get("title") or f"Conversation {cid[:8]}"
        uris = info.get("workspace_uris") or []
        if not uris and "workspaces" in info:
            uris = [w.get("workspaceFolderAbsoluteUri", "") for w in info["workspaces"] if w.get("workspaceFolderAbsoluteUri")]
        project_name = Conversation.extract_project_name(uris)

        if project_filter and project_filter.lower() not in project_name.lower():
            continue

        step_count = info.get("stepCount", 0)
        created_time = info.get("createdTime")
        last_modified = info.get("lastModifiedTime")
        status = info.get("status", "ACTIVE")

        # Fetch steps
        raw_steps = []
        ep = cascade_ep.get(cid, default_ep)
        if ep:
            try:
                raw_steps = client.get_trajectory_steps(cid, step_count=step_count or 1000, port=ep["port"], csrf_token=ep["csrf_token"])
            except Exception:
                pass

        if not raw_steps:
            # Fallback to direct brain transcript
            raw_steps = storage.read_brain_transcript(cid)

        messages = parser.parse_steps(raw_steps) if raw_steps else []

        conv = Conversation(
            conversation_id=cid,
            title=title,
            project_name=project_name,
            workspace_uris=uris,
            created_time=created_time,
            last_modified_time=last_modified,
            status=status,
            step_count=len(raw_steps) or step_count,
            messages=messages,
            raw_metadata=info,
        )
        conv.aggregate_file_changes()
        all_convs.append(conv)

    return all_convs


# ══════════════════════════════════════════════════════════════════════════
# STATUS / INFO SUBCOMMAND
# ══════════════════════════════════════════════════════════════════════════

@app.command(name="status")
@app.command(name="info")
def show_status(
    port: Optional[int] = typer.Option(None, "--port", help="Manual port override"),
    token: Optional[str] = typer.Option(None, "--token", help="Manual CSRF token override"),
):
    """Show Antigravity Language Server connection status and diagnostic information."""
    config = AntigravityConfig()
    mgr = LanguageServerManager(config)
    status = mgr.get_status(manual_port=port, manual_token=token)

    console.print(f"\n[bold cyan]Antigravity Language Server Status[/bold cyan] [dim]v{__version__}[/dim]\n")

    conn_badge = "[bold green]CONNECTED[/bold green]" if status.is_reachable else "[bold red]DISCONNECTED[/bold red]"
    proc_badge = "[green]RUNNING[/green]" if status.is_running else "[red]STOPPED[/red]"

    table = Table(show_header=False, box=box.ROUNDED)
    table.add_column("Property", style="bold white", width=25)
    table.add_column("Value")

    table.add_row("Connection State", conn_badge)
    table.add_row("Process State", proc_badge)
    if status.process_id:
        table.add_row("Process ID (PID)", str(status.process_id))
    if status.executable_path:
        table.add_row("Executable Path", f"[dim]{status.executable_path}[/dim]")
    if status.port:
        table.add_row("Active Port", f"[cyan]{status.port}[/cyan]")
    if status.csrf_token:
        table.add_row("CSRF Token", f"[dim]{status.csrf_token[:12]}...[/dim]")
    if status.ide_name:
        table.add_row("IDE Name / Version", f"{status.ide_name} {status.ide_version or ''}")

    table.add_row("App Data Directory", f"[dim]{config.root}[/dim]")
    table.add_row("Stored Conversations (DB)", f"[yellow]{status.total_stored_conversations}[/yellow]")
    table.add_row("Crash Dumps Detected", f"[red]{status.crashes_detected}[/red]" if status.crashes_detected else "[green]0[/green]")

    console.print(table)

    if status.endpoints:
        console.print(f"\n[bold green][OK] Ready for export and real-time interaction[/bold green] ({len(status.endpoints)} active endpoint(s))\n")
    else:
        console.print(f"\n[yellow][!] {status.error_message or 'No active endpoints found.'}[/yellow]")
        console.print("[dim]Hint: Launch Antigravity IDE or desktop application, or use offline recovery.[/dim]\n")


# ══════════════════════════════════════════════════════════════════════════
# LIST SUBCOMMAND
# ══════════════════════════════════════════════════════════════════════════

@app.command(name="list")
def list_chats(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Filter by project name"),
    today: bool = typer.Option(False, "--today", help="Show only today's conversations"),
    limit: int = typer.Option(50, "-n", "--limit", help="Max number of conversations to display"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON array to stdout"),
    offline: bool = typer.Option(False, "--offline", help="Read directly from local database & storage"),
    port: Optional[int] = typer.Option(None, "--port", help="Manual port override"),
    token: Optional[str] = typer.Option(None, "--token", help="Manual CSRF token override"),
):
    """List conversations with conversation IDs, project names, steps, and file change counts."""
    config = AntigravityConfig()
    mgr = LanguageServerManager(config)
    client = LanguageServerClient(config=config)
    storage = StorageReader(config)

    endpoints = _get_endpoints_or_exit(mgr, port, token, allow_offline=offline)
    convs = _load_all_conversations(
        config, client, endpoints, storage,
        include_thinking=False,
        project_filter=project,
        today_only=today,
    )

    convs = sorted(convs, key=lambda c: c.last_modified_time or "", reverse=True)[:limit]

    if json_out:
        data = [
            {
                "conversation_id": c.conversation_id,
                "title": c.title,
                "project": c.project_name,
                "steps": c.step_count,
                "files_changed": len(c.file_changes),
                "last_modified": c.last_modified_time,
                "created": c.created_time,
            }
            for c in convs
        ]
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    table = Table(
        title=f"Antigravity Conversations ({len(convs)} shown)",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Project", style="magenta", width=18)
    table.add_column("Title", style="white", min_width=30, max_width=45)
    table.add_column("Files Chg", style="green", justify="right", width=9)
    table.add_column("Steps", style="yellow", justify="right", width=6)
    table.add_column("Last Modified", style="dim", width=19)
    table.add_column("Conversation ID", style="cyan", width=12)

    for i, c in enumerate(convs, start=1):
        ts = (c.last_modified_time or "?")[:19].replace("T", " ")
        cid_short = f"{c.conversation_id[:8]}..."
        table.add_row(
            str(i),
            c.project_name[:18],
            c.title[:45],
            str(len(c.file_changes)),
            str(c.step_count),
            ts,
            cid_short,
        )

    console.print()
    console.print(table)
    console.print(f"[dim]Tip: Export by project: [cyan]agexport export -p <project>[/cyan] | Full export: [cyan]agexport export-all[/cyan][/dim]\n")


# ══════════════════════════════════════════════════════════════════════════
# PROJECTS SUBCOMMAND
# ══════════════════════════════════════════════════════════════════════════

@app.command(name="projects")
def list_projects(
    offline: bool = typer.Option(False, "--offline", help="Read directly from local database & storage"),
):
    """List all detected projects and workspaces with conversation counts."""
    config = AntigravityConfig()
    mgr = LanguageServerManager(config)
    client = LanguageServerClient(config=config)
    storage = StorageReader(config)

    endpoints = _get_endpoints_or_exit(mgr, allow_offline=True)
    convs = _load_all_conversations(config, client, endpoints, storage, include_thinking=False)

    by_project: dict[str, list[Conversation]] = defaultdict(list)
    for c in convs:
        by_project[c.project_name].append(c)

    table = Table(title="Detected Projects & Workspaces", box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Project Name", style="bold white", width=25)
    table.add_column("Conversations", justify="right", width=14)
    table.add_column("Total Steps", justify="right", width=12)
    table.add_column("Total File Edits", justify="right", width=16)
    table.add_column("Workspace URI", style="dim")

    for proj, items in sorted(by_project.items()):
        steps = sum(c.step_count for c in items)
        edits = sum(len(c.file_changes) for c in items)
        uri = items[0].workspace_uris[0] if items and items[0].workspace_uris else "-"
        table.add_row(proj, str(len(items)), str(steps), str(edits), uri)

    console.print()
    console.print(table)
    console.print()


# ══════════════════════════════════════════════════════════════════════════
# EXPORT SUBCOMMAND
# ══════════════════════════════════════════════════════════════════════════

@app.command(name="export")
def export_conversations(
    ids: Optional[list[str]] = typer.Option(None, "--id", help="Specific conversation ID(s) to export"),
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Export all chats for a specific project"),
    all_projects: bool = typer.Option(False, "--all-projects", help="Export all chats for all projects"),
    fmt: str = typer.Option("all", "-f", "--format", help="Export format: md | html | json | all"),
    with_file_changes: bool = typer.Option(True, "--with-file-changes/--no-file-changes", help="Include dedicated file changes and patch files"),
    thinking: bool = typer.Option(True, "--thinking/--no-thinking", help="Include internal AI thinking process"),
    output: str = typer.Option("./antigravity_export", "-o", "--output", help="Root output directory"),
    today: bool = typer.Option(False, "--today", help="Export only today's conversations"),
    offline: bool = typer.Option(False, "--offline", help="Run in offline mode using local databases and brain logs"),
    port: Optional[int] = typer.Option(None, "--port", help="Manual port override"),
    token: Optional[str] = typer.Option(None, "--token", help="Manual CSRF token override"),
):
    """Export conversations into Markdown, HTML, JSON, and extract file changes."""
    config = AntigravityConfig()
    mgr = LanguageServerManager(config)
    client = LanguageServerClient(config=config)
    storage = StorageReader(config)

    endpoints = _get_endpoints_or_exit(mgr, port, token, allow_offline=offline)

    console.print(f"\n[bold cyan]Antigravity Conversation Export[/bold cyan] [dim]v{__version__}[/dim]")
    console.print(f"[dim]Output directory: {Path(output).resolve()}[/dim]")
    console.print(f"[dim]Formats: {fmt.upper()} | Include thinking: {thinking} | File changes: {with_file_changes}[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        load_task = progress.add_task("[cyan]Loading conversation data...", total=None)
        convs = _load_all_conversations(
            config,
            client,
            endpoints,
            storage,
            include_thinking=thinking,
            project_filter=project,
            today_only=today,
            selected_ids=ids,
        )
        progress.update(load_task, completed=1, total=1, description="[green]Data loaded")

        if not convs:
            console.print("[yellow]No matching conversations found to export.[/yellow]")
            raise typer.Exit(0)

        out_root = Path(output)
        md_exporter = MarkdownExporter(include_thinking=thinking)
        html_exporter = HTMLExporter(include_thinking=thinking)
        json_exporter = JSONExporter()
        changes_exporter = FileChangesExporter()

        export_task = progress.add_task(f"[cyan]Exporting {len(convs)} conversation(s)...", total=len(convs))

        by_proj: dict[str, list[Conversation]] = defaultdict(list)
        total_files_written = 0

        for conv in convs:
            by_proj[conv.project_name].append(conv)

            # Determine destination folder (group by project if --all-projects or multiple projects)
            if all_projects or (not project and len(convs) > 1):
                dest_dir = out_root / conv.project_name
            else:
                dest_dir = out_root

            dest_dir.mkdir(parents=True, exist_ok=True)

            # Markdown
            if fmt in ("md", "all"):
                md_exporter.save(conv, dest_dir)
                total_files_written += 1

            # HTML
            if fmt in ("html", "all"):
                html_exporter.save(conv, dest_dir)
                total_files_written += 1

            # JSON
            if fmt in ("json", "all"):
                json_exporter.save(conv, dest_dir)
                total_files_written += 1

            # Dedicated File changes & patch
            if with_file_changes and conv.file_changes:
                changes_exporter.save(conv, dest_dir)
                total_files_written += 2

            progress.advance(export_task)

        # Write aggregated JSON and project summaries
        for proj_name, proj_convs in by_proj.items():
            proj_dir = out_root / proj_name if (all_projects or len(by_proj) > 1) else out_root
            if fmt in ("json", "all"):
                json_exporter.save_many(proj_convs, proj_dir, filename=f"{proj_name}_all_chats.json")
                total_files_written += 1
            if with_file_changes:
                changes_exporter.save_project_summary(proj_name, proj_convs, proj_dir)
                total_files_written += 1

        # Generate Master Table of Contents (index.html)
        if fmt in ("html", "all"):
            is_multi = all_projects or len(by_proj) > 1
            html_exporter.save_index(
                convs,
                out_root,
                is_multi_project=is_multi,
                title="Antigravity Conversations Archive",
            )
            total_files_written += 1

            if is_multi:
                for proj_name, proj_convs in by_proj.items():
                    proj_dir = out_root / proj_name
                    html_exporter.save_index(
                        proj_convs,
                        proj_dir,
                        is_multi_project=False,
                        title=f"Project Archive: {proj_name}",
                    )
                    total_files_written += 1

    console.print(f"\n[bold green][OK] Export successfully completed![/bold green]")
    console.print(f"  * Total conversations exported: [bold cyan]{len(convs)}[/bold cyan]")
    console.print(f"  * Projects processed: [bold magenta]{len(by_proj)}[/bold magenta] ({', '.join(by_proj.keys())})")
    console.print(f"  * Total files generated: [bold white]{total_files_written}[/bold white]")
    console.print(f"  * Location: [bold underline]{out_root.resolve()}[/bold underline]\n")


# ══════════════════════════════════════════════════════════════════════════
# EXPORT-ALL SHORTCUT
# ══════════════════════════════════════════════════════════════════════════

@app.command(name="export-all")
def export_all(
    output: str = typer.Option("./antigravity_export", "-o", "--output", help="Output directory"),
    offline: bool = typer.Option(False, "--offline", help="Run offline from local storage"),
):
    """Convenience shortcut: Export all chats for all projects in all formats (MD, HTML, JSON, Changes)."""
    export_conversations(
        ids=None,
        project=None,
        all_projects=True,
        fmt="all",
        with_file_changes=True,
        thinking=True,
        output=output,
        today=False,
        offline=offline,
        port=None,
        token=None,
    )


# ══════════════════════════════════════════════════════════════════════════
# EXPORT-CHANGES SUBCOMMAND
# ══════════════════════════════════════════════════════════════════════════

@app.command(name="export-changes")
def export_changes(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Filter by project"),
    output: str = typer.Option("./antigravity_export/changes", "-o", "--output", help="Output directory"),
    offline: bool = typer.Option(False, "--offline", help="Read directly from local storage"),
):
    """Specifically extract and export all file modifications, diffs, and patches."""
    config = AntigravityConfig()
    mgr = LanguageServerManager(config)
    client = LanguageServerClient(config=config)
    storage = StorageReader(config)

    endpoints = _get_endpoints_or_exit(mgr, allow_offline=offline)
    convs = _load_all_conversations(
        config, client, endpoints, storage,
        include_thinking=False,
        project_filter=project,
    )

    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    exporter = FileChangesExporter()

    total_changes = 0
    with console.status("[cyan]Extracting file changes and generating patches..."):
        for conv in convs:
            if conv.file_changes:
                exporter.save(conv, out_dir)
                total_changes += len(conv.file_changes)

        if project:
            exporter.save_project_summary(project, convs, out_dir)

    console.print(f"\n[bold green][OK] File changes export completed![/bold green]")
    console.print(f"  * Conversations with changes: [cyan]{sum(1 for c in convs if c.file_changes)}[/cyan]")
    console.print(f"  * Total file modifications: [cyan]{total_changes}[/cyan]")
    console.print(f"  * Output directory: [underline]{out_dir.resolve()}[/underline]\n")


# ══════════════════════════════════════════════════════════════════════════
# RECOVER SUBCOMMAND
# ══════════════════════════════════════════════════════════════════════════

@app.command(name="recover")
def recover_lost_chats(
    output: str = typer.Option("./antigravity_export/recovered", "-o", "--output", help="Output directory for recovered chats"),
    fmt: str = typer.Option("all", "-f", "--format", help="Export format: md | html | json | all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Scan and detect recoverable conversations without exporting"),
    force_all: bool = typer.Option(False, "--all", help="Force recovery of all conversations found across disk storage"),
    force_offline: bool = typer.Option(False, "--force-offline", help="Force offline recovery directly from disk without querying LS"),
    port: Optional[int] = typer.Option(None, "--port", help="Manual port override"),
    token: Optional[str] = typer.Option(None, "--token", help="Manual CSRF token override"),
):
    """Scan and recover conversations lost or corrupted after crashes or updates."""
    config = AntigravityConfig()
    mgr = LanguageServerManager(config)
    client = LanguageServerClient(config=config)
    recovery = ConversationRecovery(config=config, client=client)

    endpoints = mgr.find_all_endpoints(manual_port=port, manual_token=token)

    console.print(f"\n[bold yellow]Antigravity Conversation Recovery Engine[/bold yellow]\n")

    with console.status("[cyan]Scanning crash logs and local SQLite/JSONL storage..."):
        report = recovery.run_recovery(
            endpoints=[] if force_all else endpoints,
            dry_run=dry_run,
            force_offline=force_offline,
        )

    console.print(Panel(report.summary(), title="[bold cyan]Recovery Scan Report[/bold cyan]", box=box.ROUNDED))

    if dry_run:
        console.print("[yellow]Dry-run mode active. No files were written.[/yellow]\n")
        return

    if not report.recovered_conversations:
        console.print("[dim]No unindexed or lost conversations required recovery.[/dim]\n")
        return

    # Export recovered conversations
    out_dir = Path(output)
    md_exporter = MarkdownExporter()
    html_exporter = HTMLExporter()
    json_exporter = JSONExporter()
    changes_exporter = FileChangesExporter()

    for conv in report.recovered_conversations:
        dest_dir = out_dir / conv.project_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        if fmt in ("md", "all"):
            md_exporter.save(conv, dest_dir)
        if fmt in ("html", "all"):
            html_exporter.save(conv, dest_dir)
        if fmt in ("json", "all"):
            json_exporter.save(conv, dest_dir)
        if conv.file_changes:
            changes_exporter.save(conv, dest_dir)

    # Generate master Table of Contents for recovered sessions
    if fmt in ("html", "all"):
        is_multi = len(set(c.project_name for c in report.recovered_conversations)) > 1
        html_exporter.save_index(
            report.recovered_conversations,
            out_dir,
            is_multi_project=is_multi,
            title="Recovered Antigravity Conversations Archive",
        )

    console.print(f"\n[bold green][OK] Successfully exported {len(report.recovered_conversations)} recovered conversation(s)![/bold green]")
    console.print(f"  * Saved in: [underline]{out_dir.resolve()}[/underline]\n")


# ══════════════════════════════════════════════════════════════════════════
# MAIN CALLBACK
# ══════════════════════════════════════════════════════════════════════════

def version_callback(value: bool):
    if value:
        console.print(f"Antigravity Export CLI v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """Antigravity Export - Connect to the running Language Server and export conversations."""
    pass


if __name__ == "__main__":
    app()
