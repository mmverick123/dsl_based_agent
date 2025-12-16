from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ActionNode:
    """Represents a single action invocation in the DSL."""

    name: str
    positional_args: List[str] = field(default_factory=list)
    named_args: Dict[str, str] = field(default_factory=dict)
    line_number: int | None = None


@dataclass
class ActionFlow:
    """A sequence of actions with an optional control directive."""

    actions: List[ActionNode] = field(default_factory=list)
    goto: Optional[str] = None
    directive: Optional[str] = None  # "end" | "continue"


@dataclass
class Transition:
    """Intent transition definition."""

    intent_id: str
    condition: Optional[str]
    flow: ActionFlow


@dataclass
class StateNode:
    """State definition inside a bot."""

    state_id: str
    entry_actions: List[ActionNode] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    fallback: Optional[ActionFlow] = None

    def list_intents(self) -> List[str]:
        return [transition.intent_id for transition in self.transitions]


@dataclass
class BotDefinition:
    """Parsed bot definition."""

    bot_id: str
    states: Dict[str, StateNode]

    def initial_state(self) -> str:
        if not self.states:
            raise ValueError("Bot must contain at least one state.")
        # preserve insertion order (Python 3.7+ dict keeps order)
        return next(iter(self.states.keys()))

