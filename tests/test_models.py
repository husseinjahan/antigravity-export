"""
Unit tests for domain models.
"""

from antigravity_export.models import Conversation, FileChange, Message, ToolCall


def test_file_change_stats_computation():
    fc = FileChange(
        path="src/main.py",
        unified_diff="--- a/src/main.py\n+++ b/src/main.py\n@@ -1,3 +1,4 @@\n def hello():\n-    print('old')\n+    print('new')\n+    return True\n",
    )
    fc.compute_stats()
    assert fc.additions == 2
    assert fc.deletions == 1


def test_conversation_project_extraction():
    assert Conversation.extract_project_name(["file:///c%3A/Projects/antigravity-export"]) == "antigravity-export"
    assert Conversation.extract_project_name(["file:///c%3A/w/jahan/adswinger-ai"]) == "adswinger-ai"
    assert Conversation.extract_project_name([]) == "default"


def test_conversation_aggregate_file_changes():
    fc1 = FileChange(path="a.py", change_type="create", additions=10, deletions=0)
    fc2 = FileChange(path="b.py", change_type="modify", additions=5, deletions=2)
    m1 = Message(role="assistant", content="hello", file_changes=[fc1])
    m2 = Message(role="tool", content="edited", file_changes=[fc2])
    conv = Conversation(conversation_id="test-123", messages=[m1, m2])
    changes = conv.aggregate_file_changes()
    assert len(changes) == 2
    assert changes[0].path == "a.py"
    assert changes[1].path == "b.py"
