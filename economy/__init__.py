import asyncio

from db import Base, engine
from .cogs import Currency, Wallet, Gambling, Rewards
from .services import EconomyService


service = None

async def _reflect():
    async with engine.begin() as conn:
        conn.run_sync(Base.metadata.clear)
        conn.run_sync(Base.metadata.reflect, bind=engine)


def setup(bot):
    # asyncio.run(_reflect())
    # Base.metadata.clear() # TODO

    global service
    service = EconomyService()

    bot.add_cog(Currency(bot, service))
    bot.add_cog(Wallet(bot, service))
    bot.add_cog(Gambling(bot, service))

    rewards_cog = Rewards(bot, service)
    rewards_cog.init_policy()
    bot.add_cog(rewards_cog)



def create_initial_currency():
    asyncio.run(service.create_initial_currency())