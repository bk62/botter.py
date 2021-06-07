from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, BigInteger, DateTime, func
from sqlalchemy.orm import relationship


from db import Base


# Models:
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
        denominations = data_dict.pop('denominations', {})
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
    currency = relationship('Currency', lazy='selectin')

    balance = Column(Numeric(10, 2), default=0.0)

    wallet_id = Column(Integer, ForeignKey('wallet.id'))
    wallet = relationship('Wallet', back_populates='currency_balances', lazy='selectin')

    # B/c of ext reloading - TODO
    __table_args__ = {'extend_existing': True}


class Wallet(Base):
    __tablename__ = 'wallet'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='wallet', lazy='selectin')

    currency_balances = relationship('CurrencyBalance', back_populates='wallet', lazy='selectin')

    # B/c of ext reloading - TODO
    __table_args__ = {'extend_existing': True}

    def __repr__(self):
        return f"Wallet(user={self.user.name})"


class TransactionLog(Base):
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='transactions', lazy='selectin')

    related_user_id = Column(Integer, ForeignKey('user.id'))
    related_user = relationship('User', backref='transactions_related', lazy='selectin')

    currency_id = Column(Integer, ForeignKey('currency.id'))
    currency = relationship('Currency', lazy='selectin')

    amount = Column(Numeric(10, 2), default=0.0)

    note = Column(String, nullable=True)

    created = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"TransactionLog(amount={self.amount}, currency={self.currency}, user={self.user.name}, related={self.related_user.name})"
    
    def __str__(self):
        return f'{self.created} {self.amount} {self.currency.symbol} User: {self.user.name} ({self.user_id}), Related user: {self.related_user.name} ({self.related_user_id}), for {self.note}'



class RewardLog(Base):
    __tablename__ = 'reward_log'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='wallet', lazy='selectin')

    currency_id = Column(Integer, ForeignKey('currency.id'))
    currency = relationship('Currency', lazy='selectin')

    amount = Column(Numeric(10, 2), default=0.0)

    note = Column(String, nullable=True)

    created = Column(DateTime, server_default=func.now())

    __mapper_args__ = {"eager_defaults": True}
    # B/c of ext reloading - TODO
    __table_args__ = {'extend_existing': True}


    def __repr__(self):
        return f"RewardLog(amount={self.amount}, currency={self.currency}, user={self.user.name})"
    
    def __str__(self):
        return f'{self.created} {self.amount} {self.currency.symbol} to {self.user.name} ({self.user_id}) for {self.note}'