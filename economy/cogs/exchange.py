import typing
from decimal import Decimal

import discord
from discord.ext import commands

from economy import models, util, dataclasses
from economy import exc
from .base import BaseEconomyCog
import settings



class Exchange(BaseEconomyCog, name="Economy.Exchange", description='Economy: Currency Exchange Markets.'):

    async def cog_before_invoke(self, ctx):
        # make sure user has wallet
        await self.service.get_or_create_wallet(ctx.author.id, ctx.author)

    @commands.command(
        help="""Get current exchange rate for a currency.
        
        E.g.
        For 1 GC and 100 GC to base:
        `get_rate GC`
        `get_rate 100GC`
        
        For 100GC in RC:
        `get_rate 100GC to RC`
        `get_rate 100 GC to RC`
        
        Note the 'to' clause is required when specifying a currency to convert to.
        """,
        usage='[<convert_to_currency_symbol>] <currency_symbol> or <currency_amount>'
    )
    async def get_rate(self, ctx, *, currency_symbol_or_amount: str):
        # to_currency_symbol is optional
        to_currency_symbol = None
        if ' to ' in currency_symbol_or_amount:
            split = currency_symbol_or_amount.split('to')
            currency_symbol_or_amount = split[0].strip()
            to_currency_symbol = split[1].strip()

        #
        # Parse currency_symbol_or_amount to amount or symbol as appropriate
        currency_amount = None
        currency_symbol = None
        try:
            currency_amount = await self.service.currency_amount_from_str(currency_symbol_or_amount)
            currency_symbol = currency_amount.symbol
        except SyntaxError as e:
            currency_symbol = currency_symbol_or_amount.strip()
            # TODO better validation
            if len(currency_symbol) > 3:
                # cannot be a symbol
                raise e
            # must be a symbol?

        # Get rates
        get_rate = self.service.get_updated_exchange_rate(currency_symbol)
        rate = await self.service(get_rate)
        final_rate = rate.exchange_rate
        # TO Base

        # handle converting to another currency
        if to_currency_symbol is not None:
            # TO another currency
            get_rate = self.service.get_updated_exchange_rate(to_currency_symbol)
            to_rate = await self.service(get_rate)
            # Note:
            #       e.g. A = x BPY
            #            B = y BPY
            #         => A = x/y B
            final_rate = rate.exchange_rate / to_rate.exchange_rate
        else:
            # TODO base currency -get instance -better way to configure
            to_currency_symbol = settings.BASE_CURRENCY

        # unit vs an amount
        if currency_amount is None:
            # convert a unit
            amount_to_convert = 1
        else:
            # convert an amount
            amount_to_convert = currency_amount.amount

        converted_amount = Decimal(final_rate) * amount_to_convert

        # Display
        desc = f'{amount_to_convert} {currency_symbol} = {converted_amount} {to_currency_symbol}'

        embed = discord.Embed(title=f'Exchange rate for {currency_symbol_or_amount}', description=desc)
        # TODO handle floating points and rounding
        if currency_amount is not None:
            embed.add_field(name=f'1 {currency_symbol} = ', value=f'{rate.exchange_rate:.2f}')
        if to_currency_symbol != settings.BASE_CURRENCY:
            embed.add_field(name=f'1 {to_currency_symbol} =', value=f'{to_rate.exchange_rate:.2f}')
        embed.add_field(name=f'{currency_symbol} to {settings.BASE_CURRENCY} Rate', value=f'{rate.exchange_rate}')
        if to_currency_symbol != settings.BASE_CURRENCY:
            embed.add_field(name=f'{to_currency_symbol} to {settings.BASE_CURRENCY} Rate', value=f'{to_rate.exchange_rate}')

        await ctx.reply(embed=embed)

    @commands.command(
        help="""Exchange a currency into another. Converts to the base currency if currency to convert to is not specified.

            E.g.
            Convert 1GC to base:
            `exchange 1GC`
            
            Convert 100GC to base:
            `exchange 100GC`
            
            Convert 100GC to RC:
            `exchange 100GC to RC`
            `exchange 100 GC to RC`
            
            Note the 'to' clause is required when specifying a currency to convert to.
            """,
        usage='<currency_amount> [to <currency_symbol>]'
    )
    async def exchange(self, ctx, *, currency_str: str):
        to_currency_symbol = None
        # to_currency_symbol is optional
        if ' to ' in currency_str:
            split = currency_str.split('to')
            currency_str = split[0].strip()
            to_currency_symbol = split[1].strip()

        await self.debug(ctx, f'From {currency_str} to {to_currency_symbol}')

        currency_amount = await self.service.currency_amount_from_str(currency_str)

        # await self.debug(ctx, str(currency_amount))

        # A. check user has the required amount in wallet
        has_balance = await self.service.has_balance(user=ctx.author, currency_amount=currency_amount)
        if not has_balance:
            raise exc.WalletOpFailedException(f'You do not have {currency_amount} in your wallet.')

        # B. Get rates
        # if there are any incorrect symbols, fail here before creating
        # records

        # 1. To base currency
        get_rate = self.service.get_updated_exchange_rate(currency_amount.symbol)
        rate = await self.service(get_rate)
        final_rate = rate.exchange_rate

        # await self.debug(ctx, str(rate))
        # await self.debug(ctx, f'final rate {final_rate}')

        intermediate_converted_amount = Decimal(final_rate) * currency_amount.amount
        # also get the base currency
        base_currency = await self.service.get_base_currency()
        intermediate_currency_amount = dataclasses.CurrencyAmount(
            currency=base_currency, amount=intermediate_converted_amount,
            symbol=base_currency.symbol)

        # await self.debug(ctx, f'{intermediate_converted_amount!r}')
        # await self.debug(ctx, f'{base_currency!r}')
        await self.debug(ctx, f'intermediate_amount={intermediate_currency_amount!r}')

        # 2. if to_currency is specified
        to_currency_specified = to_currency_symbol is not None and to_currency_symbol != settings.BASE_CURRENCY
        final_converted_amount = None
        to_currency = None
        final_currency_amount = None
        to_rate = None
        if to_currency_specified:
            get_rate2 = self.service.get_updated_exchange_rate(to_currency_symbol)
            to_rate = await self.service(get_rate2)
            # Note:
            #       e.g. A = x BPY
            #            B = y BPY
            #         => A = x/y B
            final_rate = rate.exchange_rate / to_rate.exchange_rate

            final_converted_amount = Decimal(final_rate) * currency_amount.amount
            to_currency = to_rate.exchanged_currency
            final_currency_amount = dataclasses.CurrencyAmount(
                amount=final_converted_amount, currency=to_currency,
                symbol=to_currency.symbol)

            # await self.debug(ctx, f'{final_converted_amount!r}')
            # await self.debug(ctx, f'{to_currency!r}')
            await self.debug(ctx, f'final_amount={final_currency_amount!r}')

        # C. Record
        # Create exchange transaction
        # Update wallet
        # Store rate and amount so rates get updated
        # Note: doing it in the same DB transaction so everything
        # goes through or fails at once
        # 1. conversion to base currency
        # sell
        async with self.service, self.service.session.begin():
            await self.service.complete_exchange_transaction(
                ctx.author, currency_amount.currency, currency_amount.amount, rate, bought=False,
                note=f'Exchange {currency_amount} to {settings.BASE_CURRENCY}')
        # 2. convert to final currency if specified
        # buy
            if to_currency_specified:
                await self.service.complete_exchange_transaction(
                    ctx.author, to_rate.exchanged_currency, final_converted_amount, to_rate, bought=True,
                    note=f'Exchange {settings.BASE_CURRENCY} to {to_currency_symbol}')
        # 3. update wallet amount
        # - remove currency amount
            # need -ve amount to withdraw
            withdraw_amount = dataclasses.CurrencyAmount.copy(currency_amount, amount=-currency_amount.amount)
            await self.service.update_wallet(
                ctx.author.id, withdraw_amount, transaction_type='withdrawal',
                note=f'ExchangeFrom {currency_str} to {to_currency_symbol} -- Withdrawal')
            await self.debug(ctx, f'withdrawal_amount={withdraw_amount}')
        # - add final converted currency amount
            deposit_amount = None
            if to_currency_specified:
                # deposit base currency
                deposit_amount = final_currency_amount
            else:
                # deposit final currency
                deposit_amount = intermediate_currency_amount


            await self.debug(ctx, f'deposit_amount={deposit_amount}')
            await self.service.update_wallet(
                ctx.author.id, deposit_amount, transaction_type='deposit',
                note=f'ExchangeFrom {currency_str} to {to_currency_symbol} -- Deposit')

        # D. Display data
        converted_to = final_currency_amount if to_currency_specified else intermediate_currency_amount
        title = f'Converted {currency_amount} to {converted_to}'
        desc = f'{currency_amount} = {intermediate_currency_amount}'
        if to_currency_specified:
            desc += f' = {final_currency_amount}'
        embed = discord.Embed(title=title, description=desc)

        await ctx.reply(embed=embed)
