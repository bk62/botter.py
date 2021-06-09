import random
import typing
import numpy as np

import discord
from discord.ext import commands
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import exc

import db
from .base import BaseEconomyCog
from util import render_template
from economy import models, util, dataclasses
from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser



 # Util
def cointoss():
    return random.randint(0, 1)

def n_coinflips(n):
    return np.random.randint(0, 2, n)

def dice():
    return random.randint(1, 6)

def n_die(n):
    return np.random.randint(1, 7, n)

def get_msg(correct, answer, amount):
        return 'Correct!' if correct else f'Incorrect. The answer is {answer}.\n You won {amount}!'


class Gambling(BaseEconomyCog, name='Economy.Gambling'):
    # helper
    async def tick(self, ctx, correct):
        emoji = '\N{WHITE HEAVY CHECK MARK}' if correct else '\N{CROSS MARK}'
        try:
            await ctx.message.add_reaction(emoji)
        except discord.HTTPException:
            pass
        
    # everything here needs a wallet
    async def cog_before_invoke(self, ctx):
        ctx.wallet = await self.service.get_or_create_wallet(ctx.author.id, ctx.author)

    @commands.command(
        name='cointoss',
        help='''Gamble on a coin flip.
        Arguments (ignores case):
        Guess: One of {head, heads, h} or {tail, tails, t}
        Currency amount e.g. 1BPY
        ''',
        usage='<Heads or tails> <currency_amount>'
    )
    async def cointoss(self, ctx, guess: str, *, currency_str: str):
        currency_amount = await self.service.currency_amount_from_str(currency_str)

        guess = guess.lower().strip()
        if guess in {'head', 'heads', 'h'}:
            guess = 0
        elif guess in {'tail', 'tails', 't'}:
            guess = 1
        ans = cointoss()
        correct = guess == ans

        await self.service.complete_gambling_transaction(user=ctx.author, currency_amount=currency_amount, won=correct, note='Game: Cointoss')

        await self.tick(ctx, correct)
        m = get_msg(correct, ans, currency_amount)
        await ctx.reply(m)

        
    
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
