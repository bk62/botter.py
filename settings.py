import os
from dotenv import load_dotenv

load_dotenv()

# "extension path": enabled?
ALL_EXTENSIONS = {
    'extensions.admin': True,

    'extensions.encouragements': True,
    'economy': True,

    'extensions.greetings': True,
}

EXTENSIONS = [extension for extension, enabled in ALL_EXTENSIONS.items() if enabled]

TOKEN = os.getenv('TOKEN')

COMMAND_PREFIX = '$'

BOT_OWNER_ID = os.getenv('BOT_OWNER_ID')

DB_URL = 'sqlite+aiosqlite:///database.db'
DB_ENGINE_KWARGS = dict(echo=True, future=True)

