"""
Unit tests for exporters (Markdown, HTML, JSON, FileChanges).
"""

import json
from pathlib import Path

from antigravity_export.exporters.file_changes_exporter import FileChangesExporter
from antigravity_export.exporters.html_exporter import HTMLExporter
from antigravity_export.exporters.json_exporter import JSONExporter
from antigravity_export.exporters.markdown_exporter import MarkdownExporter
from antigravity_export.models import Conversation, FileChange, Message


def create_sample_conversation() -> Conversation:
    fc = FileChange(
        path="src/app.py",
        change_type="modify",
        unified_diff="--- a/src/app.py\n+++ b/src/app.py\n@@ -1,2 +1,2 @@\n-def old():\n+def new():\n",
        additions=1,
        deletions=1,
    )
    m1 = Message(role="user", content="Add new function")
    m2 = Message(
        role="assistant",
        content="I have updated `src/app.py`.",
        thinking="Carefully updating function name",
        file_changes=[fc],
    )
    conv = Conversation(
        conversation_id="conv-12345678-abcd",
        title="Sample Test Conversation",
        project_name="test-project",
        messages=[m1, m2],
    )
    conv.aggregate_file_changes()
    return conv


def test_markdown_exporter():
    conv = create_sample_conversation()
    exporter = MarkdownExporter()
    md = exporter.export(conv)
    assert "# Sample Test Conversation" in md
    assert "conv-12345678-abcd" in md
    assert "Add new function" in md
    assert "src/app.py" in md
    assert "Thinking Process" in md


def test_html_exporter():
    conv = create_sample_conversation()
    exporter = HTMLExporter()
    html_out = exporter.export(conv)
    assert "<!DOCTYPE html>" in html_out
    assert "Sample Test Conversation" in html_out
    assert "src/app.py" in html_out
    assert "Thinking Process" in html_out


def test_html_index_generation():
    conv = create_sample_conversation()
    exporter = HTMLExporter()
    index_html = exporter.generate_index([conv], is_multi_project=False)
    assert "<!DOCTYPE html>" in index_html
    assert "Master Table of Contents" in index_html
    assert "Sample Test Conversation" in index_html
    assert "test-project" in index_html
    assert "conv-12345678-abcd" in index_html
    assert "searchInput" in index_html
    assert "filterProject" in index_html


def test_json_exporter():
    conv = create_sample_conversation()
    exporter = JSONExporter()
    json_str = exporter.export(conv)
    data = json.loads(json_str)
    assert data["conversation_id"] == "conv-12345678-abcd"
    assert data["project_name"] == "test-project"
    assert len(data["messages"]) == 2
    assert len(data["file_changes"]) == 1


def test_file_changes_exporter():
    conv = create_sample_conversation()
    exporter = FileChangesExporter()
    report = exporter.export_markdown(conv)
    assert "File Changes Report: Sample Test Conversation" in report
    assert "src/app.py" in report
    patch = exporter.export_unified_patch(conv)
    assert "+++ b/src/app.py" in patch
