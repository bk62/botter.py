import functools
import logging
from contextlib import AsyncExitStack
from functools import wraps

from sqlalchemy import exc

import db

from economy import models, repositories, parsers, util, dataclasses
from economy.rewards_policy import RewardRuleEvent, EventContext
from economy.exc import WalletOpFailedException

logger = logging.getLogger('economy.EconomyService')


def async_with_session(begin=False):
    """Decorator to run service methods in service context and/or session begin context."""
    def decorator(method):
        @wraps(method)
        async def wrapper(self, *args, **kwargs):
            coroutine = method(self, *args, **kwargs)
            return await self.await_with(coroutine)
        return wrapper
    return decorator


class RepositoryDescriptor:
    """Repository descriptor to instantiate a new repository class on get.

     - Adds a list of repository attribute names to owner class' '_repositories' attr for later access by instances looking for all repos.
     - Instantiated repos are also added to instance's '_instantiated_repositories' attr dict keyed by descriptor name.
     """
    def __init__(self, repository_class, *args, **kwargs):
        self.repository_class = repository_class
        self.args = args
        self.kwargs = kwargs

    def __set_name__(self, owner, name):
        self.name = name
        owner_repos = getattr(owner, '_repositories', [])
        owner_repos.append(name)
        setattr(owner, '_repositories', owner_repos)

    def __get__(self, instance, owner):
        repo = self.repository_class(instance.session, *self.args, **self.kwargs)
        repo_instances = getattr(instance, '_instantiated_repositories', {})
        repo_instances[self.name] = repo
        setattr(instance, '_instantiated_repositories', repo_instances)
        return repo


