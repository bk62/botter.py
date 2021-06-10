import os
import logging
from pathlib import Path

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
    DB_ENGINE_KWARGS['echo'] = False #True


# Logging:

LOGGING_LEVEL = logging.INFO if DEBUG else logging.WARN


if os.getenv('LOGGING_LEVEL'):
    # can override with env var
    LOGGING_LEVEL = os.getenv('LOGGING_LEVEL')


LOGS_PATH = Path(__file__).parent / 'logs'
if not os.path.isdir(LOGS_PATH):
    os.mkdir(LOGS_PATH)

# passed to logging.config.dictConfig
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': LOGGING_LEVEL,
            'formatter': 'default',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': logging.ERROR,
            'formatter': 'default',
            'filename': LOGS_PATH / 'error.log',
            'maxBytes': 1024,
            'backupCount': 5,
        }
    },
    'root': {
        'level': LOGGING_LEVEL,
        'handlers': ['console', 'error_file']
    }
}


# Embed color theme
THEME = {
    'success': 'green',
    'error': 'red',
    'warning': 'orange',
    'debug': 'yellow',
}

# Rewards

ENABLE_REWARDS_POLICY_FILE_UPLOAD = True


# Currency Exchange

BASE_CURRENCY = 'BPY'