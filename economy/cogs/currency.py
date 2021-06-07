import typing

import discord
from discord.ext import commands
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import exc

import db
from base import BaseCog
from economy import models, util, parsers
from util import render_template
from economy.parsers import CURRENCY_SPEC_DESC
from economy.repositories import CurrencyRepository


class Currency(BaseCog, name='Economy.Currency', description='Economy: Manage Virtual Currencies. Bot owner only.'):
    
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
            repo = CurrencyRepository(session)
            currencies = await repo.find_by()

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
            currency_dict = parsers.parse_currency_from_spec(currency_spec)
            currency = models.Currency.from_dict(currency_dict)

            # save parsed info
            async with db.async_session() as session:
                async with session.begin():
                    session.add(currency)

            await ctx.reply(f'Added currency {currency.name} {currency.symbol}')
        except SyntaxError as e:
            raise commands.CommandError(f'Error parsing currency spec: {e.msg}')

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
                    # raises exception if not found
                    repo = CurrencyRepository(session)
                    currency = await repo.get(symbol)

                    # parse info from string
                    currency_dict = parsers.parse_currency_from_spec(currency_spec)

                    # update found currency obj
                    currency.name = currency_dict['name']
                    currency.description = currency_dict.get('description', None) # optional
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
            raise commands.CommandError(f'Error parsing currency spec: {e.msg}')
        except exc.NoResultFound:
            # Not found
            raise commands.CommandError(f'Error finding currency with symbol: {symbol}')
        except exc.MultipleResultsFound:
            raise commands.CommandError(f'Something went horribly wrong. Multiple currencies found with symbol: {symbol}.')

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
                    # raises exception if not found
                    repo = CurrencyRepository(session)
                    currency = await repo.get(symbol)

                    await session.delete(currency)

            await ctx.reply(f'Deleted currency {currency.name} {currency.symbol}')
        except exc.NoResultFound:
            # Not found
            raise commands.CommandError(f'Error finding currency with symbol: {symbol}')
        except exc.MultipleResultsFound:
            raise commands.CommandError(f'Something went horribly wrong. Multiple currencies found with symbol: {symbol}.')

    ### TODO!!!
    @currency.command(
        name='default',
        usage="no args or 'set_channel <currency_symbol> [@channel mentions]' or 'set_guild <currency_symbol>'",
        help="""View or Set currency as default for the guild or mentioned channels.

                All payment and gambling commands that don't specify a currency
                will use the default currency.
                """,
        brief="Set default currency",
    )
    async def default(self, ctx, set_default: typing.Optional[str] = None, symbol: typing.Optional[str] = None, *,
                      channels: commands.Greedy[discord.TextChannel] = None):
        # TODO multiple channels not working properly
        if isinstance(channels, discord.TextChannel):
            channels = [channels]
        if channels is None or len(channels) == 0:
            channels = [ctx.channel]

        # if set
        # check if currency exists
        if set_default == 'set_channel' or set_default == 'set_guild':
            try:
                async with db.async_session() as session:
                    async with session.begin():
                        # get currency obj from db
                        stmt = (select(models.Currency).
                                where(models.Currency.symbol == symbol).
                                options(selectinload(models.Currency.denominations)))
                        res = await session.execute(stmt)
                        currency = res.scalar_one()  # raises exception if not found
            except exc.NoResultFound:
                # Not found
                raise commands.CommandError(f'Error finding currency with symbol: {symbol}')

        if set_default == 'set_channel':
            # set for channels
            for c in channels:
                util.set_default_channel_currency(c.id, symbol)
            chs = [f'#{c.name}' for c in channels]
            await ctx.reply(f'Set default channel currency to {currency.name} {symbol} for {chs}')
            return
        elif set_default == 'set_guild':
            # set for guild
            util.set_default_guild_currency(symbol)
            await ctx.reply(f'Set default guild currency to {currency.name} {symbol}')
            return
        else:
            # display defaults
            gd = util.get_default_guild_currency()
            gd = gd if gd is not None else 'None'
            embed = {
                'title': 'Default Currencies',
                'description': f'Guild default: {gd}',
                'fields': []
            }
            for c in channels:
                s = util.get_default_channel_currency(c.id)
                s = s if s is not None else 'None'
                embed['fields'].append(dict(name=c.name, value=s))
            await ctx.reply(embed=discord.Embed.from_dict(embed))
            return
