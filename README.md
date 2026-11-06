# Antigravity Export (agexport)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A high-performance Python CLI and library to connect directly to the running **Google Antigravity Language Server** (`language_server`), inspect connection state, and export conversations, code modifications, unified git patches, and full reasoning chains into Markdown, self-contained HTML, and JSON. It also features a resilient **Crash Recovery Engine** that can restore unindexed or interrupted sessions directly from SQLite databases and brain logs.

[**🇮🇷 مستندات به زبان فارسی (Persian Documentation) در فایل README.fa.md موجود است.**](README.fa.md)

---

## ✨ Features

- 🛰️ **Language Server Connectivity**: Automatically discovers running Antigravity Language Server processes, dynamically scans listening ports, retrieves CSRF tokens, and connects over the gRPC-Web / HTTP Connect protocol.
- 📋 **Chat List & Project Navigation**: List and filter conversations by project, workspace, date, or step count with an interactive Rich terminal interface.
- 📁 **Multi-Project & Project-Scoped Export**: Export all conversations grouped neatly by project folders, or target a single project or conversation ID.
- 📝 **Markdown Export (`.md`)**: Clean GitHub-flavored Markdown with conversation metadata, user inputs, collapsible `<details>` tags for AI reasoning/thinking chains, and highlighted tool executions.
- 🌐 **Self-Contained HTML Export (`.html`)**: Beautiful, responsive, standalone single-page HTML files with modern dark-mode styling, syntax-highlighted unified diffs, collapsible thinking accordions, and zero external CDN dependencies (100% offline viewable).
- 📑 **Master Table of Contents (`index.html`)**: Automatically generates an interactive Table of Contents dashboard when exporting chats. Features instant search, project filtering pills, summary statistics (total conversations, projects, steps, lines modified), and direct quick-links to HTML, Markdown, JSON, and diff reports.
- 📊 **Structured JSON Export (`.json`)**: Complete, machine-readable JSON format for programmatic analysis, LLM evals, or database archiving.
- 🔍 **Dedicated File Changes & Git Patch Exporter**: Extracts all code edits, additions, deletions, unified diffs, and generates standard `.patch` files compatible with `git apply`.
- 🛡️ **Crash & Update Recovery Engine**: Recovers lost conversations after IDE crashes or updates by scanning `~/.gemini/antigravity/crashes/`, SQLite databases (`conversation_summaries.db`, `conversations/*.db`), and brain transcripts (`transcript_full.jsonl`).
- ⚡ **Global CLI & Python Library**: Can be installed globally as `agexport` / `antigravity-export` or imported into custom Python scripts.

---

## 🚀 Installation & Setup

### Option 1: Using Virtual Environment (`venv`)

```bash
# 1. Clone or navigate to the project directory
cd /path/to/antigravity-export

# 2. Create and activate a virtual environment
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install the package in editable mode
pip install -e .
```

### Option 2: Global CLI Installation

To install globally so that `agexport` is available everywhere in your terminal:

```bash
# Using standard pip
pip install .

# Or using pipx (recommended for isolated global CLI tools)
pipx install .
```

---

## 💻 CLI Commands & Usage

Once installed, the CLI is available as either `agexport` or `antigravity-export`.

### 1. Check Language Server Status
Verify whether the Antigravity Language Server is running, its PID, port, CSRF token, and storage overview:

```bash
agexport status
# or
agexport info
```

*Example Output:*
```
Antigravity Language Server Status v1.0.0

┌───────────────────────────┬─────────────────────────────────────────────────┐
│ Connection State          │ CONNECTED                                       │
│ Process State             │ RUNNING                                         │
│ Process ID (PID)          │ 32808                                           │
│ Active Port               │ 63316                                           │
│ CSRF Token                │ f442deef-118...                                 │
│ IDE Name / Version        │ antigravity 2.26.0                              │
│ App Data Directory        │ C:\Users\user\.gemini\antigravity               │
│ Stored Conversations (DB) │ 6                                               │
│ Crash Dumps Detected      │ 4                                               │
└───────────────────────────┴─────────────────────────────────────────────────┘

[OK] Ready for export and real-time interaction (1 active endpoint(s))
```

---

### 2. List Conversations
List active and stored conversations with metadata, project name, step count, and file change metrics:

```bash
# List latest conversations
agexport list

# Filter conversations by project
agexport list --project adswinger-ai

# Show only today's conversations
agexport list --today

# Output as raw JSON (ideal for piping into jq)
agexport list --json
```

---

### 3. List Projects & Workspaces
View an aggregated summary of all projects, workspaces, conversation counts, and total file modifications:

```bash
agexport projects
```

---

### 4. Export Conversations

Export conversations into Markdown, HTML, JSON, and extract file diffs:

