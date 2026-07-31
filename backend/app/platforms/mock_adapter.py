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

_PHONE_TAIL = {
    "MOCK20260731001": "8888",
    "MOCK20260731002": "6666",
    "MOCK20260731003": "1234",
}


class MockAdapter(IOrderService, ILogisticsService, IAfterSaleService):
    """Mock 实现：预设假数据，不依赖网络，用于演示与测试。

    未知名订单号返回 None，不抛错。
    """

    _ORDERS = {
        "MOCK20260731001": OrderInfo(
            order_no="MOCK20260731001",
            status="派送中",
            total_amount=19900,
            items=[{"name": "保湿面霜", "qty": 1}],
            can_refund=False,
            refund_deadline=None,
        ),
        "MOCK20260731002": OrderInfo(
            order_no="MOCK20260731002",
            status="已签收",
            total_amount=8900,
            items=[{"name": "护手霜", "qty": 2}],
            can_refund=False,
            refund_deadline=None,
        ),
        "MOCK20260731003": OrderInfo(
            order_no="MOCK20260731003",
            status="已发货",
            total_amount=49900,
            items=[{"name": "电动牙刷", "qty": 1}],
            can_refund=True,
            refund_deadline="2026-08-07T23:59:59+08:00",
        ),
    }

    _TRACKING = {
        "MOCK20260731001": TrackingInfo(
            order_no="MOCK20260731001",
            carrier="顺丰速运",
            tracking_no="SF1234567890",
            status="派送中",
            trace=[
                TraceNode(time="2026-07-30T10:12:00+08:00", node="已揽收", city="杭州"),
                TraceNode(time="2026-07-30T18:40:00+08:00", node="运输中", city="杭州转运中心"),
                TraceNode(time="2026-07-31T06:20:00+08:00", node="运输中", city="上海转运中心"),
                TraceNode(time="2026-07-31T11:05:00+08:00", node="派送中", city="上海"),
            ],
            eta="今日 18:00 前送达",
        ),
        "MOCK20260731002": TrackingInfo(
            order_no="MOCK20260731002",
            carrier="中通快递",
            tracking_no="ZT0987654321",
            status="已签收",
            trace=[
                TraceNode(time="2026-07-25T09:00:00+08:00", node="已揽收", city="广州"),
                TraceNode(time="2026-07-26T02:15:00+08:00", node="运输中", city="广州转运中心"),
                TraceNode(time="2026-07-26T15:30:00+08:00", node="派送中", city="深圳"),
                TraceNode(time="2026-07-27T10:45:00+08:00", node="已签收", city="深圳"),
            ],
            eta=None,
        ),
        "MOCK20260731003": TrackingInfo(
            order_no="MOCK20260731003",
            carrier="圆通速递",
            tracking_no="YT1112131415",
            status="已发货",
            trace=[
                TraceNode(time="2026-07-31T09:30:00+08:00", node="已揽收", city="成都"),
                TraceNode(time="2026-07-31T14:50:00+08:00", node="运输中", city="成都转运中心"),
            ],
            eta="预计 48 小时内送达",
        ),
    }

    async def get_order(self, order_no: str) -> Optional[OrderInfo]:
        return self._ORDERS.get(order_no)

    async def get_tracking(self, order_no: str) -> Optional[TrackingInfo]:
        return self._TRACKING.get(order_no)

    async def create_refund(self, order_no: str, reason: str) -> Optional[AfterSaleInfo]:
        order = self._ORDERS.get(order_no)
        if not order or not order.can_refund:
            return None
        return AfterSaleInfo(
            service_no=f"AF{order_no[-6:]}",
            status="已受理",
            refund_amount=order.total_amount,
            progress=[{"time": "2026-07-31T15:00:00+08:00", "node": "申请已提交"}],
        )

    async def query_after_sale(self, service_no: str) -> Optional[AfterSaleInfo]:
        if not service_no.startswith("AF"):
            return None
        return AfterSaleInfo(
            service_no=service_no,
            status="退款审核中",
            refund_amount=19900,
            progress=[
                {"time": "2026-07-31T15:00:00+08:00", "node": "申请已提交"},
                {"time": "2026-07-31T16:20:00+08:00", "node": "商家已同意退款"},
            ],
        )
