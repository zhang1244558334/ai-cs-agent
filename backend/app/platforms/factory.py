import json

from app.core.config import settings

from .adapters import JdAdapter, PddAdapter, TaobaoAdapter, XianyuAdapter
from .base import IAfterSaleService, ILogisticsService, IOrderService
from .mock_adapter import MockAdapter

_ADAPTERS = {
    "mock": MockAdapter,
    "xianyu": XianyuAdapter,
    "taobao": TaobaoAdapter,
    "jd": JdAdapter,
    "pdd": PddAdapter,
}


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

    @classmethod
    def switch_provider(cls, new_provider: str):
        """热切换平台"""
        if new_provider not in _ADAPTERS:
            raise ValueError(f"不支持的平台: {new_provider}，可用: {list(_ADAPTERS.keys())}")
        settings.platform.provider = new_provider

    def get_adapter(self) -> IOrderService | ILogisticsService | IAfterSaleService:
        adapter_cls = _ADAPTERS.get(self.provider)
        if adapter_cls is None:
            raise NotImplementedError(
                f"平台 '{self.provider}' 未注册，可用: {list(_ADAPTERS.keys())}"
            )
        # 闲鱼传入凭证
        if self.provider == "xianyu":
            return self._build_xianyu()
        return adapter_cls()

    def _build_xianyu(self):
        """从配置中读取闲鱼凭证"""
        config_str = getattr(settings, "platform_config", "") or ""
        try:
            cfg = json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            cfg = {}
        return XianyuAdapter(
            cookies_str=cfg.get("app_key", ""),
            seller_id=cfg.get("seller_id", ""),
        )
