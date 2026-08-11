"""各电商平台适配器。

XianyuAdapter 接入了 cv-cat/XianYuApis 真实API（商品查询+消息收发）。
其他平台目前复用Mock数据，接入时替换对应方法即可。
"""
import os
import sys
from typing import Optional

from .base import (
    AfterSaleInfo,
    IAfterSaleService,
    ILogisticsService,
    IOrderService,
    OrderInfo,
    TraceNode,
    TrackingInfo,
)
from .mock_adapter import MockAdapter

# 闲鱼SDK路径
_XIANYU_SDK = os.path.join(os.path.dirname(__file__), "xianyu_sdk")
if _XIANYU_SDK not in sys.path:
    sys.path.insert(0, _XIANYU_SDK)


class XianyuAdapter(MockAdapter):
    """闲鱼平台适配器 — 基于 cv-cat/XianYuApis 真实API。

    配置方式（在Settings页面"平台接入"中填写）：
      - app_key:    闲鱼 Cookie 字符串（从浏览器F12复制）
      - app_secret: 备用，暂未使用
      - seller_id:  卖家闲鱼用户ID（unb）

    已接入：商品查询、订单状态查询
    待接入（需官方API）：物流轨迹、售后单
    """

    def __init__(self, cookies_str: str = "", seller_id: str = ""):
        super().__init__()
        self.cookies_str = cookies_str
        self.seller_id = seller_id
        self._api = None

    def _get_api(self):
        """延迟初始化闲鱼API（避免导入时就需要cookie）"""
        if self._api is not None:
            return self._api
        if not self.cookies_str:
            return None
        try:
            from goofish_apis import XianyuApis
            from utils.goofish_utils import trans_cookies, generate_device_id

            cookies = trans_cookies(self.cookies_str)
            device_id = generate_device_id(cookies.get("unb", ""))
            self._api = XianyuApis(cookies, device_id)
            return self._api
        except Exception:
            return None

    async def get_order(self, order_no: str) -> Optional[OrderInfo]:
        """查询订单。优先用闲鱼API查商品信息，回退Mock。"""
        api = self._get_api()
        if api and order_no.isdigit():
            try:
                info = api.get_item_info(order_no)
                if info:
                    return OrderInfo(
                        order_no=order_no,
                        status=info.get("status", "在售"),
                        total_amount=int(float(info.get("price", "0")) * 100),
                        items=[{"name": info.get("title", "闲鱼商品"), "qty": 1}],
                        can_refund=False,
                    )
            except Exception:
                pass
        # 回退Mock
        return await super().get_order(order_no)

    async def get_tracking(self, order_no: str) -> Optional[TrackingInfo]:
        """物流轨迹。闲鱼不提供对个人的物流API，回退Mock。"""
        return await super().get_tracking(order_no)


class TaobaoAdapter(MockAdapter):
    """淘宝开放平台适配器。接入时替换数据源为淘宝TOP API。
    个人可申请AppKey: https://open.taobao.com
    SDK: pip install pyTOP 或 github.com/bububa/pyTOP
    """


class JdAdapter(MockAdapter):
    """京东开放平台适配器。接入时替换数据源为京东宙斯 API。"""


class PddAdapter(MockAdapter):
    """拼多多开放平台适配器。接入时替换数据源为拼多多多多客 API。"""
