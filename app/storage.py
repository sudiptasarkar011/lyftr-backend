import asyncio
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Database Setup
engine = create_async_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# DB Model
class MessageDB(Base):
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, index=True) # Enforces Uniqueness
    from_msisdn = Column(String, nullable=False)
    to_msisdn = Column(String, nullable=False)
    ts = Column(DateTime, nullable=False) # Store as datetime object
    text = Column(Text, nullable=True)
    created_at = Column(String, default=datetime.utcnow().isoformat) # Server time

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with SessionLocal() as session:
        yield session