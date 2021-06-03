from discord.ext import commands


class AdminCommands(commands.Cog, name='Bot Admin Commands'):

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.author.id == self.bot.author_id

    # @commands.group(name='admin')
    # async def admin(self, ctx):
    #   pass

    @commands.group(
        name='extensions', aliases=['cogs'],
        help="""Command to manage extensions for this bot.""",
        brief="Manage extensions",
        usage="Usage",
        description="Desc"
    )
    async def extensions(self, ctx):
        pass

    @extensions.command(name='list', aliases=['ls'])
    async def listcogs(self, ctx):
        base_string = "```css\n"  # Gives some styling to the list (on pc side)
        base_string += "\n".join([str(cog) for cog in self.bot.extensions])
        base_string += "\n```"
        await ctx.reply(base_string)

    @extensions.command(name='load', aliases=['ld'])
    async def load(self, ctx, cog):
        try:
            self.bot.load_extension(cog)
            await ctx.reply(f"`{cog}` has successfully been loaded.")
        except commands.errors.ExtensionNotFound:
            await ctx.reply(f"`{cog}` does not exist!")

    @extensions.command(name='reload', aliases=['rl'])
    async def reload(self, ctx, cog):
        extensions = self.bot.extensions
        if cog == 'all':
            for e in extensions:
                self.bot.unload_extension(cog)
                self.bot.load_extension(cog)
        elif cog in extensions:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        else:
            await ctx.reply(f'Invalid cog: {cog}')
            return
        await ctx.reply(f"Finished reloading 'all' extensions.")

    @extensions.command(name='unload', aliases=['ul'])
    async def unload(self, ctx, cog):
        extensions = self.bot.extensions
        if cog not in extensions:
            await ctx.reply(f'Cog {cog} is not loaded.')
            return
        self.bot.unload_extension(cog)
        await ctx.reply(f"Cog {cog} unloaded.")


def setup(bot):
    bot.add_cog(AdminCommands(bot))
