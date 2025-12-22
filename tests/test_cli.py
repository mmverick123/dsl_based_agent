import textwrap

from src.cli import main as cli_main


def test_cli_with_mock_llm(monkeypatch, capsys, tmp_path):
    script_path = tmp_path / "demo.dsl"
    script_path.write_text(
        textwrap.dedent(
            """
            bot demo

            state greeting:
              entry:
                reply "welcome"

              on_intent refund_request:
                reply "ok refund"
                end

              fallback:
                reply "fallback"
                continue
            """
        ),
        encoding="utf-8",
    )

    # Prepare CLI args to use mock llm
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--script", str(script_path), "--mock-llm"],
    )

    # Simulate user inputs then exit
    inputs = iter(["退款", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    cli_main()

    out = capsys.readouterr().out
    assert "welcome" in out
    assert "ok refund" in out or "fallback" in out

