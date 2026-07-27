class BotOrchestrator:
    def __init__(self):
        self._adapters = {}

    def register(self, platform: str, adapter):
        self._adapters[platform] = adapter

    async def route_message(self, platform: str, msg) -> str:
        return "default"

    async def dispatch(self, platform: str, message):
        adapter = self._adapters.get(platform)
        if not adapter:
            raise ValueError(f"No adapter for platform: {platform}")
