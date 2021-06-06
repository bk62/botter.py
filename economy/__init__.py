from .cogs import Currency, Wallet, Gambling, Rewards
from db import Base, engine
import asyncio


async def _reflect():
    async with engine.begin() as conn:
        conn.run_sync(Base.metadata.clear)
        conn.run_sync(Base.metadata.reflect, bind=engine)


def setup(bot):
    # asyncio.run(_reflect())
    # Base.metadata.clear() # TODO

    bot.add_cog(Currency(bot))
    bot.add_cog(Wallet(bot))
    bot.add_cog(Gambling(bot))

    rewards_cog = Rewards(bot)
    rewards_cog.interpret_policy()
    bot.add_cog(rewards_cog)

