# 测试方法说明

本文档介绍本项目的测试范围、执行方式以及测试桩使用方法，便于快速回归与持续集成。

## 1. 测试范围
- **单元测试**
  - `tests/test_parser.py`：验证 DSL 解析器正常生成 AST，并对语法错误报出 `DSLParseError` 及行号。
  - `tests/test_executor.py`：使用 Stub LLM 覆盖状态跳转（goto/end）、条件分支、fallback 等关键逻辑。
  - `tests/test_cli.py`：模拟命令行参数和用户输入，走 `--mock-llm` 路径验证对话闭环。
- **示例脚本校验**
  - `examples/broken_example.dsl` 用于验证语法错误提示。
  - 其余示例（如 `refund_bot.dsl`, `faq_bot.dsl`, `omni_support.dsl`）可手动跑通或作为集成测试脚本输入。

## 2. 依赖安装
```bash
pip install -r requirements.txt
```
`requirements.txt` 已包含 `pytest` 与 `dashscope`（真实 LLM 调用时使用）。

## 3. 运行单元测试
```bash
pytest -q
```
说明：
- `tests/conftest.py` 会将项目根目录加入 `sys.path`，保证 `src.*` 导入正常。
- 若未安装 pytest，会提示找不到命令，请先执行依赖安装。

## 4. 测试桩（Mock LLM）
- 单元测试使用 `StubLLM` 或 `MockLLMClient`，无需真实 LLM Key，便于离线和 CI 环境。
- 如需集成真实通义千问，可在运行时设置环境变量 `DASHSCOPE_API_KEY` 或 CLI 传参 `--api-key`，但集成测试应避免在 CI 中暴露密钥。

## 5. 手工验证建议
- **解析报错验证**：运行 `python -m src.cli --script examples/broken_example.dsl`，应抛出带行号的 `DSLParseError`。
- **Mock 路径验证**：`python -m src.cli --script examples/refund_bot.dsl --mock-llm`，输入模拟退款话术，观察状态跳转与回复。
- **真实 LLM 验证**（需要 Key）：`python -m src.cli --script examples/refund_bot.dsl --api-key <your_key>`，可选 `--model qwen-plus/qwen-max`。

## 6. 持续集成提示
- 若接入 CI（如 GitHub Actions），推荐步骤：
  1) `pip install -r requirements.txt`
  2) `pytest -q`
- 如需运行集成测试，请将涉及密钥的 job 拆分并使用 CI Secret 注入，避免在公共日志中泄露。

## 7. 常见问题
- **找不到 pytest 命令**：未安装依赖，执行 `pip install -r requirements.txt`。
- **ImportError: No module named src...**：确认在项目根目录运行；或检查 `tests/conftest.py` 是否存在（负责把根目录加入 `sys.path`）。
- **LLM 调用失败**：Mock 测试不需要 Key；真实调用需网络可达且正确设置 `DASHSCOPE_API_KEY`。

