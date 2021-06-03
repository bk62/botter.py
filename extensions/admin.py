from discord.ext import commands
import typing
import settings


class AdminCommands(commands.Cog, name='Bot Admin Commands'):

    def __init__(self, bot):
        self.bot = bot

    async def ext_check(self, ctx):
        return ctx.author.id == self.bot.author_id

    # @commands.group(name='admin')
    # async def admin(self, ctx):
    #   pass

    @commands.group(
        name='extensions', aliases=['ext'],
        help="Manage extensions for this bot. List all available extensions, and load/unload/reload them.",
        brief="Manage extensions",
        usage=""
    )
    async def extensions(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.extensions)

    @extensions.command(
        name='list', aliases=['ls'],
        help="List all available and active extensions.",
        brief="List extensions",
        usage="all | active"
    )
    async def list(self, ctx, filter_by: typing.Optional[str] = 'active'):
        if filter_by == 'all':
            exts = settings.ALL_EXTENSIONS.keys()
            filter_by = 'All'
        else:
            exts = self.bot.extensions
            filter_by = 'Active'
        base_string = f'{filter_by} Extensions:'
        base_string += "```css\n"  # Gives some styling to the list (on pc side)
        base_string += "\n".join([str(ext) for ext in exts])
        base_string += "\n```"
        await ctx.reply(base_string)

    @extensions.command(
        name='load', aliases=['ld'],
        help='Load an extension using its full name e.g. `extensions.admin`',
        brief='Load extension',
        usage='<ext>'
    )
    async def load(self, ctx, ext):
        try:
            if ext not in settings.ALL_EXTENSIONS.keys():
                raise commands.errors.ExtensionNotFound()
            self.bot.load_extension(ext)
            await ctx.reply(f"`{ext}` has successfully been loaded.")
        except commands.errors.ExtensionNotFound:
            await ctx.reply(f"`{ext}` does not exist!")

    @extensions.command(
        name='reload', aliases=['rl'],
        help='Reload an extension using its full name e.g. `extensions.admin`',
        brief='Reload extension',
        usage='<ext>'
    )
    async def reload(self, ctx, ext):
        extensions = self.bot.extensions
        reloaded = []
        if ext == 'all':
            for e in extensions:
                self.bot.unload_extension(e)
                self.bot.load_extension(e)
                reloaded.append(str(e))
        elif ext in extensions:
            self.bot.unload_extension(ext)
            self.bot.load_extension(ext)
            reloaded.append(ext)
        elif ext in settings.ALL_EXTENSIONS.keys():
            await ctx.reply(f'Cannot reload inactive extension: {ext}')
            return
        else:
            await ctx.reply(f'Invalid extension: {ext}')
            return
        await ctx.reply(f"Finished reloading extensions: {reloaded}.")

    @extensions.command(
        name='unload', aliases=['ul'],
        help='Unload an extension using its full name e.g. `extensions.admin`',
        brief='Unload extension',
        usage='<ext>'
    )
    async def unload(self, ctx, ext):
        extensions = self.bot.extensions
        if ext not in extensions:
            await ctx.reply(f'Extension {ext} is not loaded.')
            return
        self.bot.unload_extension(ext)
        await ctx.reply(f"Extension {ext} unloaded.")


def setup(bot):
    bot.add_cog(AdminCommands(bot))
