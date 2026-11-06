"""
Unit tests for step parser.
"""

from antigravity_export.parser import StepParser, create_diff_from_replacement, normalize_diff


def test_normalize_diff():
    raw_diff = {
        "unifiedDiff": {
            "lines": [
                {"type": "UNIFIED_DIFF_LINE_TYPE_CONTEXT", "text": "line 1"},
                {"type": "UNIFIED_DIFF_LINE_TYPE_DELETE", "text": "old line"},
                {"type": "UNIFIED_DIFF_LINE_TYPE_INSERT", "text": "new line"},
            ]
        }
    }
    normalized = normalize_diff(raw_diff)
    assert " line 1" in normalized
    assert "-old line" in normalized
    assert "+new line" in normalized


def test_create_diff_from_replacement():
    diff = create_diff_from_replacement("test.py", "x = 1\n", "x = 2\n")
    assert "-x = 1" in diff
    assert "+x = 2" in diff


def test_parse_user_input():
    parser = StepParser()
    step = {
        "type": "CORTEX_STEP_TYPE_USER_INPUT",
        "userInput": {"userResponse": "Please refactor this function."},
        "metadata": {"createdAt": "2026-11-06T10:00:00Z"},
    }
    msg = parser.parse_single_step(step)
    assert msg is not None
    assert msg.role == "user"
    assert msg.content == "Please refactor this function."


def test_parse_planner_response_with_tools():
    parser = StepParser(include_thinking=True)
    step = {
        "type": "CORTEX_STEP_TYPE_PLANNER_RESPONSE",
        "plannerResponse": {
            "response": "Here is the plan.",
            "thinking": "Thinking about architecture...",
            "toolCalls": [
                {
                    "name": "write_file",
                    "argumentsJson": '{"Path": "hello.py", "Content": "print(1)"}',
                }
            ],
        },
        "metadata": {"createdAt": "2026-11-06T10:01:00Z"},
    }
    msg = parser.parse_single_step(step)
    assert msg is not None
    assert msg.role == "assistant"
    assert msg.content == "Here is the plan."
    assert msg.thinking == "Thinking about architecture..."
    assert len(msg.tool_calls) == 1
    assert len(msg.file_changes) == 1
    assert msg.file_changes[0].path == "hello.py"
    assert msg.file_changes[0].change_type == "create"
