import os
import pytest

try:
    from src.llm.tongyi import TongyiLLMClient
except ImportError:
    TongyiLLMClient = None  # type: ignore


class DummyContext:
    """Minimal context to satisfy LLM client signature."""

    def __init__(self) -> None:
        self.history = []


@pytest.mark.skipif(
    os.getenv("DASHSCOPE_API_KEY") is None, reason="需要 DASHSCOPE_API_KEY 才能运行真实 LLM 测试"
)
@pytest.mark.skipif(TongyiLLMClient is None, reason="未安装 dashscope，跳过真实 LLM 测试")
def test_tongyi_llm_intent_recognition():
    """集成测试：调用通义千问识别意图并落在候选集合内。"""
    client = TongyiLLMClient(api_key=os.getenv("DASHSCOPE_API_KEY"))
    ctx = DummyContext()
    candidates = ["refund_request", "faq_hours"]
    result = client.recognize_intent("我想退款", ctx, candidates)
    assert result.intent_id in candidates, f"意图应落在候选集内: {candidates}"

