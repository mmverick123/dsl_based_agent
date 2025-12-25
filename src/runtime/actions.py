from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from src.dsl.ast import ActionNode
from src.runtime.context import RuntimeContext


@dataclass
class ActionResult:
    type: str
    payload: Dict[str, Any]
    success: bool = True
    message: str | None = None


ActionHandler = Callable[[ActionNode, RuntimeContext], ActionResult | None]


class ActionRegistry:
    """Registry of executable actions."""

    def __init__(self) -> None:
        self._handlers: Dict[str, ActionHandler] = {}

    def register(self, name: str, handler: ActionHandler) -> None:
        self._handlers[name] = handler

    def execute(self, action: ActionNode, context: RuntimeContext) -> List[ActionResult]:
        handler = self._handlers.get(action.name)
        if handler is None:
            raise ValueError(f"未注册的动作: {action.name}")
        result = handler(action, context)
        return [result] if result else []


def build_default_registry() -> ActionRegistry:
    registry = ActionRegistry()
    registry.register("reply", _reply_handler)
    registry.register("set", _set_handler)
    registry.register("call_api", _call_api_handler)
    registry.register("handover", _handover_handler)
    registry.register("log", _log_handler)
    return registry


def _reply_handler(action: ActionNode, context: RuntimeContext) -> ActionResult:
    if action.positional_args:
        text = action.positional_args[0]
    else:
        text = action.named_args.get("text", "")
    context.push_bot_message(text)
    return ActionResult(type="reply", payload={"text": text})


def _set_handler(action: ActionNode, context: RuntimeContext) -> ActionResult | None:
    key = None
    value = None

    # 位置参数形式：set foo bar
    if action.positional_args:
        key = action.positional_args[0]
        if len(action.positional_args) >= 2:
            value = action.positional_args[1]
        else:
            value = action.named_args.get("value")
    else:
        # 命名参数形式：
        # 1) set key=value
        # 2) set key = value
        # 3) set foo=bar   （取第一个键值对为 key/value）
        if "key" in action.named_args:
            key = action.named_args.get("key")
            value = action.named_args.get("value")
        elif action.named_args:
            key, value = next(iter(action.named_args.items()))

    if key is None:
        raise ValueError("set 动作缺少变量名")
    context.set_var(key, value)
    return ActionResult(
        type="context",
        payload={"op": "set", "key": key, "value": value},
        success=True,
    )


def _call_api_handler(action: ActionNode, context: RuntimeContext) -> ActionResult:
    endpoint = action.positional_args[0] if action.positional_args else "unknown"
    context.metadata.setdefault("api_calls", []).append(
        {"endpoint": endpoint, "params": action.named_args}
    )
    return ActionResult(
        type="call_api",
        payload={"endpoint": endpoint, "params": action.named_args},
        message="已模拟外部接口调用",
    )


def _handover_handler(action: ActionNode, context: RuntimeContext) -> ActionResult:
    target = action.positional_args[0] if action.positional_args else "人工客服"
    message = f"已为您转接至{target}"
    context.push_bot_message(message)
    return ActionResult(type="handover", payload={"target": target}, message=message)


def _log_handler(action: ActionNode, context: RuntimeContext) -> None:
    content = action.positional_args[0] if action.positional_args else ""
    context.metadata.setdefault("logs", []).append(content)
    return None

