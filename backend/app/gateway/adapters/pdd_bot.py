"""
拼多多智能客服机器人（骨架）。

接入方式：拼多多开放平台多多客 API（需要企业资质）
消息通道：拼多多IM消息接口
SDK：拼多多官方 SDK

TODO：接入真实 API 后替换下面逻辑。
"""
import asyncio


class PddBot:
    def __init__(self, client_id: str = "", client_secret: str = "", mall_id: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.mall_id = mall_id

    async def start(self):
        print("[PddBot] 拼多多机器人骨架已就绪，等待接入真实API")
        while True:
            await asyncio.sleep(60)


async def run_pdd_bot(client_id: str = "", client_secret: str = "", mall_id: str = ""):
    bot = PddBot(client_id, client_secret, mall_id)
    await bot.start()
