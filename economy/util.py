from dataclasses import dataclass
from decimal import Decimal

import db
from .parsers import CurrencySpecParser, CurrencyAmountParser
from .models import Currency

# Helpers
def check_mentions_members(ctx):
    return ctx.message.mentions is not None and len(ctx.message.mentions) > 0



# replit db - default currency helpers
def _channel_currency_key(channel_id):
    return f'econ__channel_{channel_id}_dc'


def set_default_guild_currency(symbol):
    db.replit_db['econ__guild_dc'] = symbol


def set_default_channel_currency(channel_id, symbol):
    k = _channel_currency_key(channel_id)
    db.replit_db[k] = symbol


def get_default_guild_currency():
    if 'econ__guild_dc' in db.replit_db.keys():
        return db.replit_db['econ__guild_dc']


def get_default_channel_currency(channel_id=None):
    if channel_id is None:
        return get_default_guild_currency()
    k = _channel_currency_key(channel_id)
    if k in db.replit_db.keys():
        return db.replit_db[k]
    return None

# currency and orm helpers

@dataclass
class CurrencyAmount:
    """An amount of specific currency."""
    amount: Decimal
    symbol: str
    currency: Currency

    @classmethod
    def from_amounts(cls, amounts, currency: Currency):
        denom_vals = {
            denom.name: denom.value
            for denom in currency.denominations
        }
        total = sum(
            Decimal(amount_item.amount) if not amount_item.is_denomination else Decimal(amount_item.amount) * denom_vals[amount_item.type]
            for amount_item in amounts
        )
        return cls(symbol=currency.symbol, amount=total, currency=currency)
    

    def __str__(self):
        return f'{self.amount} {self.symbol}'