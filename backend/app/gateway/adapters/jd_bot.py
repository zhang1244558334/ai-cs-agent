"""
京东智能客服机器人（骨架）。

接入方式：京东开放平台宙斯 API（需要企业资质）
消息通道：京东IM消息接口
SDK：京东官方 SDK

TODO：接入真实 API 后替换下面逻辑。
"""
import asyncio


class JdBot:
    def __init__(self, app_key: str = "", app_secret: str = "", access_token: str = ""):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token

    async def start(self):
        print("[JdBot] 京东机器人骨架已就绪，等待接入真实API")
        while True:
            await asyncio.sleep(60)


async def run_jd_bot(app_key: str = "", app_secret: str = "", access_token: str = ""):
    bot = JdBot(app_key, app_secret, access_token)
    await bot.start()
