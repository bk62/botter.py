import logging

from sqlalchemy import exc

import db

from economy import models, repositories, parsers, util, dataclasses
from economy.exc import WalletOpFailedException

logger = logging.getLogger('economy.EconomyService')



class EconomyService:
    """Service class to hold domain logic and/or connect various cogs, parsers, models etc.
    """
    @staticmethod
    async def create_initial_currency(**kwargs):
        """Helper to create an initial currency with spec `BotterPY BPY; description "Initial currency."`"""
        async with db.async_session() as session:
            async with session.begin():
                currency = models.Currency(name='BotterPy', symbol='BPY', description="Initial currency")
                session.add(currency)
    
    @staticmethod
    async def currency_amount_from_str(currency_str):
        try:
            # [(denom|symbol, val),] 
            amounts = parsers.parse_currency_amounts(currency_str)
            # [denom|symbol,]
            denoms = [a.type for a in amounts]
            # query db for matching currency
            async with db.async_session() as session:
                repo = repositories.CurrencyRepository(session)
                currency = await repo.find_currency_by_denoms(denoms)
        except exc.NoResultFound:
            raise WalletOpFailedException('Invalid currency string: No matching currency')
        except exc.MultipleResultsFound:
            raise WalletOpFailedException('Invalid currency string: Matches multiple currencies')
        return dataclasses.CurrencyAmount.from_amounts(amounts, currency)
    

    @staticmethod
    async def update_currency_balance(user_id, currency_amount: dataclasses.CurrencyAmount):
        # assuming user already has an up to date wallet at this point
        try :
            async with db.async_session() as session, session.begin():
                repo = repositories.WalletRepository(session)
                balance = await repo.get_currency_balance(user_id, currency_amount.symbol)
                amount = currency_amount.amount
                if amount < 0 and balance.balance < amount:
                    raise WalletOpFailedException(f'Trying to withdraw {amount} but the balance is only {balance.balance}')
                balance.balance += amount
                return balance
        except exc.NoResultFound as e:
            raise WalletOpFailedException(f'{e}: Currency {currency_symbol} not found')

    @staticmethod
    async def deposit_in_wallet(user_id, currency_amount: dataclasses.CurrencyAmount):
        await EconomyService.update_currency_balance(user_id, currency_amount)

    @staticmethod
    async def withdraw_from_wallet(user_id, currency_amount: dataclasses.CurrencyAmount):
        # subtract
        currency_amount.amount = -currency_amount.amount
        await EconomyService.update_currency_balance(user_id, currency_amount)

    @staticmethod
    async def make_payment(sender_id, receiver_id, currency_amount: dataclasses.CurrencyAmount):
        # assuming user already has an up to date wallet at this point
        try :
            async with db.async_session() as session, session.begin():
                # both ops in same transaction
                # so both are rolled back if sth goes wrong
                repo = repositories.WalletRepository(session)
                sender_balance = await repo.get_currency_balance(sender_id, currency_amount.symbol)
                receiver_balance = await repo.get_currency_balance(receiver_id, currency_amount.symbol)
                amount = currency_amount.amount
                if sender_balance.balance < amount:
                    raise WalletOpFailedException(f'Trying to withdraw {amount} but the balance is only {sender_balance.balance}')
                sender_balance.balance -= amount
                receiver_balance.balance += amount
        except exc.NoResultFound as e:
            raise WalletOpFailedException(f'{e}: Currency {currency_symbol} not found')


     # Helpers
    @staticmethod
    async def get_or_create_wallet(user_id):
        """
        Get a user's wallet.
        
        If the user does not have a wallet, create one.

        Also, handles creating wallet balances associated with currencies added since the last time the wallet was updated.
        """
        new = False
        async with db.async_session() as session, session.begin():
            # get currency obj from db
            repo = repositories.WalletRepository(session)
            try:
                wallet = await repo.get(user_id)
            except exc.NoResultFound:
                # Not found
                # create a wallet for user
                # TODO assuming user without wallet does not have a user model either
                logger.debug(f'Creating wallet for {user_id}')
                u = db.User(id=user_id)
                wallet = models.Wallet(user=u)
                session.add(u)
                session.add(wallet)
                new = True

            # get all currencies to ensure any newly added currencies
            # are also added to the user's wallet
            currency_repo = repositories.CurrencyRepository(session)
            all_currencies = await currency_repo.find_by()
            wallet_currencies = set(b.currency for b in wallet.currency_balances)

            # create balances for all currencies not in wallet
            for c in set(all_currencies) - wallet_currencies:
                b = models.CurrencyBalance(wallet=wallet, currency=c)
                session.add(b)
        
            return wallet, new

