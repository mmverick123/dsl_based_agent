import textwrap

import pytest

from src.dsl.parser import Parser
from src.dsl.errors import DSLParseError


def test_parser_success_creates_ast():
    script = textwrap.dedent(
        """
        bot demo

        state greeting:
          entry:
            reply "hi"

          on_intent faq_hours:
            reply "9-18"
            end
        """
    )
    bot = Parser().parse(script)
    assert bot.bot_id == "demo"
    assert "greeting" in bot.states
    state = bot.states["greeting"]
    assert len(state.entry_actions) == 1
    assert len(state.transitions) == 1
    assert state.transitions[0].intent_id == "faq_hours"


def test_parser_reports_line_number_on_error():
    script = textwrap.dedent(
        """
        bot broken

        state greeting  # missing colon
          entry:
            reply "hi"
        """
    )
    with pytest.raises(DSLParseError) as exc:
        Parser().parse(script)
    assert "line 4" in str(exc.value) or exc.value.line_number == 4

