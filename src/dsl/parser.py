from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import List

from .ast import ActionFlow, ActionNode, BotDefinition, StateNode, Transition
from .errors import DSLParseError


@dataclass
class ParsedLine:
    indent: int
    content: str
    line_number: int


class Parser:
    """Simple indentation-based parser for the support-bot DSL."""

    def __init__(self, indent_size: int = 2) -> None:
        self.indent_size = indent_size
        self.lines: List[ParsedLine] = []
        self.position = 0

    def parse(self, script_text: str) -> BotDefinition:
        self.lines = self._tokenize(script_text)
        self.position = 0

        if not self.lines:
            raise DSLParseError("脚本为空", None)

        bot_line = self._consume_line()
        bot_match = re.match(r"bot\s+([A-Za-z0-9_\-]+)$", bot_line.content)
        if not bot_match:
            raise DSLParseError("脚本必须以 'bot <id>' 开头", bot_line.line_number)
        bot_id = bot_match.group(1)

        states: dict[str, StateNode] = {}
        while self._has_more():
            line = self._peek_line()
            if not line.content.startswith("state "):
                raise DSLParseError("只允许定义 state 块", line.line_number)
            state = self._parse_state()
            if state.state_id in states:
                raise DSLParseError(
                    f"重复的状态 '{state.state_id}'", line.line_number
                )
            states[state.state_id] = state

        return BotDefinition(bot_id=bot_id, states=states)

    def _tokenize(self, script_text: str) -> List[ParsedLine]:
        lines: List[ParsedLine] = []
        for idx, raw_line in enumerate(script_text.splitlines(), start=1):
            stripped = raw_line.rstrip()
            if not stripped:
                continue
            logical = stripped.lstrip()
            if logical.startswith("#"):
                continue
            indent = len(stripped) - len(logical)
            if indent % self.indent_size != 0:
                raise DSLParseError(
                    f"缩进必须是 {self.indent_size} 的倍数", idx
                )
            lines.append(ParsedLine(indent=indent, content=logical, line_number=idx))
        return lines

    def _parse_state(self) -> StateNode:
        header = self._consume_line()
        match = re.match(r"state\s+([A-Za-z0-9_\-]+):$", header.content)
        if not match:
            raise DSLParseError("state 定义语法错误，缺少冒号", header.line_number)
        state_id = match.group(1)

        entry_actions: list[ActionNode] = []
        transitions: list[Transition] = []
        fallback_flow: ActionFlow | None = None

        while self._has_more():
            line = self._peek_line()
            if line.indent <= header.indent:
                break
            clause_line = self._consume_line()
            if clause_line.content == "entry:":
                entry_actions = self._parse_action_block(
                    clause_line.indent, clause_line.line_number
                )
            elif clause_line.content.startswith("on_intent"):
                transition = self._parse_transition(clause_line)
                transitions.append(transition)
            elif clause_line.content == "fallback:":
                if fallback_flow is not None:
                    raise DSLParseError("fallback 只能定义一次", clause_line.line_number)
                fallback_flow = self._parse_flow_block(
                    clause_line.indent, clause_line.line_number
                )
            else:
                raise DSLParseError("未知的子句", clause_line.line_number)

        return StateNode(
            state_id=state_id,
            entry_actions=entry_actions,
            transitions=transitions,
            fallback=fallback_flow,
        )

    def _parse_action_block(
        self, parent_indent: int, line_number: int
    ) -> list[ActionNode]:
        block = self._collect_block(parent_indent)
        if not block:
            raise DSLParseError("entry 块不能为空", line_number)
        actions = [self._parse_action_line(line) for line in block]
        return actions

    def _parse_flow_block(self, parent_indent: int, line_number: int) -> ActionFlow:
        block = self._collect_block(parent_indent)
        if not block:
            raise DSLParseError("流程块不能为空", line_number)
        return self._lines_to_flow(block)

    def _parse_transition(self, line: ParsedLine) -> Transition:
        pattern = r"on_intent\s+([A-Za-z0-9_\-]+)(?:\s+if\s+(.+))?:$"
        match = re.match(pattern, line.content)
        if not match:
            raise DSLParseError("on_intent 语法错误", line.line_number)
        intent_id = match.group(1)
        condition = match.group(2).strip() if match.group(2) else None
        flow = self._parse_flow_block(line.indent, line.line_number)
        return Transition(intent_id=intent_id, condition=condition, flow=flow)

    def _lines_to_flow(self, lines: List[ParsedLine]) -> ActionFlow:
        flow = ActionFlow()
        for line in lines:
            content = line.content
            if content.startswith("goto "):
                if flow.goto is not None:
                    raise DSLParseError("同一流程中只能出现一次 goto", line.line_number)
                flow.goto = content.split(None, 1)[1]
            elif content == "end":
                if flow.directive is not None:
                    raise DSLParseError("end/continue 只能设置一次", line.line_number)
                flow.directive = "end"
            elif content == "continue":
                if flow.directive is not None:
                    raise DSLParseError("end/continue 只能设置一次", line.line_number)
                flow.directive = "continue"
            else:
                flow.actions.append(self._parse_action_line(line))
        return flow

    def _parse_action_line(self, line: ParsedLine) -> ActionNode:
        try:
            tokens = shlex.split(line.content, posix=True)
        except ValueError as exc:
            raise DSLParseError(f"动作语法错误: {exc}", line.line_number) from exc

        if not tokens:
            raise DSLParseError("动作行不能为空", line.line_number)

        name = tokens[0]
        pos_args: list[str] = []
        named_args: dict[str, str] = {}

        idx = 1
        while idx < len(tokens):
            token = tokens[idx]
            if token == "=":
                raise DSLParseError("缺少键名", line.line_number)
            if "=" in token:
                key, value = token.split("=", 1)
                named_args[key] = value
            elif idx + 1 < len(tokens) and tokens[idx + 1] == "=":
                key = token
                if idx + 2 >= len(tokens):
                    raise DSLParseError("赋值缺少右侧操作数", line.line_number)
                value = tokens[idx + 2]
                named_args[key] = value
                idx += 2
            else:
                pos_args.append(token)
            idx += 1

        return ActionNode(
            name=name,
            positional_args=pos_args,
            named_args=named_args,
            line_number=line.line_number,
        )

    def _collect_block(self, parent_indent: int) -> List[ParsedLine]:
        block: List[ParsedLine] = []
        while self._has_more():
            line = self._peek_line()
            if line.indent <= parent_indent:
                break
            if line.indent - parent_indent != self.indent_size:
                raise DSLParseError("缩进层级错误", line.line_number)
            block.append(self._consume_line())
        return block

    def _has_more(self) -> bool:
        return self.position < len(self.lines)

    def _peek_line(self) -> ParsedLine:
        return self.lines[self.position]

    def _consume_line(self) -> ParsedLine:
        line = self.lines[self.position]
        self.position += 1
        return line

