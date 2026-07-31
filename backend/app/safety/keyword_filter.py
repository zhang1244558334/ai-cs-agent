BLOCKED_WORDS = {
    # 诱导私下交易/泄露隐私（客服不能主动提供）
    "微信", "QQ", "线下", "手机号", "身份证", "电话号码", "私人电话", "私人微信",
    # 脏话（≥2 字，单字如"日/靠/操"误伤"日期/可靠"）
    "操你妈", "傻逼", "草泥马", "你妈逼", "废物", "去死", "滚蛋",
    "他妈", "特么", "操蛋", "混蛋", "王八蛋", "狗屎", "放屁",
    "他妈的", "妈的", "我操",
}
REPLACEMENT = "[安全提醒] 请通过平台官方渠道沟通，不要透露个人联系方式。"


def filter_output(text: str) -> str:
    """过滤 AI 输出中的危险词：替换命中词而非整条拦截。

    注意：支付宝/银行卡是支付 FAQ 的必答内容（退款到账路径），不得过滤。
    """
    for word in BLOCKED_WORDS:
        if word in text:
            text = text.replace(word, REPLACEMENT)
    return text
