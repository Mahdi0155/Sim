# ───────────────────────── db.py ─────────────────────────

import os
import json
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime, timezone, timedelta
import secrets

DATABASE_URL = os.getenv("DATABASE_URL_ASYNC")

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    username: Mapped[str | None]
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def select_all_ids():
        return sa.select(User.id)

class FileBatch(Base):
    __tablename__ = "file_batches"
    code: Mapped[str] = mapped_column(sa.String(16), primary_key=True, default=lambda: secrets.token_urlsafe(8))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    channel_message_ids: Mapped[list[int] | None] = mapped_column(ARRAY(sa.Integer))

    @staticmethod
    def make():
        return FileBatch()

class FileItem(Base):
    __tablename__ = "file_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_code: Mapped[str] = mapped_column(sa.ForeignKey("file_batches.code", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(sa.String(16))  # photo/video/audio/document
    file_id: Mapped[str] = mapped_column(sa.Text)
    caption: Mapped[str | None]

    @staticmethod
    def from_state(batch_code: str, kind: str, file_id: str, caption: str | None):
        fi = FileItem()
        fi.batch_code = batch_code
        fi.kind = kind
        fi.file_id = file_id
        fi.caption = caption
        return fi

    @staticmethod
    def select_by_batch(code: str):
        return sa.select(FileItem).where(FileItem.batch_code == code).order_by(FileItem.id.asc())

class ForcedChannel(Base):
    __tablename__ = "forced_channels"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    link: Mapped[str] = mapped_column(sa.Text, unique=True)
    chat_id: Mapped[int | None] = mapped_column(sa.BigInteger)
    title: Mapped[str | None]

    @staticmethod
    def select_all():
        return sa.select(ForcedChannel).order_by(ForcedChannel.id.asc())

    @staticmethod
    def select_by_link(link: str):
        return sa.select(ForcedChannel).where(ForcedChannel.link == link)

class AdminUser(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)

class LinkHit(Base):
    __tablename__ = "link_hits"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.String(16), index=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger)
    ts: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def count_by_code(code: str):
        return sa.select(sa.func.count()).select_from(LinkHit).where(LinkHit.code == code)

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]

    @staticmethod
    async def get_delete_after(s):
        row = await s.get(Setting, "delete_after")
        return int(row.value) if row else None

    @staticmethod
    async def set_delete_after(s, seconds: int):
        row = await s.get(Setting, "delete_after")
        if not row:
            row = Setting(key="delete_after", value=str(seconds))
            s.add(row)
        else:
            row.value = str(seconds)

engine = create_async_engine(DATABASE_URL, future=True, pool_pre_ping=True)
DBSession = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def now_utc():
    return datetime.now(timezone.utc)

# Extra DB helpers
async def _count_users_since(delta: timedelta):
    async with DBSession() as s:
        since = now_utc() - delta
        q = sa.select(sa.func.count()).select_from(User).where(User.created_at >= since)
        return (await s.execute(q)).scalar_one() or 0

async def _count_users():
    async with DBSession() as s:
        q = sa.select(sa.func.count()).select_from(User)
        return (await s.execute(q)).scalar_one() or 0

async def _count_files():
    async with DBSession() as s:
        q = sa.select(sa.func.count()).select_from(FileItem)
        return (await s.execute(q)).scalar_one() or 0

# Monkey-patch simple methods onto DBSession for brevity
setattr(DBSession, 'count_users_since', staticmethod(_count_users_since))
setattr(DBSession, 'count_users', staticmethod(_count_users))
setattr(DBSession, 'count_files', staticmethod(_count_files))
