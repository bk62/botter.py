from discord.ext import commands
import typing


class NLP(commands.Cog, name="NLP"):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(
        help="NLP"
    )
    async def nlp(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @nlp.group(
        help="Read current or mentioned channel's message history"
    )
    async def read_history(self, ctx, limit: typing.Optional[int] = 100):
        await ctx.send('[+] Started scan')

        async with ctx.channel.typing():

            # TODO
            # get lasst msg in db
            # after=msg

            async for msg in ctx.channel.history(limit=limit): #, oldest_first=True):
                m = dict(
                    author=msg.author.id,
                    content=msg.content,
                    created_at=msg.created_at,
                    mentions=msg.raw_mentions,
                    channel_mentions=msg.raw_channel_mentions,
                    jump_url=msg.jump_url,
                    reference=msg.reference.message_id if msg.reference is not None else None
                )
                if m['reference'] is not None:
                    print(m['reference'])
                print(m)

        await ctx.send('[+] Done..')
