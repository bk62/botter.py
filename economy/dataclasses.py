from dataclasses import dataclass
from decimal import Decimal

import discord

from .models import Currency, Wallet


@dataclass
class CurrencyAmount:
    """An amount of specific currency."""
    amount: Decimal
    symbol: str
    currency: Currency = None

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
    
    @classmethod
    def copy(cls, currency_amount, **kwargs):
        kws = dict(amount=currency_amount.amount, symbol=currency_amount.symbol, currency=currency_amount.currency)
        kws.update(kwargs)
        return cls(**kws)
    

    def __str__(self):
        return f'{self.amount:.2f} {self.symbol}'
    


@dataclass
class WalletEmbed:
    wallet: Wallet = None
    embed: dict = None

    @classmethod
    def from_wallet(cls, wallet_new):
        wallet, new = wallet_new
        embed = {
            'title': f'Wallet:',
            'description': ''
        }
        if new:
            embed['title'] = f'Brand new wallet:'
        embed = discord.Embed.from_dict(embed)
        for balance in wallet.currency_balances:
            c = balance.currency
            n = f'{c.name} {c.symbol}'
            field = dict(name=n, value=str(balance.balance))
            embed.add_field(**field)
        return cls(wallet=wallet, embed=embed)