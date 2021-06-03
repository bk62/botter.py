from datetime import datetime

import discord
from discord.ext import commands


class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send(f'Welcome {member.mention}!')

    @commands.command(
        help="Say Hello",
    )
    async def hello(self, ctx, members: commands.Greedy[discord.Member] = []):
        if len(members) == 0:
            members = [ctx.author]
        mentions = ' '.join(m.mention for m in members)
        await ctx.send(f'**Hello** {mentions}!')


def setup(bot):
    bot.add_cog(Greetings(bot))
