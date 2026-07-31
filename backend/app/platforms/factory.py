from app.core.config import settings

from .base import IAfterSaleService, ILogisticsService, IOrderService
from .mock_adapter import MockAdapter

_SUPPORTED_PROVIDERS = {"mock"}


class PlatformGateway:
    def __init__(
        self,
        provider: str | None = None,
        timeout: float | None = None,
        retry: int | None = None,
        shadow: bool | None = None,
    ):
        self.provider = provider or settings.platform.provider
        self.timeout = timeout if timeout is not None else settings.platform.timeout
        self.retry = retry if retry is not None else settings.platform.retry
        self.shadow = shadow if shadow is not None else settings.platform.shadow

    def get_adapter(self) -> IOrderService | ILogisticsService | IAfterSaleService:
        if self.provider == "mock":
            return MockAdapter()
        raise NotImplementedError(
            f"platform provider '{self.provider}' not implemented, only 'mock' is supported"
        )
