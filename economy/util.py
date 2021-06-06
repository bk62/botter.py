import db
from .parsers import CurrencySpecParser


# Helpers
def check_mentions_members(ctx):
    return ctx.mentions is not None and len(ctx.mentions) > 0


# Parsing

def parse_currency_from_spec(currency_spec):
    parser = CurrencySpecParser(currency_spec)
    currency_dict = parser.parse()
    return currency_dict


# replit db - default currency helpers
def _channel_currency_key(channel_id):
    return f'econ__channel_{channel_id}_dc'


def set_default_guild_currency(symbol):
    db.replit_db['econ__guild_dc'] = symbol


def set_default_channel_currency(channel_id, symbol):
    k = _channel_currency_key(channel_id)
    db.replit_db[k] = symbol


def get_default_guild_currency():
    if 'econ__guild_dc' in db.replit_db.keys():
        return db.replit_db['econ__guild_dc']


def get_default_channel_currency(channel_id=None):
    if channel_id is None:
        return get_default_guild_currency()
    k = _channel_currency_key(channel_id)
    if k in db.replit_db.keys():
        return db.replit_db[k]
    return None

# orm - member wallet helpers
