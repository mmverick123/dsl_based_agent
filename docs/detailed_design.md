# 详细设计说明

## 1. DSL 解析器
- **输入**：UTF-8 文本，缩进 2 空格。
- **主要类**：`Parser`
  - `parse(text) -> BotDefinition`：入口。
  - `_tokenize`：去除空行、注释，记录缩进与行号。
  - `_parse_state`：解析 `state` 块，包含 `entry/on_intent/fallback`。
  - `_parse_action_line`：使用 `shlex` 拆分动作字符串，支持 `key=value` 与 `key = value`。
- **错误处理**：发现非法缩进、缺冒号、重复状态、空块时抛出 `DSLParseError`（携带行号）。

## 2. 语义模型 (AST)
- `BotDefinition`: `bot_id`, `states`（保持插入顺序）。
- `StateNode`: `state_id`, `entry_actions`, `transitions`, `fallback`。
- `Transition`: `intent_id`, `condition`（字符串表达式）, `flow`。
- `ActionFlow`: `actions`（列表）、`goto`、`directive(end/continue)`。
- `ActionNode`: `name`, `positional_args`, `named_args`, `line_number`。

## 3. 运行时上下文 `RuntimeContext`
- 字段：`bot_id`, `initial_state`, `current_state`, `session_id`, `variables`, `slots`, `history`, `metadata`。
- 方法：
  - `push_user_message` / `push_bot_message`：保存最近会话内容，用于 LLM 提示及日志。
  - `update_slots`：融合 LLM 返回的槽位。
  - `set_var/get_var`：对话级变量读写。
  - `set_state`：状态切换。
  - `build_eval_env`：构造 `slots`, `vars`, `context` 的 `AttrDict`，供条件表达式安全求值。

## 4. 动作系统
- **ActionRegistry**
  - `register(name, handler)`
  - `execute(action, context)`：返回 `List[ActionResult]`。
- **ActionResult**
  - 字段：`type`, `payload`, `success`, `message`。
- **默认动作**
  - `reply`: 输出文本，写入历史。
  - `set`: 更新上下文变量。
  - `call_api`: 记录模拟外部调用。
  - `handover`: 生成人工转接提示。
  - `log`: 仅写入内部日志。
- 动作处理器可返回 `None`（表示纯副作用）。

## 5. 解释器 `Executor`
- 初始化参数：`BotDefinition`, `RuntimeContext`, `LLMClient`, `ActionRegistry`。
- `bootstrap()`：执行当前状态 `entry` 动作。
- `handle_user_input(text)`：
  1. 记录用户消息。
  2. 调用 `LLMClient.recognize_intent`，传入当前状态候选意图。
  3. 更新槽位，匹配 `Transition`（检查 `intent_id` 与 `condition`）。
  4. 执行 `ActionFlow`：依次执行 `ActionNode`，随后处理 `goto`、`directive`。
  5. `goto` → `_enter_state` 执行目标状态 `entry`；`end` → `is_active=False` 并输出系统提示。
  6. 无匹配则执行 `fallback`，若缺省则返回默认回复。
- 条件表达式使用受限 `eval`，globals 清空，locals 为 `build_eval_env()`。
- 对动作异常提供 `ActionResult(type="action_error")`，避免中断。

## 6. LLM Client
- 接口 `LLMClient`
  - `recognize_intent(utterance, context, candidate_intents) -> IntentResult`
  - `IntentResult`: `intent_id`, `confidence`, `slots`, `raw`。
- `TongyiLLMClient`
  - 依赖 `dashscope.Generation.call`。
  - System Prompt 列出候选意图，要求返回 JSON。
  - `_extract_text` 兼容 content list / string；`_parse_json` 处理包裹文本。
  - 失败时抛出 `LLMError`。
- `MockLLMClient`
  - 关键词匹配到意图。
  - 自动填充 `order_id / amount` 等示例槽位。

## 7. CLI
- 模块 `src/cli.py`，使用 `argparse`。
- 参数：
  - `--script`: DSL 文件路径。
  - `--model`: 通义千问模型（默认 `qwen-plus`）。
  - `--api-key`: DashScope Key（也可用环境变量）。
  - `--mock-llm`: 使用 Mock，便于演示。
- 运行逻辑：
  1. 读取脚本并解析。
  2. 构建上下文、动作注册表、LLM 客户端、执行器。
  3. 输出 `bootstrap` 结果。
  4. while 循环读取用户输入，调用 `executor.handle_user_input`，渲染 `ActionResult`。
  5. 捕获 `EOF/KeyboardInterrupt`，友好退出。

## 8. 示例脚本
- `examples/refund_bot.dsl`：包含两个状态（`greeting`, `verify`），演示 `entry`、条件槽位、`call_api`、`goto`、`end`。

## 9. 依赖与配置
- `dashscope>=1.15.0`：通义千问 SDK。
- 环境变量 `DASHSCOPE_API_KEY` 或 CLI `--api-key`。
- 纯标准库实现解析与运行，无其他第三方依赖。

## 10. 日志与调试
- `RuntimeContext.metadata["logs"]` 可记录 `log` 动作。
- `metadata["api_calls"]` 记录 `call_api` 模拟参数，便于后续真实集成。

## 11. 扩展建议
- 动作系统可注册数据库/HTTP 调用等真实逻辑。
- CLI 渐进式升级为 RESTful 服务或 WebSocket Bot。
- 增加状态持久化、多会话并发管理等。*** End Patch