class EconomyService:
    """Service class to hold domain logic and/or connect various cogs, parsers, models etc.

        e.g.
        ```
        service = EconomyService()

         with service, service.session.begin():
           ...
         # or
         with service(begin=True):
           ...
        ```
    """
    def __init__(self, async_session=db.async_session):
        self.async_session = async_session
        self.session = None

    def _update_repo_sessions(self):
        """Update any pre-existing repository instances with session.

        Allows calling repo coroutine methods without calling them in order to run later with
        service await_with method.
        """
        for repo_name, repo in getattr(self, '_instantiated_repositories', {}).items():
            if repo is not None:
                repo.session = self.session

    async def __aenter__(self):
        # sessionmaker creates async session.
        self.session = self.async_session()
        # then we enter its context
        await self.async_session().__aenter__()

        self._update_repo_sessions()

        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._instantiated_repositories = {}
        await self.session.__aexit__(exc_type, exc_val, exc_tb)

    async def await_with(self, coroutine, *args, begin=True, **kwargs):
        """Await coroutine methods with service context manager

        Helper to allow putting multiple service method calls into the same sqlalchemy transaction.

        For example, if you wanted to combine queries from a discord.py cog command into a single DB transaction.

        E.g.
        ```
        service = EconomyService()
        coro1 = service.get_all_currencies()
        coro2 = service.get_all_denominations()

        asyn def get_currencies_and_denoms():
            currencies = await coro1
            denoms = await coro2
            return currencies, denoms

        currencies, denoms = await service.await_with(get_currencies_and_denoms())
        ```
        """
        async with AsyncExitStack() as stack:
            # enter Service context
            await stack.enter_async_context(self)
            if begin:
                # enter session.begin context
                await stack.enter_async_context(self.session.begin())
            return await coroutine

    async def __call__(self, coroutine, *args, **kwargs):
        return await self.await_with(coroutine, *args, **kwargs)

    currency_repo = RepositoryDescriptor(repositories.CurrencyRepository)
    wallet_repo = RepositoryDescriptor(repositories.WalletRepository)

    # @property
    # def currency_repo(self):
    #     return repositories.CurrencyRepository(service=self)
    #
    # @property
    # def wallet_repo(self):
    #     return repositories.WalletRepository(service=self)

    async def get_all_currencies(self):
        return await self.currency_repo.find_by()

    @async_with_session(begin=True)
    async def create_currency(self, **kwargs):
        c = models.Currency(**kwargs)
        self.session.add(c)
        return c

    async def create_initial_currency(self):
        """Helper to create an initial currency with spec `BotterPY BPY; description "Initial currency."`"""
        data = dict(name='BotterPy', symbol='BPY', description="Initial currency")
        await self.create_currency(**data)

    async def add_currency(self, currency_dict):
        currency = models.Currency.from_dict(currency_dict)
        self.session.add(currency)
        return currency

    async def update_currency(self, symbol, currency_dict):
        currency = await self.currency_repo.get(symbol)

        # update
        currency.name = currency_dict['name']
        currency.description = currency_dict.get('description', None)  # optional
        currency.symbol = currency_dict['symbol']

        # update denominations
        # - delete old ones
        for d in currency.denominations:
            await self.session.delete(d)
        # - add new ones, if any
        ds = currency_dict.pop('denominations', {})
        for name, val in ds.items():
            denom = models.Denomination(name=name, value=val, currency=currency)
            self.session.add(denom)

        return currency

    @async_with_session(begin=True)
    async def del_currency(self, symbol):
        currency = await self.currency_repo.get(symbol)
        await self.session.delete(currency)
        return currency
    
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
    async def update_currency_balance(user_id, currency_amount: dataclasses.CurrencyAmount, note='', transaction_type=''):
        # assuming user already has an up to date wallet at this point
        try :
            async with db.async_session() as session, session.begin():
                repo = repositories.WalletRepository(session)
                balance = await repo.get_currency_balance(user_id, currency_amount.symbol)
                amount = currency_amount.amount
                if amount < 0 and balance.balance + amount < 0:
                    raise WalletOpFailedException(f'Trying to withdraw {amount} but the balance is only {balance.balance}')
                balance.balance += amount

                # store transaction log
                note =  f'{note}: {currency_amount}'
                transaction = models.TransactionLog(user_id=user_id, currency_id=balance.currency_id, amount=amount, note=note, transaction_type=transaction_type)
                session.add(transaction)

                return balance
        except exc.NoResultFound as e:
            raise WalletOpFailedException(f'{e}: Currency {currency_amount.symbol} not found')

    @staticmethod
    async def deposit_in_wallet(user_id, currency_amount: dataclasses.CurrencyAmount, note=''):
        await EconomyService.update_currency_balance(user_id, currency_amount, note=note, transaction_type='deposit')

    @staticmethod
    async def withdraw_from_wallet(user_id, currency_amount: dataclasses.CurrencyAmount, note):
        # subtract
        currency_amount.amount = -currency_amount.amount
        await EconomyService.update_currency_balance(user_id, currency_amount, note=note, transaction_type='withdrawal')

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

                # store transaction log
                note =  f'Payment from {sender_id} to {receiver_id} of amount {currency_amount}'
                transaction = models.TransactionLog(user_id=sender_id, related_user_id=receiver_id, currency_id=sender_balance.currency_id, amount=amount, note=note, transaction_type='payment')
                session.add(transaction)

        except exc.NoResultFound as e:
            raise WalletOpFailedException(f'{e}: Currency {currency_amount.symbol} not found')


     # Helpers
    async def get_or_create_wallet(self, user_id, user=None):
        """
        Get a user's wallet.
        
        If the user does not have a wallet, create one.

        Also, handles creating wallet balances associated with currencies added since the last time the wallet was updated.
        """
        new = False
        async with self, self.session.begin():
            try:
                wallet = await self.wallet_repo.get(user_id)
            except exc.NoResultFound:
                # Not found
                # create a wallet for user
                # TODO assuming user without wallet does not have a user model either
                logger.debug(f'Creating wallet for {user_id}')
                u = db.User(id=user_id)
                if user:
                    u.name = user.display_name
                wallet = models.Wallet(user=u)
                self.session.add(u)
                self.session.add(wallet)
                await self.session.flush()
                new = True

                # query it again -- b/c we'll need currency balances loaded
                wallet = await self.wallet_repo.get(user_id)

            # get all currencies to ensure any newly added currencies
            # are also added to the user's wallet
            wallet_currencies = set(b.currency for b in wallet.currency_balances)

            all_currencies = set(await self.currency_repo.find_by())
            diff = all_currencies - wallet_currencies
            # create balances for all currencies not in wallet
            for c in diff:
                b = models.CurrencyBalance(wallet=wallet, currency=c)
                self.session.add(b)
            
            await self.session.flush()
        
            return wallet, new


    # TODO args needlessly long
    async def grant_reward(self, rule_event: RewardRuleEvent, event_ctx: EventContext, reward):
        # ensure user has wallet
        user = event_ctx.get_attribute(reward.user)

        logger.debug(f'Executing individual reward: {reward.currency_amount.amount} {reward.currency_amount.code} to {user}')

        await self.get_or_create_wallet(user.id, user)

        # get currency amount from parsed string
        currency_str = f'{reward.currency_amount.amount} {reward.currency_amount.code}'
        currency_amount = await EconomyService.currency_amount_from_str(currency_str)

        # TODO inefficient
        # deposit reward amount
        user_id = user.id
        note = f'Reward for policy rule {rule_event}'
        balance = await EconomyService.update_currency_balance(user_id, currency_amount, note=note, transaction_type='deposit')
    
        async with db.async_session() as session:
            async with session.begin():
                reward_log = models.RewardLog(user_id=user.id, currency=balance.currency, amount=currency_amount.amount, note=note)
                session.add(reward_log)
  
    
    async def has_balance(self, user, currency_amount: dataclasses.CurrencyAmount):
        async with self:
            balance = await self.wallet_repo.get_currency_balance(user.id, currency_amount.symbol)
            amount = currency_amount.amount
            return balance.balance < amount
            

    async def complete_gambling_transaction(self, user, currency_amount: dataclasses.CurrencyAmount, won: bool, note=''):
        # first check they could've afforded the wager amount
        async with self:
            balance = await self.wallet_repo.get_currency_balance(user.id, currency_amount.symbol)
            wager_amount = currency_amount.amount
            if balance.balance < wager_amount:
                raise WalletOpFailedException(f'Trying to withdraw {wager_amount} but the balance is only {balance.balance}')
                return

        if won:
            await self.deposit_in_wallet(user.id, currency_amount, note=f'Winnings from gambling: {note}')
        else:
            await self.withdraw_from_wallet(user.id, currency_amount, note=f'Losses from gambling: {note}')