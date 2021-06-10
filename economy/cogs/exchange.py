import typing

import discord
from discord.ext import commands

from economy import models, util, dataclasses
from .base import BaseEconomyCog



class Exchange(BaseEconomyCog, name="Economy.Exchange", description='Economy: Currency Exchange Markets.'):
    @commands.command(
        help="Get current exchange rate for a currency",
        usage='(<currency_symbol> or <currency_amount>)'
    )
    async def get_rate_for(self, ctx, currency_symbol: str):
        rate = await self.service.currency_repo.get_exchange_rate(currency_symbol)
