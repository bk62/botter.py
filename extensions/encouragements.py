from discord.ext import commands
from replit import db
import aiohttp
import json
import random

sad_words = ['sad', 'depressed', 'unhappy', 'angry', 'miserable']
starter_encouragements = [
    "Cheer up!", "Hang in there.", "You are a great person / bot!"
]


def update_encouragements(msg):
    if 'encouragements' in db.keys():
        encouragements = db['encouragements']
        encouragements.append(msg)
    else:
        db['encouragements'] = [msg]


def delete_encouragements(index):
    encouragements = db['encouragements']
    if len(encouragements) > index:
        del encouragements[index]
    db['encouragements'] = encouragements


quotes_url = 'https://zenquotes.io/api/random'


async def get_quote():
    async with aiohttp.ClientSession() as session:
        async with session.get(quotes_url) as resp:
            if resp.status == 200:
                # d = await resp.json()
                d = json.loads(await resp.text())
                q = d[0]['q'] + " -" + d[0]['a']
                return q


class Encouragements(commands.Cog, name='Encouragements'):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(help='Fetch an inspiring quote from zenquotes.io')
    async def inspire(self, ctx):
        quote = await get_quote()
        await ctx.send(quote)

    @commands.group(
        name='encourage',
        help='Manage encouraging messages. List, add or delete custom messages.'
        )
    async def encourage(self, ctx):
        pass

    @encourage.command(name='active', help='Enable/Disable')
    async def responding(self, ctx, val: bool):
        db['responding'] = val
        status = 'on' if val else 'off'
        await ctx.send(f'Responding: {status}')

    @encourage.command(help='List all messages.')
    async def list(self, ctx):
        encouragements = []
        if 'encouragements' in db.keys():
            encouragements = db['encouragements']
        await ctx.send(encouragements)

    @encourage.command(help='Add a message to DB.')
    async def add(self, ctx, new_msg: str):
        update_encouragements(new_msg)
        await ctx.send('New message added.')

    @encourage.command(help='Delete from DB.')
    async def delete(self, ctx, index: int):
        encouragements = []
        if 'encouragements' in db.keys():
            delete_encouragements(index)
            encouragements = db['encouragements']
        await ctx.send(encouragements)

    @commands.Cog.listener()
    async def on_message(self, message):
        if db['responding']:
            options = starter_encouragements
            if 'encouragements' in db.keys():
                options = options + list(db['encouragements'])

            if any(word in message.content for word in sad_words):
                await message.channel.send(random.choice(options))


def setup(bot):
    if 'responding' not in db.keys():
        db['responding'] = True
    bot.add_cog(Encouragements(bot))
