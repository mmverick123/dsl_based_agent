from __future__ import annotations

from typing import Dict, List

from .base import IntentResult, LLMClient


class MockLLMClient(LLMClient):
    """Rule-based mock client for offline testing."""

    def __init__(self, model: str = "mock-intent") -> None:
        self.model = model
        self._rules: Dict[str, str] = {
            "退款": "refund_request",
            "退货": "refund_request",
            "物流": "logistics_track",
            "快递": "logistics_track",
            "人工": "need_human",
            "转人工": "need_human",
            "营业时间": "faq_hours",
            "地址": "faq_location",
        }

    def recognize_intent(
        self, utterance: str, context, candidate_intents: List[str]
    ) -> IntentResult:
        matches = [
            intent
            for keyword, intent in self._rules.items()
            if keyword in utterance and intent in candidate_intents
        ]
        intent_id = matches[0] if matches else (candidate_intents[0] if candidate_intents else "unknown")
        slots = {}
        if "订单" in utterance:
            slots["order_id"] = "AUTO_DEMO"
        if "金额" in utterance or "元" in utterance:
            slots["amount"] = 100
        return IntentResult(intent_id=intent_id, confidence=0.6, slots=slots, raw={"mock": True})

