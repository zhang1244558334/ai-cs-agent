"""平台接口适配层（Phase 8 第一期）单元测试"""
import pytest
from app.platforms.factory import PlatformGateway
from app.platforms.mock_adapter import MockAdapter


@pytest.mark.asyncio
async def test_get_tracking_mock_20260731001():
    adapter = MockAdapter()
    info = await adapter.get_tracking("MOCK20260731001")
    assert info is not None
    assert info.carrier == "顺丰速运"
    assert info.status == "派送中"
    assert len(info.trace) >= 3


@pytest.mark.asyncio
async def test_get_tracking_unknown_order_returns_none():
    adapter = MockAdapter()
    assert await adapter.get_tracking("NOPE20269999999") is None


def test_platform_gateway_default_provider_is_mock():
    gateway = PlatformGateway()
    assert gateway.provider == "mock"
    adapter = gateway.get_adapter()
    assert isinstance(adapter, MockAdapter)
