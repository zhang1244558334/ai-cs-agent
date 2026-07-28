BLOCKED_WORDS = {
    "微信", "QQ", "支付宝", "银行卡", "线下", "电话号码", "手机号", "身份证",
    # 脏话
    "操你妈", "傻逼", "草泥马", "你妈逼", "废物", "去死", "滚蛋",
    "他妈", "特么", "操蛋", "混蛋", "王八蛋", "狗屎", "放屁",
    "他妈的", "妈的", "靠", "我操", "操", "日",
}
REPLACEMENT = "[安全提醒] 请通过平台官方渠道沟通，不要透露个人联系方式。"


def filter_output(text: str) -> str:
    for word in BLOCKED_WORDS:
        if word in text:
            return REPLACEMENT
    return text
