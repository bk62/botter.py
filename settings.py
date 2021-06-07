import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv('DEBUG', default=False)

# "extension path": enabled?
ALL_EXTENSIONS = {
    'extensions.admin': True,

    # 'extensions.encouragements': True,

    'economy': True,

    'extensions.greetings': True,
    'extensions.guessing_game': True,
}

EXTENSIONS = [extension for extension, enabled in ALL_EXTENSIONS.items() if enabled]

TOKEN = os.getenv('TOKEN')

COMMAND_PREFIX = 'bp*'

BOT_OWNER_ID = os.getenv('BOT_OWNER_ID')

# pysqlite for sync, aiosqlite for async
DB_NAME = 'database'
DB_PATH = f'{DB_NAME}.db'
DB_URL = f'sqlite+aiosqlite:///{DB_PATH}'
DB_ENGINE_KWARGS = dict(future=True)


if DEBUG:
    # Echo queries in debug mode
    DB_ENGINE_KWARGS['echo'] = True
