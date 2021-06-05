from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from db import Base


class Currency(Base):
    __tablename__ = 'currency'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    symbol = Column(String(length=3), index=True)
    description = Column(String, nullable=True)

    guild_id = Column(BigInteger, ForeignKey('guild.id'), nullable=True)
    guild = relationship('Guild', backref='currencies', lazy='selectin')

    denominations = relationship('Denomination', back_populates='currency', lazy='selectin')

    __mapper_args__ = {"eager_defaults": True}
    # B/c of ext reloading - TODO
    __table_args__ = {'extend_existing': True}

    def __repr__(self):
        return f"Currency({self.name!r}, {self.symbol!r})"

    @classmethod
    def from_dict(cls, data_dict: dict):
        denominations = data_dict.pop('denominations', [])
        instance = cls(**data_dict)
        for name, val in denominations.items():
            denom = Denomination(name=name, value=val, currency=instance)
        return instance


class Denomination(Base):
    __tablename__ = 'currency_denomination'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(Numeric(10, 2))

    currency_id = Column(Integer, ForeignKey('currency.id'))

    currency = relationship('Currency', back_populates='denominations', lazy='selectin')

    # B/c of ext reloading - TODO
    __table_args__ = {'extend_existing': True}

    def __repr__(self):
        return f"Denomination({self.name!r}, {self.value!r}, currency={self.currency.symbol})"


class CurrencyBalance(Base):
    __tablename__ = 'wallet_currency'

    id = Column(Integer, primary_key=True)

    currency_id = Column(Integer, ForeignKey('currency.id'))
    balance = Column(Numeric(10, 2))

    wallet_id = Column(Integer, ForeignKey('wallet.id'))
    wallet = relationship('Wallet', backref='currency_balances', lazy='selectin')

    # B/c of ext reloading - TODO
    __table_args__ = {'extend_existing': True}


class Wallet(Base):
    __tablename__ = 'wallet'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='wallet', lazy='selectin')

    # B/c of ext reloading - TODO
    __table_args__ = {'extend_existing': True}

    def __repr__(self):
        return f"Wallet(user={self.user.name})"