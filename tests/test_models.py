"""
Unit tests for domain models.
"""

from antigravity_export.models import Conversation, FileChange, Message, ToolCall, normalize_file_path


def test_normalize_file_path():
    # Plain paths
    assert normalize_file_path("src/main.py") == "src/main.py"
    assert normalize_file_path("") == ""
    assert normalize_file_path(None) == ""

    # Dict wrappers
    assert normalize_file_path({"path": "src/main.py"}) == "src/main.py"
    assert normalize_file_path({"filePath": "src/main.py"}) == "src/main.py"
    assert "report" in normalize_file_path({"absoluteUri": "file:///d:/w/pay/report/page.tsx"})

    # Nested dict
    assert "test.ts" in normalize_file_path({"createFile": {"path": {"absoluteUri": "file:///d:/w/test.ts"}}})


def test_file_change_dict_path_normalization():
    # FileChange with dict path
    fc = FileChange(
        path={"absoluteUri": "file:///d:/w/pay/report/page.tsx"},  # type: ignore
        change_type="create",
    )
    assert isinstance(fc.path, str)
    assert "report" in fc.path


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
