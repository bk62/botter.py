import os

EXTENSIONS = [
    'extensions.admin',
    'extensions.encouragements',
    'extensions.economy',
]

TOKEN = os.getenv('TOKEN')


COMMAND_PREFIX = '$'


BOT_OWNER_ID = os.getenv('BOT_OWNER_ID')