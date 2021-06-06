import random

import discord
from discord.ext import commands
import db
from economy import models
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import exc

from util import render_template, BaseCog
import typing

from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser
from economy import util


class Gambling(commands.Cog, name='Gambling'):
    def __init__(self, bot):
        self.bot = bot

    def coinflip(self):
        return random.randint(0, 1)

    @commands.command(
        help='Gamble. STUB'
    )
    async def gamble(self, ctx, amount: float):
        pass
