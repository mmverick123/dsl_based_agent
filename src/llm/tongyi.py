from __future__ import annotations

import json
from typing import Any, Dict, List

from .base import IntentResult, LLMClient, LLMError

try:
    import dashscope
    from dashscope import Generation
except ImportError:  # pragma: no cover - optional dependency
    dashscope = None
    Generation = None


SYSTEM_PROMPT = """
你是企业智能客服系统的意图解析器，需要根据用户话术推断意图与槽位。
请仅输出 JSON，格式如下：
{"intent": "<intent_id>", "confidence": 0-1, "slots": {"slot": "value"}}
候选意图: {candidate_intents}
如果难以确定，intent 返回 "unknown"，confidence 设为 0.0。
""".strip()


class TongyiLLMClient(LLMClient):
    """LLM client backed by Qianwen (DashScope)."""

    def __init__(self, api_key: str | None = None, model: str = "qwen-plus") -> None:
        if Generation is None:
            raise ImportError("未安装 dashscope，无法调用通义千问 API")
        self.model = model
        if api_key:
            dashscope.api_key = api_key

    def recognize_intent(
        self,
        utterance: str,
        context,
        candidate_intents: List[str],
    ) -> IntentResult:
        if not candidate_intents:
            candidate_intents = ["unknown"]
        prompt = SYSTEM_PROMPT.format(
            candidate_intents=", ".join(candidate_intents)
        )
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "utterance": utterance,
                        "history_tail": [
                            {"role": record.role, "content": record.content}
                            for record in context.history[-3:]
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        try:
            response = Generation.call(
                model=self.model,
                messages=messages,
                result_format="message",
            )
        except Exception as exc:  # pragma: no cover
            raise LLMError(str(exc)) from exc

        if response.status_code != 200:
            raise LLMError(f"LLM 调用失败: {response.code} {response.message}")

        text = self._extract_text(response)
        data = self._parse_json(text)

        return IntentResult(
            intent_id=data.get("intent", "unknown"),
            confidence=float(data.get("confidence", 0)),
            slots=data.get("slots", {}),
            raw=text,
        )

    def _extract_text(self, response: Any) -> str:
        choice = response.output.choices[0]
        content = choice["message"]["content"]
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content)
        return str(content)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            cleaned = text[text.find("{") : text.rfind("}") + 1]
            try:
                return json.loads(cleaned)
            except Exception as exc:  # pragma: no cover
                raise LLMError(f"无法解析 LLM 输出: {text}") from exc

