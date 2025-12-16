bot refund_bot

state greeting:
  entry:
    reply "欢迎来到退款中心，请描述订单问题。"

  on_intent refund_request if slots.order_id and slots.reason:
    set ticket_reason = slots.reason
    call_api fetch_order order_id=slots.order_id
    goto verify

  fallback:
    reply "需要提供订单号和退款原因才能继续。"
    continue

state verify:
  entry:
    reply "已获取订单信息，请确认需退款金额。"

  on_intent confirm_amount if slots.amount:
    set refund_amount = slots.amount
    call_api create_refund order_id=slots.order_id amount=slots.amount
    reply "已提交退款申请，稍后短信通知结果。"
    end

  fallback:
    reply "请提供正确的退款金额。"
    continue

