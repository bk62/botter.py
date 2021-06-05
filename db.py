from sqlalchemy import Table, Column, Integer, ForeignKey, String, BigInteger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import create_engine
import settings

Base = declarative_base()
engine = create_async_engine(settings.DB_URL, **settings.DB_ENGINE_KWARGS)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Guild(Base):
    __tablename__ = 'guild'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String, nullable=True)

    def __repr__(self):
        return f"Server({self.name!r}, {self.discord_id!r})"


class User(Base):
    __tablename__ = 'user'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String, nullable=True)

    def __repr__(self):
        return f"User({self.name!r}, {self.discord_id!r})"


class Channel(Base):
    __tablename__ = 'channel'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String, nullable=True)

    guild_id = Column(BigInteger, ForeignKey('guild.id'), nullable=True)
    guild = relationship('Guild', backref='channels', lazy='selectin')

    def __repr__(self):
        return f"Channel({self.name!r}, {self.discord_id!r})"


def get_session():
    return sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def get_sync_engine():
    return create_engine(settings.DB_URL.replace('aiosqlite', 'pysqlite'), **settings.DB_ENGINE_KWARGS)


def create_db():
    Base.metadata.create_all(engine)


def drop_db():
    Base.metadata.drop_all(engine)
