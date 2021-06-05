import random
import asyncio

from discord.ext import commands
import discord
import typing


# https://github.com/Rapptz/discord.py/blob/v1.7.2/examples/guessing_game.py
class GuessingGame(commands.Cog, name="Guessing game"):
    def __init__(self, bot):
        self.bot = bot
    
    async def tick(self, ctx, correct):
        emoji = '\N{WHITE HEAVY CHECK MARK}' if correct else '\N{CROSS MARK}'
        try:
            await ctx.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    @commands.command(
      name='guess_now',
      help='Guess a random number from 1-9',
    )
    async def guess_now(self, ctx, num: int):
        answer = random.randint(1, 9)
        correct = num == answer
        await self.tick(ctx, correct)
        await ctx.reply('Correct!' if correct else f'Incorrect. The answer is {answer}', mention_author=True)

    @commands.command(
      name='guess',
      help='Guess a random number between 1-99 or a provided range.'
    )
    async def guess(self, ctx, start: typing.Optional[int] = 1, end: typing.Optional[int]= 99):
        await ctx.send(f'Guess a number between {start}-{end}')

        def is_correct(m):
            return m.author == ctx.message.author and m.content.isdigit()

        answer = random.randint(start, end)

        try:
            guess = await self.bot.wait_for('message', check=is_correct, timeout=5.0)
        except asyncio.TimeoutError:
            return await ctx.reply(f'Sorry, you took too long. The answer is {answer}')
        
        correct = int(guess.content) == answer
        await self.tick(ctx, correct)
        await ctx.reply('Correct!' if correct else f'Incorrect. The answer is {answer}', mention_author=True)





def setup(bot):
    bot.add_cog(GuessingGame(bot))
