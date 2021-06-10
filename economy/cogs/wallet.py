import re
import typing
from dataclasses import dataclass
from decimal import Decimal

import discord
from discord.ext import commands
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import exc

import settings
from base import BaseCog
import db
from util import render_template

from economy import models, util, dataclasses
from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser, re_decimal_value
from economy.exc import WalletOpFailedException
from .base import BaseEconomyCog


class Wallet(BaseEconomyCog, name="Economy.Wallet", description='Economy: Wallet and Payments.'):

    # everything here needs a wallet
    async def cog_before_invoke(self, ctx):
        ctx.wallet = await self.service.get_or_create_wallet(ctx.author.id, ctx.author)

    #
    # Admin commands:
    @commands.group(
        help="View and manage member wallets. Bot owner only.",
        aliases=['economy']
    )
    async def econ(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.econ)

    @econ.command(
        help="View member wallets",
        aliases=['wallet', 'view']
    )
    async def view_wallets(self, ctx, *, members: commands.Greedy[discord.Member] = None):
        if not util.check_mentions_members(ctx):
            await self.reply_embed(ctx, 'Error', 
                f'Invalid: You must specify users by mentioning them.')
            return
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        for member in members:
            wallet_data = dataclasses.WalletEmbed.from_wallet(await self.service.get_or_create_wallet(member.id, member))

            await ctx.reply(embed=wallet_data.embed)

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
            # TODO inefficient
            try:
                # make sure they have a wallet
                await self.service.get_or_create_wallet(member.id, member)
                currency_amount = await self.service.currency_amount_from_str(currency_str)
                await self.service.deposit_in_wallet(member.id, currency_amount, note=f'Initiated by {ctx.author.id} {ctx.author.display_name}')
                await self.reply_embed(ctx, 'Success', f"Deposited amount {currency_amount} into {member.display_name}'s wallet")
            except WalletOpFailedException as e:
                raise WalletOpFailedException(f"Failed to deposited amount into {member.display_name}'s wallet: {e}")

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
            try:
                # make sure they have a wallet
                await self.service.get_or_create_wallet(member.id, member)
                currency_amount = await self.service.currency_amount_from_str(currency_str)
                await self.service.withdraw_from_wallet(member.id, currency_amount, note=f'Initiated by {ctx.author.id} {ctx.author.display_name}')
                await self.reply_embed(ctx, 'Success', f"Withdrew {currency_amount} from {member.display_name}'s wallet")
            except WalletOpFailedException as e:
                raise WalletOpFailedException(f"Failed to withdraw amount from {member.display_name}'s wallet: {e}")
    
    @econ.command(
        name='transactions',
        help='View transactions. Filter by currencies and/or members.',
        usage="<@member mentions> <currency_symbol>",
        alias="logs"
    )
    async def econ_transactions(self, ctx, members: commands.Greedy[discord.Member] = None, *, currency_str: typing.Optional[str] = None):
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        member_ids = None
        if members and len(members) > 0:
            member_ids = [member.id for member in members]
        currency_symbols = None
        if currency_str:
            currency_symbols = [
                c.strip() for c in currency_str.split()
            ]
        find_all = self.service.wallet_repo.find_transactions_by(member_ids, currency_symbols)
        transactions = await self.service(find_all)
        
        if len(transactions) < 1:
            await self.reply_embed(ctx, 'Error', 'No transactions in database')
            return

        data = dict(title=f'Transactions', object_list=transactions, member_ids=member_ids, currency_symbols=currency_symbols)
        text = await render_template('transactions.jinja2', data)
        await ctx.reply(text)

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
        wallet_data = dataclasses.WalletEmbed.from_wallet(await self.service.get_or_create_wallet(ctx.author.id, ctx.author))
        await ctx.reply(embed=wallet_data.embed)

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
        await self.service.get_or_create_wallet(ctx.author.id)
        sender_id = ctx.author.id
        for member in members:
            try:
                await self.service.get_or_create_wallet(member.id)
                currency_amount = await self.service.currency_amount_from_str(currency_str)
                await self.service.make_payment(sender_id, member.id, currency_amount)
                await self.reply_embed(ctx, 'Success', 
                    f"Made payment of {currency_amount} from {ctx.author.display_name} to {member.display_name}")
            except WalletOpFailedException as e:
                raise WalletOpFailedException(
                    f"Failed to make payment from {ctx.author.display_name} to {member.display_name}: {e}")

    @commands.command(
        help='View your transactions. Filter by currencies.',
        usage="<currency_symbol>",
        alias="logs"
    )
    async def transactions(self, ctx, *, currency_str: typing.Optional[str] = None):
        currency_symbols = None
        if currency_str:
            currency_symbols = [
                c.strip() for c in currency_str.split()
            ]
        find_all = self.service.wallet_repo.find_user_transactions(ctx.author.id, currency_symbols)
        transactions = await self.service(find_all)
        
        if len(transactions) < 1:
            await self.reply_embed(ctx, 'Error', 'No transactions in database')
            return

        data = dict(title=f'Transactions', object_list=transactions, current_user_id=ctx.author.id, currency_symbols=currency_symbols)
        text = await render_template('transactions.jinja2', data)
        await ctx.reply(text)
    
    
    @commands.command(
        help='New members: Thank members for helping you.',
        usage="ty_for_help <@helpful_author>",
        alias="ty"
    )
    async def ty_for_help(self, ctx, helped_by: discord.Member):

        # get correct currency symbol from settings
        currency_symbol = settings.NEWBIE_HELP_COIN
        default_tip  = settings.DEFAULT_TIP
        # create a currency amount instance
        tip_amount = dataclasses.CurrencyAmount(
            amount=Decimal(default_tip), symbol=currency_symbol)


        # check the user has enough to afford a tip
        has_balance = self.service.has_balance(user=ctx.author, currency_amount=tip_amount)

        if not has_balance:
            # raise exception so the exception handler can display the error in an embed
            raise exc.WalletOpFailedException("You don't have enough in your wallet to do this.")
        
        # carry out the tip
        sender_id = ctx.author.id
        helper_id = helped_by.id
        await self.service.make_payment(sender_id, helper_id, tip_amount)

        # reply with success message in an embed
        await self.reply_embed(ctx, 'Success', 
            f"Tipped {tip_amount} from {ctx.author.display_name} to {helped_by.display_name} for being helpful!")
