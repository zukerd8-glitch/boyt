import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from config import settings
from loguru import logger
import os

Base = declarative_base()

class MessageContext(Base):
    __tablename__ = "message_contexts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    role = Column(String)  # "user" or "bot"
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

DATABASE_URL = f"sqlite+aiosqlite:///{settings.DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    os.makedirs(os.path.dirname(settings.DB_PATH) or ".", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized at {}", settings.DB_PATH)

async def save_message(user_id: str, role: str, content: str):
    async with AsyncSessionLocal() as session:
        msg = MessageContext(user_id=user_id, role=role, content=content)
        session.add(msg)
        await session.commit()
        logger.debug("Saved message for user {} role {} content {}", user_id, role, content[:100])

async def get_last_messages(user_id: str, limit: int = 2):
    async with AsyncSessionLocal() as session:
        q = await session.execute(
            f"SELECT id, role, content, created_at FROM message_contexts WHERE user_id = :uid ORDER BY created_at DESC LIMIT :limit",
            {"uid": user_id, "limit": limit}
        )
        rows = q.fetchall()
        # rows are tuples; return reversed to get chronological order
        results = [{"role": r[1], "content": r[2]} for r in reversed(rows)]
        logger.debug("Fetched {} messages for user {}", len(results), user_id)
        return results
