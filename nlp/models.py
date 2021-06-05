from sqlalchemy import Column, DateTime, Integer, String, Numeric, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from db import Base


class Message(Base):
    __tablename__ = 'message'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    content = Column(String)
    created_at = Column(DateTime)
    mentions = Column(String, nullable=True)
    channel_mentions = Column(String, nullable=True)
    jump_url = Column(String, nullable=True)

    author_id = Column(BigInteger, ForeignKey('user.id'), nullable=False)
    author = relationship('User', backref='messages', lazy='selectin')

    reference_id = Column(BigInteger, ForeignKey(id), nullable=True)
    reference = relationship('Message', backref='replies', lazy='selectin', remote_side=id)
