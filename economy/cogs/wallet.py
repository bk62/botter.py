import re
import typing
from dataclasses import dataclass

import discord
from discord.ext import commands
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import exc

from base import BaseCog
import db
from util import render_template

from economy import models, util, dataclasses
from economy.parsers import CURRENCY_SPEC_DESC, CurrencySpecParser, CurrencyAmountParser, re_decimal_value
from economy.exc import WalletOpFailedException
from .base import BaseEconomyCog


class Wallet(BaseEconomyCog, name="Economy.Wallet", description='Economy: Wallet and Payments.'):

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
            wallet_data = dataclasses.WalletEmbed.from_wallet(await self.service.get_or_create_wallet(member.id))

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
                await self.service.get_or_create_wallet(member.id)
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
                await self.service.get_or_create_wallet(member.id)
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

        data = dict(title=f'Transactions\n\n[{len(transactions)} results filtered by member id in {member_ids}, currency symbol in {currency_symbols}]', object_list=transactions)
        text = await render_template('base_list.txt.jinja2', data)
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
        wallet_data = dataclasses.WalletEmbed.from_wallet(await self.service.get_or_create_wallet(ctx.author.id))
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

        data = dict(title=f'Transactions\n\n[{len(transactions)} results filtered by currency symbol in {currency_symbols}]', object_list=transactions)
        text = await render_template('base_list.txt.jinja2', data)
        await ctx.reply(text)