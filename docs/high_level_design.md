# 概要设计说明

## 1. 总体架构
```
DSL Script --> Parser --> AST --> Executor
                                  |-- RuntimeContext
                                  |-- ActionRegistry (reply/set/...)
                                  |-- LLM Client (Tongyi / Mock)
                                  |-- CLI Shell
```

系统按“配置驱动 + 解释执行”的分层理念实现，核心模块如下：

1. **DSL Parser**：读取脚本文本，输出 `BotDefinition` AST。
2. **Semantic Model**：`BotDefinition`、`StateNode`、`Transition`、`ActionNode`。
3. **RuntimeContext**：管理状态、变量、槽位、历史纪录。
4. **Executor**：解释 AST，驱动动作执行与状态跳转。
5. **ActionRegistry**：动作插件系统，提供回复、变量设置、API 调用、转人工等。
6. **LLM Client**：封装通义千问 API，并提供 Mock 实现。
7. **CLI/IO Adapter**：命令行会话循环，承载输入输出。

## 2. 运行流程
1. CLI 读取 DSL → Parser 生成 AST。
2. 初始化 `RuntimeContext`（含初始状态）、`ActionRegistry`、`LLM Client`、`Executor`。
3. `Executor.bootstrap()` 执行当前状态的 `entry` 动作。
4. 用户输入一轮话术：
   - CLI 把原始文本交给 `Executor.handle_user_input`。
   - Executor 调用 LLM Client 获取 `IntentResult(intent, confidence, slots)`。
   - 根据当前 `StateNode` 查找满足意图与条件的 `Transition`。
   - 执行 `ActionFlow`：动作序列 → `goto`/`end` 控制 → 进入新状态时执行 `entry`。
   - 若未匹配，则执行 `fallback`。
5. CLI 渲染 `ActionResult`，直至状态指令 `end` 或用户退出。

## 3. 模块接口
| 模块 | 输入 | 输出 | 关键方法 |
| --- | --- | --- | --- |
| Parser | DSL 文本 | `BotDefinition` | `parse(script_text)` |
| RuntimeContext | - | - | `push_user_message`, `set_var`, `update_slots`, `build_eval_env` |
| ActionRegistry | `ActionNode` | `List[ActionResult]` | `register(name, handler)`, `execute(action, ctx)` |
| Executor | AST + Runtime | `List[ActionResult]` | `bootstrap()`, `handle_user_input(text)` |
| LLM Client | 话术、候选意图 | `IntentResult` | `recognize_intent(utterance, context, intents)` |
| CLI | 用户输入 | 屏幕输出 | `render_results`, 主循环 |

## 4. 数据结构
- **ActionFlow**：`actions`, `goto`, `directive(end|continue)`。
- **IntentResult**：`intent_id`, `confidence`, `slots`, `raw`。
- **ActionResult**：`type`, `payload`, `success`, `message`。
- **RuntimeContext**：`variables`, `slots`, `history`, `current_state`, `session_id`。

## 5. LLM 交互
- 采用 DashScope `Generation.call`，系统提示包含候选意图，要求输出 JSON。
- `TongyiLLMClient` 统一解析响应，若失败抛出 `LLMError`。
- 提供 `MockLLMClient` 供离线/自动化测试。

## 6. 错误与兜底
- Parser 检测缩进、语法、重复状态，抛出 `DSLParseError`。
- Executor 捕获动作异常并以 `action_error` 形式返回 CLI。
- LLM 失败或未匹配意图 → 触发 `fallback` 或默认提示。

## 7. 扩展点
- 新动作：通过 `ActionRegistry.register` 即可。
- 新 LLM 或策略：实现 `LLMClient` 协议替换。
- 条件表达式：`RuntimeContext.build_eval_env` 可扩展变量、工具函数。
- IO 适配：CLI 可替换为 HTTP 服务或对接 IM。*** End Patch

