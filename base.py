import logging

import discord
from discord.ext import commands

import settings
from util import dump_command_ctx, str_2_color

logger = logging.getLogger(__name__)


class BaseCog(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.bot = bot


    async def cog_command_error(self, ctx, command_error):
        embed = discord.Embed(title='Something went wrong..', description=str(command_error), colour=discord.Colour.red())
        if settings.DEBUG and ctx.author.id == self.bot.author_id:
            # Log detail into context if in DEBUG mode
            # and command author is bot owner
            for name, val, inline in dump_command_ctx(ctx):
                embed.add_field(name=name, value=val, inline=inline)
            embed.add_field(name='class', value=self.__class__, inline=True)
            embed.add_field(name='qualified_name', value=self.qualified_name, inline=True)
        embed.set_footer(text='Please contact the bot owner for assistance.')
        await ctx.message.reply(embed=embed)

        # logger.error(f'Base cog on_command_error: {command_error}')
        raise command_error


    async def reply_embed(self, ctx, title, desc='', footer=None, fields=None, image_url=None, file=None, color=discord.Embed.Empty):
        if color == discord.Embed.Empty or type(color) == str:
            color = str_2_color(color if color else title.lower())

        embed = discord.Embed(title=title, description=desc, colour=color)
        reply_kwargs = {} 
        if fields:
            for f in fields:
                embed.add_field(**f)
        if footer:
            embed.set_footer(footer)
        if image_url:
            embed.set_image(image_url)
        if file:
            reply_kwargs['file'] = file
        
        await ctx.reply(embed=embed, **reply_kwargs)
        