import os
import logging

from dotenv import load_dotenv

load_dotenv()

# ENV:

DEBUG = os.getenv('DEBUG', default=True)

TOKEN = os.getenv('TOKEN')

BOT_OWNER_ID = os.getenv('BOT_OWNER_ID')

# Prefix:

COMMAND_PREFIX = 'bp*'


# Extensions:

# "extension path": enabled?
ALL_EXTENSIONS = {
    'extensions.admin': True,

    # 'extensions.encouragements': True,

    'economy': True,

    'extensions.greetings': True,
    'extensions.guessing_game': True,
}

EXTENSIONS = [extension for extension, enabled in ALL_EXTENSIONS.items() if enabled]



# Database:

# pysqlite for sync, aiosqlite for async
DB_NAME = 'database'
DB_PATH = f'{DB_NAME}.db'
DB_URL = f'sqlite+aiosqlite:///{DB_PATH}'
DB_ENGINE_KWARGS = dict(future=True)


if DEBUG:
    # Echo queries in debug mode
    DB_ENGINE_KWARGS['echo'] = True


# Logging:

LOGGING_LEVEL = logging.DEBUG if DEBUG else logging.INFO

if os.getenv('LOGGING_LEVEL'):
    # can override with env var
    LOGGING_LEVEL = os.getenv('LOGGING_LEVEL')


# passed to logging.config.dictConfig
LOGGING_CONFIG = {
    'formatters': {
        'default': logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': LOGGING_LEVEL,
            'formatter': 'default',
        }
    },
    'root': {
        'level': LOGGING_LEVEL,
        'handlers': ['console']
    }
}