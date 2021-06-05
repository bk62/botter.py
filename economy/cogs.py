import random

import discord
from discord.ext import commands
import db
from economy import models
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import exc

from util import render_template, BaseCog
import typing

from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser


# Helpers
def check_mentions_members(ctx):
    return ctx.mentions is not None and len(ctx.mentions) > 0


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


#
# Cogs
class Currency(BaseCog, name='Economy: Manage Virtual Currencies. Bot owner only.'):
    @commands.group(
        name='currency', aliases=['cur'],
        help="Manage virtual currencies. List, create, edit and delete currencies.",
        brief="Manage currencies",
        usage=""
    )
    async def currency(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.currency)

    @currency.command(
        name='list', aliases=['ls'],
        help="List currencies.",
        brief="List currencies",
    )
    async def list(self, ctx, detailed: typing.Optional[bool] = False):
        async with db.async_session() as session:
            # query currencies and denominations
            stmt = select(models.Currency).options(selectinload(models.Currency.denominations))
            res = await session.execute(stmt)
            currencies = res.scalars().all()

            # if no currencies, send empty message and help on how to add one
            if len(currencies) == 0:
                await ctx.reply(await render_template('empty_currency_list.jinja2'))
                await ctx.send_help(self.add)
                return

            if detailed:
                # embed currency details
                embed = {
                    'title': 'Currencies:',
                    'fields': [
                    ]
                }
                for c in currencies:
                    embed['fields'].append({'name': f'{c.name} {c.symbol}', 'value': f'{c.description}'})
                    for d in c.denominations:
                        embed['fields'].append(
                            {'name': f'{d.name}', 'value': str(d.value), 'inline': True}
                        )
                await ctx.reply(embed=discord.Embed.from_dict(embed))
                return
            else:
                # Brief list
                data = dict(title='Currencies:', object_list=currencies)
                text = await render_template('currency_list.txt.jinja2', data)
                await ctx.reply(text)
            return

    @currency.command(
        name='add', aliases=['a'],
        usage="<currency_spec>",
        help="""Add a currency.\n""" + CURRENCY_SPEC_DESC,
        brief="Add a currency",
    )
    async def add(self, ctx, *, currency_spec: str):
        try:
            # parse currency info from string
            currency_dict = parse_currency_from_spec(currency_spec)
            currency = models.Currency.from_dict(currency_dict)

            # save parsed info
            async with db.async_session() as session:
                async with session.begin():
                    session.add(currency)

            await ctx.reply(f'Added currency {currency.name} {currency.symbol}')
        except SyntaxError as e:
            await ctx.reply(f'Error parsing currency spec: {e.msg}')


    @currency.command(
        name='edit', aliases=['e'],
        usage="<currency_symbol> <currency_spec>",
        help="""Edit a currency.\n""" + CURRENCY_SPEC_DESC,
        brief="Edit a currency",
    )
    async def edit(self, ctx, symbol: str, *, currency_spec: str):
        try:
            async with db.async_session() as session:
                async with session.begin():
                    # get currency obj from db
                    stmt = (select(models.Currency).
                        where(models.Currency.symbol == symbol).
                        options(selectinload(models.Currency.denominations)))
                    res = await session.execute(stmt)
                    currency = res.scalar_one() # raises exception if not found

                    # parse info from string
                    currency_dict = parse_currency_from_spec(currency_spec)
                    
                    # update found currency obj
                    currency.name = currency_dict['name']
                    currency.description = currency_dict['description']
                    currency.symbol = currency_dict['symbol']

                    # update denominations
                    # - delete old ones
                    for d in currency.denominations:
                        await session.delete(d)
                    # - add new ones, if any
                    ds = currency_dict.pop('denominations', {})
                    for name, val in ds.items():
                        denom = models.Denomination(name=name, value=val, currency=currency)
                        session.add(denom)

            await ctx.reply(f'Updated currency {currency.name} {currency.symbol}')
        except SyntaxError as e:
            await ctx.reply(f'Error parsing currency spec: {e.msg}')
        except exc.NoResultFound:
            # Not found
            await ctx.reply(f'Error finding currency with symbol: {symbol}')
        
    @currency.command(
        name='del', aliases=['d'],
        usage="<currency_symbol>",
        help="""Delete a currency.\n""" + CURRENCY_SPEC_DESC,
        brief="Delete a currency",
    )
    async def delete(self, ctx, symbol: str):
        try:
            async with db.async_session() as session:
                async with session.begin():
                    # get currency obj from db
                    stmt = (select(models.Currency).
                        where(models.Currency.symbol == symbol).
                        options(selectinload(models.Currency.denominations)))
                    res = await session.execute(stmt)
                    currency = res.scalar_one() # raises exception if not found

                    await session.delete(currency)

            await ctx.reply(f'Deleted currency {currency.name} {currency.symbol}')
        except exc.NoResultFound:
            # Not found
            await ctx.reply(f'Error finding currency with symbol: {symbol}')

    @currency.command(
        name='default',
        usage="no args or 'set_channel <currency_symbol> [@channel mentions]' or 'set_guild <currency_symbol>'",
        help="""View or Set currency as default for the guild or mentioned channels.
                
                All payment and gambling commands that don't specify a currency
                will use the default currency.
                """,
        brief="Set default currency",
    )
    async def default(self, ctx, set_default: typing.Optional[str] = None, symbol: typing.Optional[str] = None, *, channels: commands.Greedy[discord.TextChannel] = None):
        # TODO multiple channels not working properly
        if isinstance(channels, discord.TextChannel):
            channels = [channels]
        if channels is None or len(channels) == 0:
            channels = [ctx.channel]
        if set_default == 'set_channel':
            # set for channels
            for c in channels:
                set_default_channel_currency(c.id, symbol)
            chs = [f'#{c.name}' for c in channels]
            await ctx.reply(f'Set default channel currency to {symbol} for {chs}')
            return
        elif set_default == 'set_guild':
            # set for guild
            set_default_guild_currency(symbol)
            await ctx.reply(f'Set default guild currency to {symbol}')
            return
        else:
            # display defaults
            gd = get_default_guild_currency()
            gd = gd if gd is not None else 'None'
            embed = {
                'title': 'Default Currencies',
                'description': f'Guild default: {gd}',
                'fields': []
            }
            for c in channels:
                s = get_default_channel_currency(c.id)
                s = s if s is not None else 'None'
                embed['fields'].append(dict(name=c.name, value=s))
            await ctx.reply(embed=discord.Embed.from_dict(embed))
            return




