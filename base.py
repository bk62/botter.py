import discord
from discord.ext import commands

import settings
from util import dump_command_ctx


class BaseCog(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def cog_command_error(self, ctx, command_error):
        embed = discord.Embed(title='Something went wrong..', description=str(command_error))
        if settings.DEBUG and ctx.author.id == self.bot.author_id:
            # Log detail into context if in DEBUG mode
            # and command author is bot owner
            for name, val, inline in dump_command_ctx(ctx):
                embed.add_field(name=name, value=val, inline=inline)
            embed.add_field(name='class', value=self.__class__, inline=True)
            embed.add_field(name='qualified_name', value=self.qualified_name, inline=True)
        embed.set_footer(text='Please contact the bot owner for assistance.')
        await ctx.message.reply(embed=embed)

