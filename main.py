from discord.ext import commands
import logging
import importlib
import settings

logger = logging.getLogger(__name__)

bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, case_insensitive=True)


@bot.event
async def on_ready():
    logging.info(f'We have logged in as {bot.user}')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)


def _import_models(package):
    try:
        importlib.import_module(f"{package}.models")
        logger.debug(f'Imported {package}.models')
    except ModuleNotFoundError:
        pass
    except ImportError:
        logger.error(f'ImportError: import `{package}.models`')
        return


def init_extensions():
    for extension in settings.EXTENSIONS:
        logger.debug(f'Init extension {extension}')
        _import_models(extension)
        bot.load_extension(extension)


def main():

    if settings.BOT_OWNER_ID is not None:
        bot.author_id = int(settings.BOT_OWNER_ID)
        logger.info(f'Setting bot author id to {settings.BOT_OWNER_ID}')

    init_extensions()

    bot.run(settings.TOKEN)


if __name__ == '__main__':
    main()