class Economy(BaseCog, name='Economy: Wallet and Payments.'):

    #
    # Admin commands:
    @commands.group(
        help="View and manage member wallets. Bot owner only.",
        aliases=['economy']
    )
    async def econ(self, ctx):
        if ctx.invoked_subcommand is None:
            ctx.send_help(self.econ)

    @econ.command(
        help="View member wallets",
        aliases=['wallet', 'view']
    )
    async def view_wallets(self, ctx, *, members: commands.Greedy[discord.Member] = None):
        if not check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        for member in members:
            # TODO
            await ctx.reply(f"{member}'s wallet TODO")

    @econ.command(
        help="Deposit currency in member wallets",
        aliases=['add']
    )
    async def deposit(self, ctx, *, members: commands.Greedy[discord.Member] = None):
        if not check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        for member in members:
            # TODO
            await ctx.reply(f"Deposited amount into {member}'s wallet TODO")
    
    @econ.command(
        help="Withdraw currency from member wallets",
        aliases=['remove']
    )
    async def withdraw(self, ctx, *, members: commands.Greedy[discord.Member] = None):
        if not check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        for member in members:
            # TODO
            await ctx.reply(f"Withdrew amount from {member}'s wallet TODO")

    #
    # Normal users:

    @commands.command(
        name='wallet',
        usage="[<currency_symbol>]",
        help="""View wallet.
                    """,
        brief="View wallet.",
    )
    async def wallet(self, ctx, symbol: typing.Optional[str] = 'all'):
        await ctx.reply(symbol)

    @commands.command()
    async def pay(self, ctx, amount: float, *, members: commands.Greedy[discord.Member] = None):
        if not check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        for member in members:
            # TODO
            await ctx.reply(f"Payed amount to {member} from your wallet TODO")



class Gambling(commands.Cog, name='Gambling'):
    def __init__(self, bot):
        self.bot = bot

    def coinflip(self):
        return random.randint(0, 1)
    
    @commands.command(
        help = 'Gamble.'
    )
    async def gamble(self, ctx, amount: float):
        pass
