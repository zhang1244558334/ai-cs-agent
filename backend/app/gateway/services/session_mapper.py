from app.core.database import async_session
from app.models.session import Session
from sqlalchemy import select


class SessionMapper:
    async def get_or_create(
        self, platform: str, platform_session_id: str, user_id: str
    ) -> Session:
        async with async_session() as session:
            result = await session.execute(
                select(Session).where(
                    Session.platform == platform,
                    Session.platform_session_id == platform_session_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            new_sess = Session(
                platform=platform,
                platform_session_id=platform_session_id,
                user_id=user_id,
            )
            session.add(new_sess)
            await session.commit()
            await session.refresh(new_sess)
            return new_sess
