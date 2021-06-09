import random
import typing
import numpy as np
import asyncio
from decimal import Decimal

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

def get_msg_embed(correct, answer, amount):
    t = 'Congratulations!' if correct else f'Sorry.'
    wl = "won" if correct else "lost"
    d = f'You {wl} {amount}!' 
    e = discord.Embed(title=t, description=d)
    e.add_field(name='Answer', value=str(answer))
    return e


class Gambling(BaseEconomyCog, name='Economy.Gambling'):
    # helper
    async def tick(self, ctx=None, correct=False, message=None):
        emoji = '\N{WHITE HEAVY CHECK MARK}' if correct else '\N{CROSS MARK}'
        try:
            if message:
                await message.add_reaction(emoji)
            else:
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

        ans = 'heads' if guess == 0 else 'tails'
        await self.tick(ctx, correct)
        me = get_msg_embed(correct, ans, currency_amount)
        await ctx.reply(reply=me)

    
    @commands.command(
        help='''Single-player interactive game. Wager on a multiple attempt guessing game.
        
        Guess a number between 1-99. You win double the amount if you guess correctly.
        If you guess wrong, the computer tells you whether you went too high or too low but the pot gets decreased.
        
        Maximum 5 guesses.''',
        usage='<Heads or tails> <currency_amount>'
    )
    async def guess_hilo(self, ctx, *, currency_str: str):
        currency_amount = await self.service.currency_amount_from_str(currency_str)
        pot_amount = dataclasses.CurrencyAmount.copy(currency_amount,amount=currency_amount.amount*2)

        embed = discord.Embed(title='Guess a number between 1-99', description='Reply to this message with your guess.')
        embed.add_field(name='Your bet', value=currency_str)
        embed.add_field(name='Attempts left', value=5)
        embed.add_field(name='Pot', value=pot_amount)
        
        reply_to_msg = await ctx.reply(embed=embed)

        answer = random.randint(1, 99)
        attempts = 0
        guess = 0
        won = False
        hilo = ''
        
        while guess != answer:

            def is_correct(m):
                return m.author == ctx.message.author and m.content.isdigit() and m.reference and m.reference.message_id == reply_to_msg.id  

            try:
                guess_msg = await self.bot.wait_for('message', check=is_correct, timeout=120.0)
            except asyncio.TimeoutError:
                return await self.reply_embed('Error', f'Sorry, you took too long. The answer is {answer}')
                won = False
                break
            attempts += 1

            # guess is a message
            guess = int(guess_msg.content)
            if guess == answer:
                won = True
                break
            elif guess < answer:
                hilo = 'too low'
            else:
                hilo = 'too high'
            
            if attempts > 4:
                won = False
                break

            pot_amount.amount -=  Decimal(0.125) * currency_amount.amount

            embed = discord.Embed(title=f'Your guess is {hilo}', description=f'**{hilo.upper()}**\nReply to this message with your new guess.')
            embed.add_field(name='Your bet', value=currency_str)
            embed.add_field(name='Attempts left', value=5 - attempts)
            embed.add_field(name='New Pot', value=pot_amount)
        
            reply_to_msg = await ctx.reply(embed=embed)
        
        # change balance
        if won:
            # win pot amount - bet amount (b/c bet amount not withdrawn yet)
            update_amount = dataclasses.CurrencyAmount.copy(pot_amount, amount=pot_amount.amount - currency_amount.amount)
            # but display total pot
            amount = pot_amount
        else:
            # lose bet amount
            update_amount = currency_amount
            amount = currency_amount
        await self.service.complete_gambling_transaction(user=ctx.author, currency_amount=update_amount, won=won, note='Game: Guess High-Low')

        # tick on last guess
        await self.tick(message=guess_msg, correct=won)
        me = get_msg_embed(won, answer, amount)
        await guess_msg.reply(embed=me)

                

    
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
