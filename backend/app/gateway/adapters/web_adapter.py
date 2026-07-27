from ..interfaces.bot_platform import BotMessage, BotStatus, IBotPlatform


class WebAdapter(IBotPlatform):
    def __init__(self):
        self._connected = False

    async def connect(self, config: dict) -> bool:
        self._connected = True
        return True

    async def disconnect(self):
        self._connected = False

    async def send_message(self, msg: BotMessage) -> bool:
        return self._connected

    async def on_message(self):
        if False:
            yield

    async def get_status(self) -> BotStatus:
        return BotStatus(connected=self._connected, platform="web")

    async def reconnect(self) -> bool:
        self._connected = True
        return True
