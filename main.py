# https://www.freecodecamp.org/news/create-a-discord-bot-with-python/

import discord
from discord.ext import commands
import os
from replit import db
from keep_alive import keep_alive
import logging

import settings


logging.basicConfig(level=logging.INFO)


bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, case_insensitive=True)

bot.author_id = settings.BOT_OWNER_ID


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)




keep_alive()


for extension in settings.EXTENSIONS:
  bot.load_extension(extension)

bot.run(settings.TOKEN)
