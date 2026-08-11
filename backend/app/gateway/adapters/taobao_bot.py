"""
淘宝智能客服机器人（骨架）。

接入方式：淘宝开放平台 TOP API（个人可申请 AppKey，open.taobao.com）
消息通道：轮询淘宝 IM 消息接口（taobao.im.message.get）
SDK：pip install pyTOP 或 github.com/bububa/pyTOP

TODO：接入真实 API 后替换下面逻辑。
"""
import asyncio


class TaobaoBot:
    """淘宝AI客服机器人。收到消息→调AI引擎→自动回复。"""

    def __init__(self, app_key: str = "", app_secret: str = "", session_key: str = ""):
        self.app_key = app_key
        self.app_secret = app_secret
        self.session_key = session_key

    async def start(self):
        """启动机器人主循环（轮询淘宝IM消息）"""
        print("[TaobaoBot] 淘宝机器人骨架已就绪，等待接入真实API")
        # TODO: 轮询 taobao.im.message.get
        # TODO: 收到消息 → Router.route() → Agent.chat() → 发送回复
        while True:
            await asyncio.sleep(60)


async def run_taobao_bot(app_key: str = "", app_secret: str = "", session_key: str = ""):
    bot = TaobaoBot(app_key, app_secret, session_key)
    await bot.start()
