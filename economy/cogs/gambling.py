import random
import typing

import discord
from discord.ext import commands
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import exc

import db
from base import BaseCog
from util import render_template
from economy import models, util
from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser


class Gambling(BaseCog, name='Economy.Gambling'):

    @commands.command(
        help='Gamble on a coin flip. STUB'
    )
    async def coinflip(self, ctx, currency_str: str):
        pass
    
    @commands.command(
        help='Single-player. Wager on a guessing game. Guess a number between 1-9.'
    )
    async def guess_now(self, ctx, guess: int, *, currency_str: str):
        pass
    
    @commands.command(
        help='Multiplayer winner takes all. Wager on a guessing game. Guess a number between 1-99. Pot grows larger if noone wins.'
    )
    async def guess(self, ctx, *, currency_str: str):
        pass
