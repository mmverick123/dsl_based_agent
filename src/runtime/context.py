from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class AttrDict(dict):
    """Dictionary that exposes keys as attributes for condition expressions."""

    def __getattr__(self, item: str) -> Any:
        return self.get(item)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


@dataclass
class MessageRecord:
    role: str
    content: str


@dataclass
class RuntimeContext:
    bot_id: str
    initial_state: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    variables: Dict[str, Any] = field(default_factory=dict)
    slots: Dict[str, Any] = field(default_factory=dict)
    history: List[MessageRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    current_state: str = field(init=False)

    def __post_init__(self) -> None:
        self.current_state = self.initial_state

    # --- history helpers ---
    def push_user_message(self, content: str) -> None:
        self.history.append(MessageRecord(role="user", content=content))

    def push_bot_message(self, content: str) -> None:
        self.history.append(MessageRecord(role="bot", content=content))

    # --- slots & vars ---
    def update_slots(self, new_slots: Dict[str, Any]) -> None:
        if not new_slots:
            return
        self.slots.update(new_slots)

    def set_var(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get_var(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    # --- state management ---
    def set_state(self, state_id: str) -> None:
        self.current_state = state_id

    # --- evaluation helpers ---
    def build_eval_env(self) -> Dict[str, Any]:
        """Provide safe evaluation context for condition expressions."""
        return {
            "slots": AttrDict(self.slots),
            "vars": AttrDict(self.variables),
            "context": self,
        }

