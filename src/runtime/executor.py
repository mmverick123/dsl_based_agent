from __future__ import annotations

import traceback
from typing import List, Optional

from src.dsl.ast import ActionFlow, ActionNode, BotDefinition, StateNode, Transition
from src.llm.base import IntentResult, LLMClient, LLMError
from src.runtime.actions import ActionRegistry, ActionResult
from src.runtime.context import RuntimeContext


class Executor:
    """DSL AST interpreter."""

    def __init__(
        self,
        bot_definition: BotDefinition,
        context: RuntimeContext,
        llm_client: LLMClient,
        action_registry: ActionRegistry,
    ) -> None:
        self.bot = bot_definition
        self.context = context
        self.llm = llm_client
        self.actions = action_registry
        self.is_active = True
        self._just_entered = True

    def bootstrap(self) -> List[ActionResult]:
        """Run entry actions for the initial state."""
        return self._enter_state(self.context.current_state)

    def handle_user_input(self, utterance: str) -> List[ActionResult]:
        if not self.is_active:
            return [
                ActionResult(
                    type="system",
                    payload={},
                    success=False,
                    message="对话已结束",
                )
            ]

        state = self._current_state()
        self.context.push_user_message(utterance)

        try:
            intent = self.llm.recognize_intent(
                utterance, self.context, state.list_intents()
            )
        except LLMError as exc:
            return [
                ActionResult(
                    type="system",
                    payload={},
                    success=False,
                    message=f"LLM 调用失败: {exc}",
                )
            ]

        self.context.update_slots(intent.slots)
        transition = self._match_transition(state, intent)

        if transition:
            results = self._execute_flow(transition.flow)
        else:
            results = self._execute_fallback(state)

        return results

    # --- helpers ---
    def _current_state(self) -> StateNode:
        try:
            return self.bot.states[self.context.current_state]
        except KeyError as exc:
            raise ValueError(f"状态未定义: {self.context.current_state}") from exc

    def _match_transition(
        self, state: StateNode, intent: IntentResult
    ) -> Optional[Transition]:
        for transition in state.transitions:
            if transition.intent_id != intent.intent_id:
                continue
            if transition.condition is None:
                return transition
            if self._eval_condition(transition.condition):
                return transition
        return None

    def _eval_condition(self, expression: str) -> bool:
        try:
            env = self.context.build_eval_env()
            return bool(eval(expression, {"__builtins__": {}}, env))
        except Exception:
            traceback.print_exc()
            return False

    def _execute_flow(self, flow: ActionFlow) -> List[ActionResult]:
        results: List[ActionResult] = []
        for action in flow.actions:
            results.extend(self._execute_action(action))

        if flow.goto:
            results.extend(self._enter_state(flow.goto))

        if flow.directive == "end":
            self.is_active = False
            results.append(
                ActionResult(
                    type="system",
                    payload={},
                    message="对话结束",
                )
            )
        return results

    def _execute_action(self, action: ActionNode) -> List[ActionResult]:
        try:
            return self.actions.execute(action, self.context)
        except Exception as exc:
            return [
                ActionResult(
                    type="action_error",
                    payload={"action": action.name},
                    success=False,
                    message=str(exc),
                )
            ]

    def _enter_state(self, state_id: str) -> List[ActionResult]:
        self.context.set_state(state_id)
        state = self._current_state()
        results: List[ActionResult] = []
        for action in state.entry_actions:
            results.extend(self._execute_action(action))
        return results

    def _execute_fallback(self, state: StateNode) -> List[ActionResult]:
        if state.fallback:
            return self._execute_flow(state.fallback)
        return [
            ActionResult(
                type="reply",
                payload={"text": "抱歉，我暂时无法处理该请求。"},
                message="默认兜底回复",
            )
        ]

