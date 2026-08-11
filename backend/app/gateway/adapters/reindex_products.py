"""
手动入口：批量将已知商品灌入ChromaDB知识库。
启动时若 REINDEX_PRODUCTS=true 则执行一次。
"""
import json
import sys
import os

# 确保 SDK 可导入
_sdk = os.path.join(os.path.dirname(__file__), "..", "..", "platforms", "xianyu_sdk")
if _sdk not in sys.path:
    sys.path.insert(0, _sdk)


def _parse_cookies(cookies_str: str) -> dict:
    """
    兼容多种 cookies 输入格式：
    - 已经是 dict → 直接返回
    - JSON 字符串 → json.loads
    - 原始 cookie 字符串 (含 "=") → 用 trans_cookies 解析
    """
    if isinstance(cookies_str, dict):
        return cookies_str

    if not isinstance(cookies_str, str) or not cookies_str.strip():
        return {}

    # 尝试 JSON 解析
    stripped = cookies_str.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            return json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            pass

    # 原始 cookie 字符串: "key1=val1; key2=val2"
    if "=" in stripped:
        from utils.goofish_utils import trans_cookies
        return trans_cookies(stripped)

    # fallback
    from utils.goofish_utils import trans_cookies
    return trans_cookies(stripped)


def _extract_item(info: dict) -> dict:
    """
    从 get_item_info 返回的响应中提取商品 data dict。
    兼容多种 MTOP 响应结构：
      - info["data"]["itemDO"]
      - info["data"] 本身就是 item
      - info["itemDO"]
      - info["result"]["itemDO"]
      - info["result"]
    """
    if not isinstance(info, dict):
        return {}

    # 候选路径列表
    candidates = [
        ["data", "itemDO"],
        ["data"],
        ["itemDO"],
        ["result", "itemDO"],
        ["result"],
    ]

    for path in candidates:
        node = info
        for key in path:
            if isinstance(node, dict):
                node = node.get(key, {})
            else:
                node = {}
                break
        # 如果 node 是 dict 且包含 itemId 或 title 之类字段，认为它就是商品数据
        if isinstance(node, dict) and node:
            # 进一步确认：含有关键字段 itemId / title / price 之一
            if any(k in node for k in ("itemId", "title", "price", "item_id")):
                return node

    # 如果所有候选都没命中，尝试在整个响应中递归查找第一个含 itemId 的 dict
    def _find_item(data, depth=0):
        if depth > 5 or not isinstance(data, (dict, list)):
            return None
        if isinstance(data, dict):
            if "itemId" in data or "item_id" in data:
                return data
            for v in data.values():
                result = _find_item(v, depth + 1)
                if result:
                    return result
        elif isinstance(data, list):
            for v in data:
                result = _find_item(v, depth + 1)
                if result:
                    return result
        return None

    found = _find_item(info)
    return found if found else {}


def index_all_known_items(item_ids: list[str], cookies_str: str):
    """
    批量索引商品到 ChromaDB 知识库。

    Args:
        item_ids: 闲鱼商品ID列表
        cookies_str: 闲鱼登录cookies（支持 dict / JSON 字符串 / 原始cookie字符串）
    """
    if not item_ids:
        print("[Reindex] 无商品需要索引")
        return

    from goofish_apis import XianyuApis
    from utils.goofish_utils import generate_device_id
    from app.knowledge.product_indexer import ProductIndexer

    cookies = _parse_cookies(cookies_str)
    if not cookies:
        print("[Reindex] cookies 解析为空，无法初始化 API")
        return

    myid = cookies.get("unb", "")
    device_id = generate_device_id(myid)
    api = XianyuApis(cookies, device_id)

    # 刷新token（必须在 get_item_info 之前）
    token_resp = api.get_token()
    ret = token_resp.get("ret", "")
    if isinstance(ret, list):
        ret = ret[0] if ret else ""
    if "SUCCESS" not in str(ret):
        print(f"[Reindex] token刷新失败: {ret}")
        return
    print(f"[Reindex] token刷新成功")

    indexer = ProductIndexer()
    success = 0
    skipped = 0
    failed = 0

    for item_id in item_ids:
        try:
            info = api.get_item_info(item_id)

            # 调试：打印返回值结构
            info_keys = list(info.keys()) if isinstance(info, dict) else type(info).__name__
            info_preview = str(info)[:200]
            print(f"[Reindex] {item_id} 返回值类型键: {info_keys}")
            print(f"[Reindex] {item_id} 返回值预览(前200字符): {info_preview}")

            raw_item = _extract_item(info)
            if not raw_item:
                print(f"[Reindex] 商品 {item_id} 无数据（尝试了多种路径仍未找到 itemDO），跳过")
                skipped += 1
                continue

            print(f"[Reindex] 商品 {item_id} 提取成功，字段: {list(raw_item.keys())[:10]}")

            result = indexer.index_item(item_id, raw_item)
            if result:
                success += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"[Reindex] 商品 {item_id} 索引异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"[Reindex] 完成: 成功={success}, 跳过={skipped}, 失败={failed}")
