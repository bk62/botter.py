from .cogs import NLP


def setup(bot):
    bot.add_cog(NLP(bot))