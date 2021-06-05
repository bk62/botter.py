from discord.ext import commands
import logging
import importlib
import settings

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, case_insensitive=True)

bot.author_id = int(settings.BOT_OWNER_ID)
logging.info(f'Setting bot author id to {settings.BOT_OWNER_ID}')


@bot.event
async def on_ready():
    logging.info(f'We have logged in as {bot.user}')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$ping'):
        await message.reply('pong.')

    await bot.process_commands(message)


def _import_models(package):
    try:
        importlib.import_module(f"{package}.models")
    except ModuleNotFoundError:
        pass
    except ImportError:
        logging.debug(f'Could not import `{package}.models`')
        return


def init_extensions():
    for extension in settings.EXTENSIONS:
        _import_models(extension)
        bot.load_extension(extension)


def main():
    init_extensions()

    bot.run(settings.TOKEN)


if __name__ == '__main__':
    main()
