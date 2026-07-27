from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional


@dataclass
class BotMessage:
    platform: str
    platform_session_id: str
    user_id: str
    content: str
    message_id: str = ""
    item_id: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class BotStatus:
    connected: bool = False
    platform: str = ""
    error: Optional[str] = None


class IBotPlatform(ABC):
    @abstractmethod
    async def connect(self, config: dict) -> bool: ...

    @abstractmethod
    async def disconnect(self): ...

    @abstractmethod
    async def send_message(self, msg: BotMessage) -> bool: ...

    @abstractmethod
    async def on_message(self) -> AsyncGenerator[BotMessage, None]: ...

    @abstractmethod
    async def get_status(self) -> BotStatus: ...

    @abstractmethod
    async def reconnect(self) -> bool: ...