```bash
# Export all conversations across all projects (organized by project folder)
agexport export --all-projects -o ./my_exports

# Export all conversations for a specific project
agexport export -p adswinger-ai -o ./my_exports

# Export a single conversation by ID
agexport export --id c13776f9-5e3b-49e6-9532-3f19ab2a568a -o ./single_chat

# Export only in Markdown format
agexport export -f md -o ./markdown_only

# Export only in HTML format
agexport export -f html -o ./html_only

# Export only in JSON format
agexport export -f json -o ./json_only

# Exclude AI internal thinking process
agexport export --no-thinking -o ./concise_exports

# Offline export (reads directly from SQLite and brain logs without running server)
agexport export --all-projects --offline -o ./offline_exports
```

---

### 5. Quick One-Shot Full Export
Shortcut command to export everything in all formats across all projects:

```bash
agexport export-all -o ./antigravity_export
```

---

### 6. Export File Changes & Git Patches
Specifically extract code modifications, unified diffs, and generate `.patch` files:

```bash
# Export all file changes across all projects
agexport export-changes -o ./patches

# Export file changes for a specific project
agexport export-changes -p antigravity-export -o ./patches
```

Generated files include:
- `<Title>_<ID>_file_changes.md`: Chronological summary of edits with unified diffs.
- `<Title>_<ID>.patch`: Standard Git patch file ready to apply via `git apply`.
- `<Project>_project_file_changes.md`: High-level overview of all modified files.

---

### 7. Recover Lost Conversations After Crashes/Updates
Scan local crash logs (`~/.gemini/antigravity/crashes/`), unindexed SQLite databases, and brain transcripts to restore lost sessions:

```bash
# 1. Preview recoverable sessions without writing files (dry-run)
agexport recover --dry-run

# 2. Recover unindexed/lost conversations
agexport recover -o ./recovered_chats

# 3. Force full offline recovery of all sessions on disk
agexport recover --all --force-offline -o ./full_recovery
```

---

## 🐍 Python Library Usage

You can also import `antigravity_export` directly into your own Python applications:

```python
from antigravity_export import (
    LanguageServerManager,
    LanguageServerClient,
    ConversationRecovery,
)
from antigravity_export.exporters import HTMLExporter, MarkdownExporter, JSONExporter

# 1. Inspect Language Server connection
mgr = LanguageServerManager()
status = mgr.get_status()
print(f"Server Running: {status.is_running}, Port: {status.port}")

# 2. Query conversations via client
endpoints = mgr.find_all_endpoints()
client = LanguageServerClient()
summaries, _, _ = client.get_all_trajectories_merged(endpoints)

# 3. Recover an interrupted conversation
recovery = ConversationRecovery()
conversation = recovery.recover_conversation("c13776f9-5e3b-49e6-9532-3f19ab2a568a")

if conversation:
    print(f"Title: {conversation.title}, Files Changed: {len(conversation.file_changes)}")
    
    # Export to HTML
    html_exporter = HTMLExporter(include_thinking=True)
    html_exporter.save(conversation, output_dir=Path("./exports"))
```

---

## 🏗️ Architecture & Project Structure

```
antigravity-export/
├── src/
│   └── antigravity_export/
│       ├── __init__.py           # Package exports and version metadata
│       ├── __main__.py           # CLI invocation via `python -m antigravity_export`
│       ├── cli.py                # Rich + Typer CLI implementation
│       ├── config.py             # System paths (~/.gemini/antigravity) & constants
│       ├── connection.py         # Process detection (WMI/ps), port resolver & health checks
│       ├── api_client.py         # gRPC-Web / HTTP Connect protocol client
│       ├── models.py             # Dataclass models: Conversation, Message, ToolCall, FileChange
│       ├── parser.py             # Multi-modal step parser & unified diff generator
│       ├── storage.py            # SQLite reader (conversation_summaries.db) & brain logs
│       ├── recovery.py           # Crash dump analysis & unindexed conversation recovery
│       └── exporters/
│           ├── __init__.py
│           ├── markdown_exporter.py    # GitHub-flavored Markdown formatter
│           ├── html_exporter.py        # Standalone, interactive HTML generator
│           ├── json_exporter.py        # Structured JSON serializer
│           └── file_changes_exporter.py# Code diffs and .patch generator
├── tests/                        # Comprehensive pytest test suite
│   ├── test_models.py
│   ├── test_parser.py
│   ├── test_exporters.py
│   └── test_recovery.py
├── pyproject.toml                # Modern PEP 621 build configuration
├── setup.py                      # Compatibility installation script
├── requirements.txt              # Production dependencies
├── README.md                     # English documentation
└── README.fa.md                  # Persian documentation (راهنمای فارسی)
```

---

## 🧪 Running Tests

Run the test suite using `pytest`:

```bash
pytest
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
