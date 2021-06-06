import re
import typing

import discord
from discord.ext import commands
import db
from economy import models
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import exc

from util import render_template, BaseCog

from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser, re_decimal_value
from economy import util


class Wallet(BaseCog, name='Economy: Wallet and Payments.'):


    # Helpers
    async def get_or_create_wallet_embed(self, user):
        """
        Get a user's wallet serialized into an embed dictionary.
        
        If the user does not have a wallet, create one.

        Also, handles creating and/or deleting wallet balances associated with currencies added and/or removed since the last time the wallet was updated.
        """
        embed = {
            'title': f'{user.display_name}\'s Wallet:',
            'description': '',
            'fields': []
        }
        async with db.async_session() as session:
            async with session.begin():
                # get currency obj from db
                stmt = (
                    select(models.Wallet).
                        where(models.Wallet.user_id == user.id).
                        options(
                        selectinload(models.Wallet.currency_balances).
                            selectinload(models.CurrencyBalance.currency)
                    )
                )
                res = await session.execute(stmt)

                try:
                    wallet = res.scalar_one()
                except exc.NoResultFound:
                    # Not found
                    # create a wallet for user
                    u = db.User(id=user.id, name=user.display_name)
                    wallet = models.Wallet(user=u)
                    session.add(u)
                    session.add(wallet)

                    # query again - should work this time so no except blocks
                    res = await session.execute(stmt)
                    wallet = res.scalar_one()

                    embed['description'] = f'Just created a new wallet for {user.display_name}'

                # get all currencies to ensure any newly added currencies
                # are also added to the user's wallet, and deleted currencies
                # are removed
                all_currencies = await session.execute(select(models.Currency))
                all_currencies = all_currencies.scalars().all()
                all_currencies = set(all_currencies)
                wallet_currencies = set()

                # put balances for all currencies in wallet in embed
                for b in wallet.currency_balances:
                    c = b.currency
                    if c not in all_currencies:
                        # don't display removed currencies and delete em
                        session.delete(b)
                        continue
                    n = f'{c.name} ({c.symbol})'
                    embed['fields'].append(dict(name=n, value=f'{b.balance}'))
                    wallet_currencies.add(c)

                # create and put balances for all currencies not in wallet in embed and session
                for c in all_currencies - wallet_currencies:
                    b = models.CurrencyBalance(wallet=wallet, currency=c)
                    session.add(b)
                    n = f'{c.name} ({c.symbol})'
                    embed['fields'].append(dict(name=n, value=f'0.0'))

        return wallet, embed

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
        help="View member wallets STUB",
        aliases=['wallet', 'view']
    )
    async def view_wallets(self, ctx, *, members: commands.Greedy[discord.Member] = None):
        if not util.check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        for member in members:
            _, embed = await self.get_or_create_wallet_embed(member)
            await ctx.reply(embed=discord.Embed.from_dict(embed))

    @econ.command(
        help="Deposit currency in member wallets STUB",
        aliases=['add']
    )
    async def deposit(self, ctx, currency_str: str, members: commands.Greedy[discord.Member] = None):
        if not util.check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        for member in members:
            # TODO
            amount = 1
            await ctx.reply(f"Deposited amount {amount} into {member.display}'s wallet TODO")

    @econ.command(
        help="Withdraw currency from member wallets STUB",
        aliases=['remove']
    )
    async def withdraw(self, ctx, *, members: commands.Greedy[discord.Member] = None):
        if not util.check_mentions_members(ctx):
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
        usage="",
        help="""View your wallet.
                    """,
        brief="View your wallet.",
    )
    async def wallet(self, ctx):
        _, embed = await self.get_or_create_wallet_embed(ctx.author)
        await ctx.reply(embed=discord.Embed.from_dict(embed))
    

    @commands.command(
        help="Make payments from your wallet. STUB"
    )
    async def pay(self, ctx, amount: float, *, members: commands.Greedy[discord.Member] = None):
        if not util.check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        for member in members:
            # TODO
            await ctx.reply(f"Payed amount to {member} from your wallet TODO")