import discord
from discord.ext import commands

import settings


class BaseCog(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def cog_command_error(self, ctx, command_error):
        # Log error into context if in DEBUG mode
        embed = dict(title='Command Error', fields=[])
        if settings.DEBUG:
            embed['description'] = str(command_error)
            # if command author is bot owner
            # also log context
            embed['fields'].append(dict(name='ctx', value=str(ctx)))
        else:
            embed['description'] = 'Something went wrong..'
            embed['fields'].append(dict(name='', value='Please contact the bot owner for assistance.'))
            # log generic error otherwise
        embed = discord.Embed.from_dict(embed)
        await ctx.reply(embed=embed)

