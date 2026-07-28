BLOCKED_WORDS = {
    "微信",
    "QQ",
    "支付宝",
    "银行卡",
    "线下",
    "电话号码",
    "手机号",
    "身份证",
}
REPLACEMENT = "[安全提醒] 请通过平台官方渠道沟通，不要透露个人联系方式。"


def filter_output(text: str) -> str:
    for word in BLOCKED_WORDS:
        if word in text:
            return REPLACEMENT
    return text
