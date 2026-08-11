"""快速测试闲鱼连接"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app", "platforms", "xianyu_sdk"))

# 读取配置
with open("config/settings.json") as f:
    settings = json.load(f)
cfg = json.loads(settings.get("platform_config", "{}"))
cookie = cfg.get("app_key", "")
unb = cfg.get("seller_id", "")

print(f"Cookie长度: {len(cookie)}")
print(f"UNB: {unb}")
print(f"Cookie前100字: {cookie[:100]}")

if not cookie:
    print("❌ 未找到Cookie")
    sys.exit(1)

from goofish_apis import XianyuApis
from utils.goofish_utils import trans_cookies, generate_device_id

cookies = trans_cookies(cookie)
device_id = generate_device_id(cookies.get("unb", unb))
api = XianyuApis(cookies, device_id)

# 测试获取Token
try:
    token = api.get_token()
    print(f"✅ Token获取成功: {token[:50]}...")
    
    # 测试获取商品（随便一个ID）
    try:
        info = api.get_item_info("891198795482")
        if info:
            print(f"✅ 商品查询成功: {info.get('title', 'N/A')}")
        else:
            print("⚠️ 商品不存在（正常）")
    except Exception as e:
        print(f"⚠️ 商品查询失败（可能未登录）: {e}")
        
except Exception as e:
    print(f"❌ Token获取失败: {e}")
