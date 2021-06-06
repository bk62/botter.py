import re
import typing
from dataclasses import dataclass

import discord
from discord.ext import commands
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import exc

import db
from util import render_template

from economy import models, queries, util
from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser, re_decimal_value


class WalletOpFailedException(Exception):
    pass


@dataclass
class WalletData:
    wallet: models.Wallet
    embed: dict
    new: bool


class Wallet(commands.Cog, name="Economy.Wallet", description='Economy: Wallet and Payments.'):
    def __init__(self, bot):
        self.bot = bot

    # Helpers
    @staticmethod
    async def get_or_create_wallet_embed(user):
        """
        Get a user's wallet serialized into an embed dictionary.
        
        If the user does not have a wallet, create one.

        Also, handles creating and/or deleting wallet balances associated with currencies added and/or removed since the last time the wallet was updated.

        TODO - refactor
        """
        embed = {
            'title': f'{user.display_name}\'s Wallet:',
            'description': '',
            'fields': []
        }
        new = False
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
                    new = True

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

        return WalletData(wallet=wallet, embed=embed, new=new)
    

    @staticmethod
    async def get_balance(session, user_id, currency_symbol):
        # Raises exc.NoResultFound
        # Run in session context
        stmt = (
            select(models.CurrencyBalance).
            join(models.CurrencyBalance.wallet).
            where(models.Wallet.user_id == user_id).
            join(models.CurrencyBalance.currency).
            where(models.Currency.symbol == currency_symbol).
            options(
                joinedload(models.CurrencyBalance.currency)
            )
        )
        res = await session.execute(stmt)

        balance = res.scalar_one()

        return balance

    @staticmethod
    async def deposit_in_wallet(user_id, currency_symbol, amount):
        # assuming user already has an up to date wallet at this point
        async with db.async_session() as session:
            async with session.begin():
                try :
                    balance = await Wallet.get_balance(session, user_id, currency_symbol)
                    balance.balance += amount
                except exc.NoResultFound as e:
                    raise WalletOpFailedException(f'{e}: Currency {currency_symbol} not found')


    @staticmethod
    async def withdraw_from_wallet(user_id, currency_symbol, amount):
        # assuming user already has an up to date wallet at this point
        async with db.async_session() as session:
            async with session.begin():
                try :
                    balance = await Wallet.get_balance(session, user_id, currency_symbol)
                    if balance.balance < amount:
                        raise WalletOpFailedException(f'Trying to withdraw {amount} but the balance is only {balance.balance}')
                    balance.balance -= amount
                except exc.NoResultFound as e:
                    raise WalletOpFailedException(f'{e}: Currency {currency_symbol} not found')

    @staticmethod
    async def make_payment(sender_id, receiver_id, currency_symbol, amount):
        # assuming user already has an up to date wallet at this point
        async with db.async_session() as session:
            async with session.begin():
                # both ops in same transaction
                # so both are rolled back if sth goes wrong
                try :
                    sender_balance = await Wallet.get_balance(session, sender_id, currency_symbol)
                    receiver_balance = await Wallet.get_balance(session, receiver_id, currency_symbol)
                    if sender_balance.balance < amount:
                        raise WalletOpFailedException(f'Trying to withdraw {amount} but the balance is only {sender_balance.balance}')
                    sender_balance.balance -= amount
                    receiver_balance.balance += amount
                except exc.NoResultFound as e:
                    raise WalletOpFailedException(f'{e}: Currency {currency_symbol} not found')

    @staticmethod
    async def currency_amount_from_str(currency_str):
        # [(denom|symbol, val),] 
        amounts = util.parse_currency_amounts(currency_str)
        # [denom|symbol,]
        denoms = [a.type for a in amounts]
        stmt = queries.currency_from_denoms(denoms)
        # query db for matching currency
        async with db.async_session() as session:
            try:
                res = await session.execute(stmt)
                currency = res.unique().scalar_one()
            except exc.NoResultFound:
                raise WalletOpFailedException('Invalid currency string: No matching currency')
            except exc.MultipleResultsFound:
                raise WalletOpFailedException('Invalid currency string: Matches multiple currencies') # TODO not clear error- better to display list of matches
            return util.CurrencyAmount.from_amounts(amounts, currency)

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
        if not util.check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        for member in members:
            wallet_data = await self.get_or_create_wallet_embed(member)
            await ctx.reply(embed=discord.Embed.from_dict(wallet_data.embed))

    @econ.command(
        help="Deposit currency in member wallets",
        usage="<@member mentions> <currency_amount>",
        aliases=['add']
    )
    async def deposit(self, ctx, members: commands.Greedy[discord.Member] = None, *, currency_str: str):
        if not util.check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        for member in members:
            # make sure they have a wallet
            await self.get_or_create_wallet_embed(member)
            # deposit amount
            try:
                currency_amount = await self.currency_amount_from_str(currency_str)
                amount = currency_amount.amount
                currency_symbol = currency_amount.symbol
                await self.deposit_in_wallet(member.id, currency_symbol, amount)
                await ctx.reply(f"Deposited amount {currency_amount} into {member.display_name}'s wallet")
            except WalletOpFailedException as e:
                await ctx.reply(f"Failed to deposited amount {currency_amount} into {member.display_name}'s wallet: {e}")

    @econ.command(
        help="Withdraw currency from member wallets",
        usage="<@member mentions> <currency_amount>",
        aliases=['remove']
    )
    async def withdraw(self, ctx, members: commands.Greedy[discord.Member] = None, *, currency_str: str):
        if not util.check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        for member in members:
            # make sure they have a wallet
            await self.get_or_create_wallet_embed(member)
            # withdraw amount
            try:
                currency_amount = await self.currency_amount_from_str(currency_str)
                amount = currency_amount.amount
                currency_symbol = currency_amount.symbol
                await self.withdraw_from_wallet(member.id, currency_symbol, amount)
                await ctx.reply(f"Withdrew {currency_amount} from {member.display_name}'s wallet")
            except WalletOpFailedException as e:
                await ctx.reply(f"Failed to withdraw {currency_amount} from {member.display_name}'s wallet: {e}")

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
        wallet_data = await self.get_or_create_wallet_embed(ctx.author)
        await ctx.reply(embed=discord.Embed.from_dict(wallet_data.embed))
    

    @commands.command(
        help="Make payments from your wallet."
    )
    async def pay(self, ctx, members: commands.Greedy[discord.Member] = None, *, currency_str: str):
        if not util.check_mentions_members(ctx):
            await ctx.send(
                f'Invalid: You must specify users by mentioning them.')
            return
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        # make sure sender has a wallet
        await self.get_or_create_wallet_embed(ctx.author)
        sender_id = ctx.author.id
        for member in members:
            # make sure they have a wallet
            await self.get_or_create_wallet_embed(member)
            # pay amount
            try:
                currency_amount = await self.currency_amount_from_str(currency_str)
                amount = currency_amount.amount
                currency_symbol = currency_amount.symbol
                await self.make_payment(sender_id, member.id, currency_symbol, amount)
                await ctx.reply(f"Made payment of {currency_amount} from {ctx.author.display_name} to {member.display_name}")
            except WalletOpFailedException as e:
                await ctx.reply(f"Failed to make payment of {currency_amount} from {ctx.author.display_name} to {member.display_name}: {e}")
