from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, runtime_checkable

try:
    from typing import TYPE_CHECKING
except ImportError:  # pragma: no cover
    TYPE_CHECKING = False

if TYPE_CHECKING:  # pragma: no cover
    from src.runtime.context import RuntimeContext


@dataclass
class IntentResult:
    intent_id: str
    confidence: float
    slots: Dict[str, Any]
    raw: Any = None


class LLMError(Exception):
    """Raised when the LLM call fails."""


@runtime_checkable
class LLMClient(Protocol):
    model: str

    def recognize_intent(
        self,
        utterance: str,
        context: "RuntimeContext",
        candidate_intents: List[str],
    ) -> IntentResult:
        ...

