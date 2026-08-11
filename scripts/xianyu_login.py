"""
闲鱼扫码登录 → 获取 Cookie 和 unb。
运行: python3 scripts/xianyu_login.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app", "platforms", "xianyu_sdk"))

from goofish_apis import qrcode_login
from utils.goofish_utils import get_session_cookies_str

print("正在生成登录二维码...")
print("请用闲鱼App扫描终端中的二维码\n")

api = qrcode_login(poll_interval=3.0, timeout=180.0, show_qrcode=True)

cookies_str = get_session_cookies_str(api.session)
print("\n========== 登录成功！==========")
print(f"\nCookie字符串（复制到设置页第一栏）:\n{cookies_str}")
print(f"\n卖家ID unb: {api.cookies.get('unb', '未找到')}")
