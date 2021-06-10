import random
import typing
import numpy as np
import asyncio
from decimal import Decimal
from collections import defaultdict


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

async def timeout_after(after=120):
    await asyncio.sleep(after)
    raise asyncio.TimeoutError(f'Timeout after: {after}')


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
        help='Single-player. Wager on a guessing game. Guess a number between 1-9.',
        usage='<guess> <currency_amount>',
    )
    async def guess_1p(self, ctx, guess: int, *, currency_str: str):
        pass
    
    @commands.command(
        help='''Multiplayer single round guessing game. Closest guess takes all.
        
        Guess a number between 1-99.
                
        Only people who reply to first message with a guess join the game. Game creator joins automatically. Game is cancelled if noone else joins within 2 mins.

        Set buy in amount as last argument.
        E.g.
        start a 1BPY game.
        `guess_multi 1 BPY`
        '''
    )
    async def guess_multi(self, ctx, members: commands.Greedy[discord.Member] = None, *, currency_str: str):
        buy_in_amount = await self.service.currency_amount_from_str(currency_str)

        embed = discord.Embed(title='Guess a number between 1-99', description='Reply to this message within 2 mins with your guess to join the game.')
        embed.add_field(name='Buy in amount', value=str(buy_in_amount), inline=False)

        creator = ctx.author
        
        reply_to_msg = await ctx.reply(embed=embed)

        answer = random.randint(1, 99)
        players = {
            ctx.author.id: {
                'user': ctx.author,
                'guess': None
            }
        }
        winners = []
        closest = defaultdict(list)

        def is_valid(m):
            return m.content.isdigit() and m.reference and m.reference.message_id == reply_to_msg.id  

        try:
            # start the clock
            timeout_120 = timeout_after(120)
            timeout_task = asyncio.create_task(timeout_120)

            await timeout_task

            # take guesses
            while True:
                guess_msg = await self.bot.wait_for('message', check=is_valid, timeout=120.0)
                guess_num = int(guess_msg.content)

                if guess_msg.author == creator:
                    players[creator.id]['guess'] = guess_num
                else:
                    u = guess_msg.author
                    players[u.id] = {
                        'user': u,
                        'guess': guess_num
                    }
        except asyncio.TimeoutError:
            await reply_to_msg.reply('Betting is now closed. Processing winners...')
    
        if len(players) == 1 and players[creator.id]['guess'] is not None:
            # only game creator played
            await reply_to_msg.reply(f'{ctx.author.display_name} won by forfeit!')
            return
        
        embed_dict = {'fields': []}
        desc = ''
        pot_amount = dataclasses.CurrencyAmount.copy(buy_in_amount, amount=Decimal(0))
        split_amount = dataclasses.CurrencyAmount.copy(buy_in_amount, amount=Decimal(0))

        for player_id, guess_dict in players:
            player = guess_dict['user']
            guess = guess_dict['guess']
            # first check they can afford the bet
            has_balance = self.service.has_balance(user=player, currency_amount=buy_in_amount)
            if not has_balance:
                embed_dict['fields'].append(dict(name=player.display_name, value='Forfeited because they cannot afford the buy in.'))
                continue
            pot_amount.amount += buy_in_amount.amount
            embed_dict['fields'].append(dict(name=player.display_name, value=f'Guessed: {guess}'))
            if guess == answer:
                winners.append(player)
            else:
                closest[abs(guess - answer)].append(player)

        if len(winners) == 0:
            desc = 'No one guessed accurately. Closest guesses win!'
            closest_dist = min(closest.keys())
            winners = closest[closest_dist]
        
        deposit_amount = pot_amount
        if len(winners) > 1:
            split_amount.amount = pot_amount.amount / Decimal(len(winners))
            deposit_amount = split_amount
            desc += f'\nThere are {len(winners)} winners.\nPot split **{len(winners)} ways**. Each gets {split_amount}'
            winners_str = ', '.join(u.display_name for u in winners)
        else:
            deposit_amount = pot_amount
            desc = f'{winners[0].display_name} wins {pot_amount}!'
            winners_str = winners[0].display_name
        

        embed_dict('fields').append(dict(name='Winners:', value=winners_str,inline=False))

        # Deposit winnings/withdra1 bet amount
        # first subtract buy in amount from winnings
        deposit_amount.amount = deposit_amount.amount - buy_in_amount.amount
        # create winners set so membership check is O(1)
        winners_set = set(w.id for w in winners)
        for player_id, guess_dict in players:
            player = guess_dict['user']
            # sub buy in if lost
            # add (pot / num_winners) - buy win if won
            won = player_id in winners_set
            amount = deposit_amount if won else buy_in_amount
            await self.service.complete_gambling_transaction(user=player,currency_amount=deposit_amount, note='Game: Multiplayer Guess Game (Single Round)', won=won)
        
        # finally done
        embed = discord.Embed.from_dict(embed)
        await reply_to_msg.reply(embed=embed)
            

            


        
        

