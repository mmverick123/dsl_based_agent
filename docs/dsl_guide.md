# DSL 脚本编写指南

## 1. 基本结构
```
bot <bot_id>

state <state_id>:
  entry:
    <action...>

  on_intent <intent_id> [if <condition>]:
    <action...>
    [goto <state_id>]
    [end|continue]

  fallback:
    <action...>
    [goto ... / end / continue]
```
- 首行必须声明 `bot`。
- 每个 `state` 块用冒号结尾，内部缩进 2 空格。
- `entry`/`on_intent`/`fallback` 行下方再缩进 2 空格书写动作。
- `#` 开头为单行注释，整行忽略；空行仅起分隔作用。

## 2. 完整文法定义
采用 EBNF 表示，`Indent` 表示相对缩进（2 个空格）。

```
Script          ::= BotDecl NEWLINE StateBlock+
BotDecl         ::= "bot" Identifier
StateBlock      ::= "state" Identifier ":" NEWLINE Indent StateBody Dedent
StateBody       ::= (EntryBlock | TransitionBlock | FallbackBlock)+
EntryBlock      ::= "entry:" NEWLINE Indent ActionLines Dedent
TransitionBlock ::= "on_intent" Identifier [ "if" Condition ] ":" NEWLINE
                    Indent FlowBlock Dedent
FallbackBlock   ::= "fallback:" NEWLINE Indent FlowBlock Dedent

FlowBlock       ::= ActionLines [GotoLine] [DirectiveLine]
ActionLines     ::= ActionLine+

ActionLine      ::= ActionName [Argument+] NEWLINE
Argument        ::= QuotedString | Identifier | KeyValue
KeyValue        ::= Identifier "=" ValueToken
GotoLine        ::= "goto" Identifier NEWLINE
DirectiveLine   ::= ("end" | "continue") NEWLINE
Condition       ::= PythonExpression  ; 在运行期加以求值

Identifier      ::= /[A-Za-z_][A-Za-z0-9_\-]*/
QuotedString    ::= '"' <任何非引号字符，可含空格> '"'
ValueToken      ::= QuotedString | Identifier | NumberLiteral
```

**缩进规则**  
1. `state`、`entry`、`on_intent`、`fallback` 等关键字必须处于父级的下一层缩进（2 个空格）。  
2. 任何同级块必须保持相同缩进，否则解析器报 “缩进层级错误”。  
3. 动作行不允许空缩进；若需要空行，请使用纯空行（解释器会忽略）。

**字符串与参数**  
- 推荐使用双引号包裹包含空格或中文的文本（`reply "欢迎光临"`）。  
- 未加引号的 `Identifier` 视为变量名或常量字面量。  
- `key=value` 与 `key = value` 等价；值同样支持引用/常量/变量。

## 3. 动作语法
| 动作 | 写法示例 | 说明 |
| --- | --- | --- |
| reply | `reply "您好"` 或 `reply text="欢迎"` | 向用户输出文本。|
| set | `set ticket_reason = slots.reason` | 写入上下文变量；`key=value` 或位置参数。|
| call_api | `call_api create_refund order_id=slots.order_id amount=slots.amount` | 模拟外部接口调用，参数以 `key=value` 形式。|
| handover | `handover "人工客服"` | 返回人工转接提示。|
| log | `log "调试信息"` | 写入内部日志，不向用户展示。|

可通过注册表扩展更多动作，只需在 Python 端向 `ActionRegistry` 注册同名 handler。

## 4. 条件表达式
- 写在 `on_intent ... if <expr>:` 中。
- 表达式在运行期通过受限 `eval` 求值，可访问：
  - `slots.<name>`：LLM 识别出的槽位。
  - `vars.<name>`：会话变量（`set` 动作写入）。
  - `context`：`RuntimeContext` 本体（如 `context.metadata`）。
- 使用标准 Python 布尔语法，例如：
  - `slots.order_id and slots.reason`
  - `slots.amount and float(slots.amount) > 0`
- 表达式错误不会中断执行，但会导致条件判定为 `False` 并记录栈追踪。

## 5. 控制指令
- `goto <state_id>`：跳转到指定状态，并立即执行目标状态的 `entry` 动作。
- `end`：结束对话，CLI 会提示“对话结束”并停止继续读取输入。
- `continue`：保持当前状态，等待下一轮输入。
- 同一流程块中 `goto` 与 `end/continue` 最多各出现一次，顺序不限；若都未出现则默认停留在当前状态。

## 6. Fallback 机制
- 每个 `state` 可定义 `fallback`。
- 当所有 `on_intent` 均未匹配（包括条件为 False 或意图不在候选中）时触发。
- 常见用途：提示缺失信息、记录失败次数、调用 `handover` 转人工、回退到路由状态等。

## 7. 示例片段
```
state router:
  entry:
    reply "您好，我可以处理退款、物流查询或人工转接。"

  on_intent refund_request:
    goto refund_flow

  on_intent need_human if vars.fail_count >= 2:
    handover "人工客服"
    end

  fallback:
    set fail_count = vars.fail_count + 1
    reply "还没识别您的需求，请说明退款/物流/人工。"
    continue
```

## 8. 编写建议
- 采用有意义的 intent/state 命名，例如 `refund_verify`, `logistics_track`。
- 在 `entry` 中给出欢迎语或说明本状态需要的信息。
- 复杂流程可拆分多个状态，避免在单状态内堆积过多动作。
- 优先使用 `slots.xxx` 判断槽位是否齐全，再进入下一状态。
- 使用 `log` 记录关键路径，便于调试；`call_api` 可模拟真实系统交互，后续可替换为实际 handler。

## 9. 示例文件
- `examples/refund_bot.dsl`：两阶段退款流程，可直接用于 CLI 演示：  
  `python -m src.cli --script examples/refund_bot.dsl --mock-llm`

