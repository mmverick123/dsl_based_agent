bot faq_bot

state greeting:
  entry:
    reply "您好，这里是智能 FAQ 机器人，可以咨询营业时间、地址、电话。"

  on_intent faq_hours:
    reply "营业时间：工作日 9:00-18:00。"
    end

  on_intent faq_location:
    reply "门店地址：上海市浦东新区 XX 路 88 号。"
    end

  on_intent faq_phone:
    reply "客服电话：400-123-4567，欢迎来电。"
    end

  fallback:
    reply "抱歉未识别，请问想咨询营业时间、地址还是电话？"
    continue

