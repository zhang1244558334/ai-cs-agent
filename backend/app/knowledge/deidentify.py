import re

# 去标识化：将企业名、商品名替换为泛化词
# 用于跨企业知识共享时保护隐私
DEIDENTIFY_PATTERNS = [
    (re.compile(r"(本公司|我司|我们公司)\s*"), "某企业 "),
    (re.compile(r"(?:商品|产品)[""「『](.+?)[""」』]"), "某商品"),
    (re.compile(r"[A-Z][a-z]+[A-Z][a-z]+\d*"), "某品牌型号"),  # iPhone15, MacBookPro 等
    (re.compile(r"定价[：:]?\d+[.,]?\d*"), "定价X元"),
    (re.compile(r"优惠价[：:]?\d+[.,]?\d*"), "优惠价X元"),
]


def deidentify(text: str) -> str:
    """将文本中的企业标识信息替换为泛化词"""
    for pattern, replacement in DEIDENTIFY_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
