from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

from src.dsl.parser import Parser
from src.llm.base import LLMError
from src.llm.mock import MockLLMClient
from src.runtime.actions import ActionResult, build_default_registry
from src.runtime.context import RuntimeContext
from src.runtime.executor import Executor


def build_llm(args):
    if args.mock_llm:
        return MockLLMClient()
    # 延迟导入，避免在仅使用 mock 时强依赖 dashscope
    from src.llm.tongyi import TongyiLLMClient

    api_key = args.api_key or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("未提供 dashscope API Key，可使用 --mock-llm 进行本地调试。")
    return TongyiLLMClient(api_key=api_key, model=args.model)


def render_results(results: List[ActionResult]) -> None:
    for result in results:
        if result.type == "reply":
            print(f"机器人> {result.payload.get('text', '')}")
        elif result.type == "handover":
            print(f"机器人> {result.message}")
        elif result.type == "system":
            print(f"[系统]{result.message}")
        elif result.type == "action_error":
            print(f"[动作错误]{result.message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="领域特定客服 DSL 解释器 CLI")
    parser.add_argument("--script", required=True, help="DSL 脚本文件路径")
    parser.add_argument("--model", default="qwen-plus", help="通义千问模型名称")
    parser.add_argument("--api-key", help="DashScope API Key，若缺省则读取环境变量")
    parser.add_argument("--mock-llm", action="store_true", help="使用规则引擎替代 LLM 调试")
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        raise FileNotFoundError(f"脚本不存在: {script_path}")
    script_text = script_path.read_text(encoding="utf-8")

    bot_def = Parser().parse(script_text)
    context = RuntimeContext(bot_id=bot_def.bot_id, initial_state=bot_def.initial_state())
    registry = build_default_registry()

    try:
        llm_client = build_llm(args)
    except (ValueError, LLMError) as exc:
        print(f"[LLM 初始化失败] {exc}")
        return

    executor = Executor(
        bot_definition=bot_def,
        context=context,
        llm_client=llm_client,
        action_registry=registry,
    )

    render_results(executor.bootstrap())

    while executor.is_active:
        try:
            user_input = input("用户> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已终止会话。")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("用户主动结束会话。")
            break
        results = executor.handle_user_input(user_input)
        render_results(results)

    print("对话结束。")


if __name__ == "__main__":
    main()

