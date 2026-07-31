from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


class TraceNode(BaseModel):
    time: Optional[str] = None
    node: Optional[str] = None
    city: Optional[str] = None


class OrderInfo(BaseModel):
    order_no: Optional[str] = None
    status: Optional[str] = None
    total_amount: Optional[int] = None
    items: list = Field(default_factory=list)
    can_refund: Optional[bool] = None
    refund_deadline: Optional[str] = None


class TrackingInfo(BaseModel):
    order_no: Optional[str] = None
    carrier: Optional[str] = None
    tracking_no: Optional[str] = None
    status: Optional[str] = None
    trace: list[TraceNode] = Field(default_factory=list)
    eta: Optional[str] = None


class AfterSaleInfo(BaseModel):
    service_no: Optional[str] = None
    status: Optional[str] = None
    refund_amount: Optional[int] = None
    progress: list = Field(default_factory=list)


class IOrderService(ABC):
    @abstractmethod
    async def get_order(self, order_no: str) -> Optional[OrderInfo]:
        raise NotImplementedError


class ILogisticsService(ABC):
    @abstractmethod
    async def get_tracking(self, order_no: str) -> Optional[TrackingInfo]:
        raise NotImplementedError


class IAfterSaleService(ABC):
    @abstractmethod
    async def create_refund(self, order_no: str, reason: str) -> Optional[AfterSaleInfo]:
        raise NotImplementedError

    @abstractmethod
    async def query_after_sale(self, service_no: str) -> Optional[AfterSaleInfo]:
        raise NotImplementedError
