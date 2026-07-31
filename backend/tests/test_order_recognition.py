"""订单识别状态机（Phase 8 第二期）单元测试"""
import pytest
from app.agents.logistics_agent import LogisticsAgent
from app.api.routes.chat import _extract_order_no
from app.core.config import settings
from app.platforms.mock_adapter import _PHONE_TAIL


def test_extract_order_no_mock_order():
    assert _extract_order_no("我的订单 MOCK20260731001 到哪了") == "MOCK20260731001"


def test_extract_order_no_numeric_long_order():
    assert _extract_order_no("订单号 20260731001 查询物流") == "20260731001"


def test_extract_order_no_missing():
    assert _extract_order_no("我的快递到哪了") is None


def _capture_stream(captured: list):
    def _chat_stream(messages):
        captured.append(messages)

        async def _gen():
            yield "[DONE]"

        return _gen()

    return _chat_stream


@pytest.mark.asyncio
async def test_no_order_no_asks_for_order(monkeypatch):
    """无订单号时 system 追加询问订单号，且不调用 get_tracking"""
    agent = LogisticsAgent()
    captured: list = []
    monkeypatch.setattr(agent.llm, "chat_stream", _capture_stream(captured))

    def _no_adapter():
        raise AssertionError("不应调用 adapter / get_tracking")

    monkeypatch.setattr(agent.gateway, "get_adapter", _no_adapter)

    async for _ in agent.chat_stream([{"role": "user", "content": "我的快递到哪了"}]):
        pass

    content = captured[0][0]["content"]
    assert "询问订单号" in content
    assert "不要编造物流信息" in content
    assert "实时物流信息" not in content


@pytest.mark.asyncio
async def test_verify_no_tail_does_not_query(monkeypatch):
    """verify 开启、无手机尾号时不查轨迹，提示询问尾号"""
    monkeypatch.setattr(settings.platform, "verify", True)
    agent = LogisticsAgent()
    captured: list = []
    monkeypatch.setattr(agent.llm, "chat_stream", _capture_stream(captured))

    def _no_adapter():
        raise AssertionError("不应调用 adapter / get_tracking")

    monkeypatch.setattr(agent.gateway, "get_adapter", _no_adapter)

    async for _ in agent.chat_stream(
        [{"role": "user", "content": "查一下我的快递现在到哪了"}],
        order_no="MOCK20260731001",
    ):
        pass

    content = captured[0][0]["content"]
    assert "请向用户询问手机尾号" in content
    assert "实时物流信息" not in content


@pytest.mark.asyncio
async def test_verify_wrong_tail_does_not_query(monkeypatch):
    """verify 开启、手机尾号不匹配时不查轨迹，提示验证失败"""
    monkeypatch.setattr(settings.platform, "verify", True)
    assert _PHONE_TAIL["MOCK20260731001"] == "8888"
    agent = LogisticsAgent()
    captured: list = []
    monkeypatch.setattr(agent.llm, "chat_stream", _capture_stream(captured))

    def _no_adapter():
        raise AssertionError("不应调用 adapter / get_tracking")

    monkeypatch.setattr(agent.gateway, "get_adapter", _no_adapter)

    async for _ in agent.chat_stream(
        [{"role": "user", "content": "订单 MOCK20260731001 尾号9999"}],
        order_no="MOCK20260731001",
    ):
        pass

    content = captured[0][0]["content"]
    assert "订单验证失败" in content
    assert "实时物流信息" not in content


@pytest.mark.asyncio
async def test_verify_correct_tail_queries_tracking(monkeypatch):
    """verify 开启、手机尾号匹配时正常查轨迹"""
    monkeypatch.setattr(settings.platform, "verify", True)
    agent = LogisticsAgent()
    captured: list = []
    monkeypatch.setattr(agent.llm, "chat_stream", _capture_stream(captured))

    async for _ in agent.chat_stream(
        [{"role": "user", "content": "订单 MOCK20260731001 尾号8888"}],
        order_no="MOCK20260731001",
    ):
        pass

    content = captured[0][0]["content"]
    assert "实时物流信息" in content
    assert "顺丰速运" in content
