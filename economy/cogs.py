import random

import discord
from discord.ext import commands
import db
from economy import models
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from util import get_template
import typing

from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser


class Economy(commands.Cog, name='Economy'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def econ(self, ctx):
        await ctx.reply('econ')

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
            stmt = select(models.Currency).options(selectinload(models.Currency.denominations))
            res = await session.execute(stmt)

            if detailed:
                # embed currency details
                embed = {
                    'title': 'Currencies:',
                    'fields': [
                    ]
                }
                for c in res.scalars():
                    embed['fields'].append({'name': f'{c.name} {c.symbol}', 'value': c.description})
                    for d in c.denominations:
                        embed['fields'].append(
                            {'name': f'{d.name}', 'value': str(d.value), 'inline': True}
                        )
                await ctx.reply(embed=discord.Embed.from_dict(embed))
                return
            else:
                # Brief list
                tmpl = get_template('currency_list.txt.jinja2')
                text = await tmpl.render_async(title='Currencies:', object_list=res.scalars())
                await ctx.reply(text)
            return

    @currency.command(
        name='add', aliases=['a'],
        usage="<currency_spec>",
        help="""Add a currency.\n""" + CURRENCY_SPEC_DESC,
        brief="Add a currency",
    )
    async def add(self, ctx, *, currency_spec: str):
        parser = CurrencySpecParser(currency_spec)
        try:
            currency_dict = parser.parse()
            currency = models.Currency.from_dict(currency_dict)
            print(currency)

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
        await ctx.reply(currency_spec)

    @currency.command(
        name='del', aliases=['d'],
        usage="<currency_symbol>",
        help="""Delete a currency.\n""" + CURRENCY_SPEC_DESC,
        brief="Delete a currency",
    )
    async def delete(self, ctx, symbol: str, *, currency_spec: str):
        await ctx.reply(currency_spec)

    @currency.command(
        name='default',
        usage="<currency_symbol>",
        help="""Set currency as default for the guild or mentioned channels.
                
                All payment and gambling commands that don't specify a currency
                will use the default currency.
                """,
        brief="Set default currency",
    )
    async def default(self, ctx, symbol: str, channels: commands.Greedy[discord.TextChannel] = None):
        await ctx.reply(symbol)

    @currency.command(
        name='wallet',
        usage="[<currency_symbol>]",
        help="""View wallet.
                    """,
        brief="View wallet.",
    )
    async def wallet(self, ctx, symbol: typing.Optional[str] = 'all'):
        await ctx.reply(symbol)


class Gambling(commands.Cog, name='Gambling'):
    def __init__(self, bot):
        self.bot = bot

    def coinflip(self):
        return random.randint(0, 1)
