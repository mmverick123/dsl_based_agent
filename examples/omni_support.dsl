bot omni_support

state router:
  entry:
    reply "您好，我可以处理退款、物流查询、人工转接。请直接描述需求。"

  on_intent refund_request:
    goto refund_flow

  on_intent logistics_track:
    goto logistics_flow

  on_intent need_human:
    handover "人工客服"
    end

  fallback:
    reply "可处理：退款、物流、人工。如需人工可直接说“转人工”。"
    continue

state refund_flow:
  entry:
    reply "已进入退款流程，请提供订单号和退款原因。"

  on_intent refund_request if slots.order_id and slots.reason:
    call_api fetch_order order_id=slots.order_id
    set ticket_reason = slots.reason
    goto refund_amount

  fallback:
    reply "需要订单号和退款原因才能继续。"
    continue

state refund_amount:
  entry:
    reply "请确认退款金额。"

  on_intent confirm_amount if slots.amount:
    set refund_amount = slots.amount
    call_api create_refund order_id=slots.order_id amount=slots.amount
    reply "退款申请已提交，稍后短信通知结果。"
    end

  fallback:
    reply "请提供明确的退款金额。"
    continue

state logistics_flow:
  entry:
    reply "请输入订单号或运单号，我来查询物流。"

  on_intent logistics_track if slots.order_id:
    call_api query_logistics order_id=slots.order_id
    reply "已查询最新物流节点，将很快返回结果。"
    end

  fallback:
    reply "未获取到订单号，请提供订单号或运单号。"
    continue

