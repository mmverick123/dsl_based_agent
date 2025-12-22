import textwrap
from typing import List

from src.dsl.parser import Parser
from src.llm.base import IntentResult, LLMClient
from src.runtime.actions import build_default_registry
from src.runtime.context import RuntimeContext
from src.runtime.executor import Executor


class StubLLM(LLMClient):
    """Deterministic intent responder for tests."""

    def __init__(self, responses: List[IntentResult]):
        self.responses = responses
        self.model = "stub"

    def recognize_intent(self, utterance, context, candidate_intents):
        if not self.responses:
            return IntentResult(intent_id="unknown", confidence=0.0, slots={})
        return self.responses.pop(0)


def build_executor(script: str, responses: List[IntentResult]) -> Executor:
    bot = Parser().parse(textwrap.dedent(script))
    ctx = RuntimeContext(bot_id=bot.bot_id, initial_state=bot.initial_state())
    llm = StubLLM(responses)
    registry = build_default_registry()
    return Executor(bot_definition=bot, context=ctx, llm_client=llm, action_registry=registry)


def test_executor_goto_and_end():
    script = """
    bot demo

    state start:
      entry:
        reply "hello"

      on_intent go:
        reply "go"
        goto second

      fallback:
        reply "fallback"
        continue

    state second:
      entry:
        reply "entered second"

      on_intent done:
        reply "bye"
        end
    """
    responses = [
        IntentResult(intent_id="go", confidence=1.0, slots={}),
        IntentResult(intent_id="done", confidence=1.0, slots={}),
    ]
    executor = build_executor(script, responses)

    boot = executor.bootstrap()
    assert any(r.payload.get("text") == "hello" for r in boot)

    r1 = executor.handle_user_input("step1")
    texts = [r.payload.get("text") for r in r1 if r.payload]
    assert "go" in texts and "entered second" in texts
    assert executor.context.current_state == "second"

    r2 = executor.handle_user_input("step2")
    texts2 = [r.payload.get("text") for r in r2 if r.payload]
    assert "bye" in texts2
    assert executor.is_active is False


def test_executor_condition_and_fallback():
    script = """
    bot demo

    state ask_amount:
      entry:
        reply "please provide amount"

      on_intent pay if slots.amount:
        reply "ok"
        end

      fallback:
        reply "need amount"
        continue
    """
    responses = [
        IntentResult(intent_id="pay", confidence=1.0, slots={"amount": 10}),
    ]
    executor = build_executor(script, responses)
    executor.bootstrap()
    r = executor.handle_user_input("pay now")
    texts = [res.payload.get("text") for res in r if res.payload]
    assert "ok" in texts
    assert executor.is_active is False

    # Fallback path with missing slot
    responses2 = [
        IntentResult(intent_id="pay", confidence=1.0, slots={}),
    ]
    executor2 = build_executor(script, responses2)
    executor2.bootstrap()
    r_fb = executor2.handle_user_input("pay now")
    fb_texts = [res.payload.get("text") for res in r_fb if res.payload]
    assert "need amount" in fb_texts
    assert executor2.is_active is True

