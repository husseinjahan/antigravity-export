"""
Parser converting raw Antigravity Language Server steps and JSONL logs into structured models.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Optional

from antigravity_export.models import FileChange, Message, ToolCall

_DIFF_PREFIX = {
    "UNIFIED_DIFF_LINE_TYPE_INSERT": "+",
    "UNIFIED_DIFF_LINE_TYPE_DELETE": "-",
    "UNIFIED_DIFF_LINE_TYPE_CONTEXT": " ",
}


def normalize_diff(diff_obj: Any) -> str:
    """Normalize raw diff structures from LanguageServer into a standard unified diff string."""
    if not diff_obj:
        return ""
    if isinstance(diff_obj, str):
        return diff_obj
    if isinstance(diff_obj, dict):
        lines_data = diff_obj.get("unifiedDiff", {}).get("lines", [])
        if not lines_data:
            return str(diff_obj)
        parts = []
        for line in lines_data:
            text = line.get("text", "")
            prefix = _DIFF_PREFIX.get(line.get("type", ""), " ")
            parts.append(f"{prefix}{text}")
        return "\n".join(parts)
    return str(diff_obj)


def create_diff_from_replacement(
    file_path: str,
    target: str,
    replacement: str,
) -> str:
    """Generate a standard unified diff between target and replacement text."""
    fname = Path(file_path).name or "file"
    from_lines = target.splitlines(keepends=True)
    to_lines = replacement.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            from_lines,
            to_lines,
            fromfile=f"a/{fname}",
            tofile=f"b/{fname}",
        )
    )
    return "".join(diff)


class StepParser:
    """Parses raw Language Server steps into structured Message, ToolCall, and FileChange objects."""

    def __init__(self, include_thinking: bool = True, include_full: bool = True):
        self.include_thinking = include_thinking
        self.include_full = include_full

    def parse_steps(self, raw_steps: list[dict[str, Any]]) -> list[Message]:
        """Convert a list of raw steps into structured Messages."""
        messages: list[Message] = []
        for step in raw_steps:
            msg = self.parse_single_step(step)
            if msg:
                messages.append(msg)
        return messages

    def parse_single_step(self, step: dict[str, Any]) -> Optional[Message]:
        """Parse one step dict (either from API or brain transcript JSONL)."""
        step_type = step.get("type", "")
        metadata = step.get("metadata", {})
        created_at = metadata.get("createdAt") or step.get("created_at")
        step_index = step.get("step_index")

        # 1. USER INPUT
        if step_type in ("CORTEX_STEP_TYPE_USER_INPUT", "USER_INPUT"):
            return self._parse_user_input(step, created_at, step_index)

        # 2. PLANNER RESPONSE (Model / Assistant)
        if step_type in ("CORTEX_STEP_TYPE_PLANNER_RESPONSE", "PLANNER_RESPONSE"):
            return self._parse_planner_response(step, created_at, step_index)

        # 3. CODE ACTION (File edits / creations)
        if step_type == "CORTEX_STEP_TYPE_CODE_ACTION":
            return self._parse_code_action(step, created_at, step_index)

        # 4. RUN COMMAND (Bash / PowerShell)
        if step_type == "CORTEX_STEP_TYPE_RUN_COMMAND":
            return self._parse_run_command(step, created_at, step_index)

        # 5. VIEW FILE
        if step_type == "CORTEX_STEP_TYPE_VIEW_FILE":
            return self._parse_view_file(step, created_at, step_index)

        # 6. WEB SEARCH
        if step_type == "CORTEX_STEP_TYPE_SEARCH_WEB":
            return self._parse_search_web(step, created_at, step_index)

        # 7. GENERIC / SYSTEM MESSAGE
        if step_type in ("CORTEX_STEP_TYPE_SYSTEM_MESSAGE", "GENERIC"):
            content = step.get("content") or ""
            if content.strip():
                return Message(
                    role="system",
                    content=content,
                    timestamp=created_at,
                    step_index=step_index,
                )

        return None

    def _parse_user_input(
        self,
        step: dict[str, Any],
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Optional[Message]:
        ui = step.get("userInput", {})
        content = ui.get("userResponse") or step.get("content") or ""
        if not content.strip():
            return None

        return Message(
            role="user",
            content=content,
            timestamp=created_at,
            step_index=step_index,
        )

    def _parse_planner_response(
        self,
        step: dict[str, Any],
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Optional[Message]:
        pr = step.get("plannerResponse", {})
        content = pr.get("modifiedResponse") or pr.get("response") or step.get("content") or ""
        thinking = pr.get("thinking") or step.get("thinking")
        stop_reason = pr.get("stopReason")
        thinking_duration = pr.get("thinkingDuration")

        model = step.get("metadata", {}).get("generatorModel") or step.get("model")

        # Parse tool calls embedded in planner response
        tool_calls: list[ToolCall] = []
        file_changes: list[FileChange] = []

        raw_calls = pr.get("toolCalls") or step.get("tool_calls") or []
        for raw_call in raw_calls:
            tc = self._parse_tool_call(raw_call, created_at, step_index)
            if tc:
                tool_calls.append(tc)
                # Check if this tool call represents a file change
                fc = self._extract_file_change_from_tool_call(tc, created_at, step_index)
                if fc:
                    file_changes.append(fc)

        # Even if content is empty, if we have thinking or tool calls, it's a valid assistant message
        if not content.strip() and not thinking and not tool_calls:
            return None

        return Message(
            role="assistant",
            content=content,
            thinking=thinking if self.include_thinking else None,
            timestamp=created_at,
            tool_calls=tool_calls,
            file_changes=file_changes,
            step_index=step_index,
            model=model,
            stop_reason=stop_reason,
            thinking_duration=thinking_duration,
        )

    def _parse_tool_call(
        self,
        raw_call: dict[str, Any],
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Optional[ToolCall]:
        name = raw_call.get("name")
        fn = raw_call.get("function", {})
        if not name and fn:
            name = fn.get("name")

        if not name:
            return None

        args: dict[str, Any] = {}
        args_json = raw_call.get("argumentsJson")
        if args_json:
            try:
                args = json.loads(args_json)
            except Exception:
                args = {"raw": args_json}
        elif fn.get("arguments"):
            raw_args = fn["arguments"]
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {"raw": raw_args}
            elif isinstance(raw_args, dict):
                args = raw_args

        return ToolCall(
            name=name,
            call_id=raw_call.get("id"),
            args=args,
            status=raw_call.get("status"),
        )

    def _extract_file_change_from_tool_call(
        self,
        tc: ToolCall,
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Optional[FileChange]:
        """Extract a FileChange object from write_file or edit_file tool calls."""
        name = tc.name.lower()
        args = tc.args

        if "write_file" in name or name == "write":
            path = args.get("Path") or args.get("path") or ""
            content = args.get("Content") or args.get("content") or ""
            if path:
                diff = f"+++ b/{Path(path).name}\n" + "\n".join(f"+{l}" for l in content.splitlines())
                fc = FileChange(
                    path=path,
                    change_type="create",
                    content=content,
                    unified_diff=diff,
                    timestamp=created_at,
                    step_index=step_index,
                )
                fc.compute_stats()
                return fc

        if "edit_file" in name or name == "edit":
            path = args.get("Path") or args.get("path") or ""
            target = args.get("Target") or args.get("target") or ""
            replacement = args.get("Replacement") or args.get("replacement") or ""
            if path:
                diff = create_diff_from_replacement(path, target, replacement)
                fc = FileChange(
                    path=path,
                    change_type="modify",
                    target=target,
                    replacement=replacement,
                    unified_diff=diff,
                    timestamp=created_at,
                    step_index=step_index,
                )
                fc.compute_stats()
                return fc

        return None

    def _parse_code_action(
        self,
        step: dict[str, Any],
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Message:
        ca = step.get("codeAction", {})
        description = ca.get("description", "")
        file_path = ""

        action_result = ca.get("actionResult", {})
        edit = action_result.get("edit", {})
        if edit.get("absoluteUri"):
            file_path = edit["absoluteUri"]
        elif ca.get("actionSpec", {}).get("createFile", {}).get("path"):
            file_path = ca["actionSpec"]["createFile"]["path"]

        summary = f"[Code Edit] {file_path}" if file_path else "[Code Edit]"
        if description:
            summary += f"\n{description}"

        diff = normalize_diff(edit.get("diff"))
        artifact = ca.get("artifactMetadata", {})

        file_changes: list[FileChange] = []
        if file_path:
            fc = FileChange(
                path=file_path,
                change_type="modify",
                unified_diff=diff if diff else None,
                artifact_summary=artifact.get("summary"),
                timestamp=created_at,
                step_index=step_index,
            )
            fc.compute_stats()
            file_changes.append(fc)

        tool_call = ToolCall(
            name="code_action",
            args={"path": file_path, "description": description},
            output=diff,
        )

        return Message(
            role="tool",
            content=summary,
            timestamp=created_at,
            tool_calls=[tool_call],
            file_changes=file_changes,
            step_index=step_index,
        )

    def _parse_run_command(
        self,
        step: dict[str, Any],
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Message:
        rc = step.get("runCommand", {})
        cmd = rc.get("commandLine") or rc.get("command") or ""
        cwd = rc.get("cwd")
        exit_code = rc.get("exitCode")
        output = rc.get("combinedOutput", {}).get("full")

        summary = f"Run Command: {cmd}"
        if cwd:
            summary += f" (in {cwd})"
        if exit_code is not None:
            summary += f" -> exit {exit_code}"

        tc = ToolCall(
            name="run_command",
            args={"command": cmd, "cwd": cwd},
            output=output,
            exit_code=exit_code,
        )

        return Message(
            role="tool",
            content=summary,
            timestamp=created_at,
            tool_calls=[tc],
            step_index=step_index,
        )

    def _parse_view_file(
        self,
        step: dict[str, Any],
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Message:
        vf = step.get("viewFile", {})
        path = vf.get("absolutePathUri") or vf.get("filePath") or vf.get("path") or ""
        num_lines = vf.get("numLines")
        num_bytes = vf.get("numBytes")

        summary = f"Viewed File: {path}"
        if num_lines:
            summary += f" ({num_lines} lines)"

        tc = ToolCall(
            name="view_file",
            args={"path": path, "num_lines": num_lines, "num_bytes": num_bytes},
        )

        return Message(
            role="tool",
            content=summary,
            timestamp=created_at,
            tool_calls=[tc],
            step_index=step_index,
        )

    def _parse_search_web(
        self,
        step: dict[str, Any],
        created_at: Optional[str],
        step_index: Optional[int],
    ) -> Message:
        sw = step.get("searchWeb", {})
        query = sw.get("query") or ""
        summary = sw.get("summary") or ""

        tc = ToolCall(
            name="search_web",
            args={"query": query},
            output=summary,
        )

        return Message(
            role="tool",
            content=f"Web Search: {query}",
            timestamp=created_at,
            tool_calls=[tc],
            step_index=step_index,
        )
