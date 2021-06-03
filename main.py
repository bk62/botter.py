from discord.ext import commands
import logging

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


def main():
    for extension in settings.EXTENSIONS:
        bot.load_extension(extension)

    bot.run(settings.TOKEN)


if __name__ == '__main__':
    main()
