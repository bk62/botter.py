import db

from economy import models, repositories, parsers, util
from economy.exc import WalletOpFailedException


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
                currency = await repo.currency_from_denoms(denoms)
        except exc.NoResultFound:
            raise WalletOpFailedException('Invalid currency string: No matching currency')
        except exc.MultipleResultsFound:
            raise WalletOpFailedException('Invalid currency string: Matches multiple currencies')
        return util.CurrencyAmount.from_amounts(amounts, currency)
    

    @staticmethod
    async def update_currency_balance(user_id, currency_symbol, amount):
        # assuming user already has an up to date wallet at this point
        try :
            async with db.async_session() as session, session.begin():
                repo = repositories.WalletRepository(session)
                balance = await repo.get_currency_balance(user_id, currency_symbol)
                if amount < 0 and balance.balance < amount:
                    raise WalletOpFailedException(f'Trying to withdraw {amount} but the balance is only {balance.balance}')
                balance.balance += amount
                return balance
        except exc.NoResultFound as e:
            raise WalletOpFailedException(f'{e}: Currency {currency_symbol} not found')

    @staticmethod
    async def deposit_in_wallet(*args, **kwargs):
        EconomyService.update_currency_balance(*args, **kwargs)

    @staticmethod
    async def withdraw_from_wallet(user_id, currency_symbol, amount):
        amount = -amount
        EconomyService.update_currency_balance(user_id, currency_symbol, amount)

    @staticmethod
    async def make_payment(sender_id, receiver_id, currency_symbol, amount):
        # assuming user already has an up to date wallet at this point
        try :
            async with db.async_session() as session, session.begin():
                # both ops in same transaction
                # so both are rolled back if sth goes wrong
                repo = repositories.WalletRepository(session)
                sender_balance = await repo.get_currency_balance(sender_id, currency_symbol)
                receiver_balance = await repo.get_currency_balance(receiver_id, currency_symbol)
                if sender_balance.balance < amount:
                    raise WalletOpFailedException(f'Trying to withdraw {amount} but the balance is only {sender_balance.balance}')
                sender_balance.balance -= amount
                receiver_balance.balance += amount
        except exc.NoResultFound as e:
            raise WalletOpFailedException(f'{e}: Currency {currency_symbol} not found')
