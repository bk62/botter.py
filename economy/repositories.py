from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload, contains_eager, aliased
from sqlalchemy import exc, or_, func, asc, desc


from db import User
from economy import models


class BaseRepository:
    def __init__(self, session=None):
        self.session = session

    def add(self, *args):
        self.session.add_all(*args)


class CurrencyRepository(BaseRepository):
    
    @staticmethod
    def get_query(filters=None, load_denoms=True):
        stmt = select(models.Currency)
        if filters:
            stmt = stmt.filter(*filters)
        if load_denoms:
            stmt = stmt.options(selectinload(models.Currency.denominations))
        return stmt
    
    async def get(self, symbol, **kwargs):
        """Get currency by symbol.
        
         Parameters
        ----------
        symbol : str
            Currency symbol
        load_denoms : bool
            selectin load denominations?
            

        Raises
        ------
        sqlalchemy.exc.NoResultFound
        sqlalchemy.exc.MultipleResultsFound 

        Returns
        -------
        Currency
        """
        filters = [models.Currency.symbol == symbol]
        stmt = self.get_query(filters, **kwargs)
        res = await self.session.execute(stmt)
        currency = res.scalar_one()
        return currency
    
    async def find_by(self, filters=None, **kwargs):
        stmt = self.get_query(filters, **kwargs)
        res = await self.session.execute(stmt)
        currencies = res.scalars().all()
        return currencies

    async def find_currency_by_denoms(self, denoms):
        '''Get currency row joined with related denominations given a list with currency symbol and/or denominations.
        
         Parameters
        ----------
        denoms : list[str]
            List of denomination names and/or Currency symbols

        Raises
        ------
        sqlalchemy.exc.NoResultFound
        sqlalchemy.exc.MultipleResultsFound 

        Returns
        -------
        Currency
        '''
        stmt = (
            select(models.Currency).
            outerjoin(models.Currency.denominations).
            filter(
                or_(
                    models.Currency.symbol.in_(denoms),
                    models.Denomination.name.in_(denoms)
                )
            )
            # .options(
                # joinedload(Currency.denominations)
            # )
        )
        res = await self.session.execute(stmt)
        currency = res.unique().scalar_one()
        return currency
    
    async def get_economy_status(self):
        data = {}
        # 1. total # user wallets
        wallets_stmt = (
            select(models.Wallet).
            join(models.Wallet.user).
            join(models.Wallet.currency_balances).
            join(models.CurrencyBalance.currency)
        )

        wallet_count = await self.session.execute(select(func.count(models.Wallet.id)))

        data['num_wallets'] = wallet_count.scalars().one()

        s = select(models.Currency.symbol, func.sum(models.CurrencyBalance.balance).label('total_money_supply')).\
            join(models.Wallet.currency_balances).\
            join(models.CurrencyBalance.currency).\
            group_by(models.Currency.id).\
            order_by(desc('total_money_supply'))
        money_supply = await self.session.execute(s)

        data['money_supply'] = {
            sym: total
            for sym, total in money_supply.all()
        }


        return data
    
    async def get_exchange_rate(self, currency_symbol):
        stmt = select(models.CurrencyExchangeRate).\
            join(models.CurrencyExchangeRate.exchanged_currency).\
            where(models.Currency.symbol == currency_symbol).\
            order_by(desc(models.CurrencyExchangeRate.created)).\
            limit(1)
        r = await self.session.execute(stmt)
        return r.scalar_one()



class WalletRepository(BaseRepository):

    @staticmethod
    def get_query(filters=None, load_balances=True, load_currencies=True):
        stmt = select(models.Wallet)
        if filters:
            stmt = stmt.filter(*filters)
        if load_balances:
            lb = selectinload(models.Wallet.currency_balances)
            if load_currencies:
                lb = lb.selectinload(models.CurrencyBalance.currency)
            stmt = stmt.options(lb)
        return stmt
    
    async def get(self, user_id, **kwargs):
        """Get wallet by user id.
        
         Parameters
        ----------
        user_id : int
            Discord user id
            

        Raises
        ------
        sqlalchemy.exc.NoResultFound
        sqlalchemy.exc.MultipleResultsFound 

        Returns
        -------
        Currency
        """
        filters = [models.Wallet.user_id == user_id]
        stmt = self.get_query(filters, **kwargs)
        res = await self.session.execute(stmt)
        wallet = res.scalar_one()
        return wallet
    
    async def get_currency_balance(self, user_id, currency_symbol):
        """Get currency balance, i.e. the amount of a specific currency in a wallet, by user id and currency eymbol.
        
         Parameters
        ----------
        user_id : int
            Discord user id
        currency_symbol: str
            Currency symbol
            

        Raises
        ------
        sqlalchemy.exc.NoResultFound
        sqlalchemy.exc.MultipleResultsFound 

        Returns
        -------
        CurrencyBalance
        """
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
        res = await self.session.execute(stmt)

        balance = res.scalar_one()

        return balance

    #
    # TransactionLog:
    @staticmethod
    def get_transactions_query(filters=None):
        related_user_alias = aliased(User)
        stmt = (
            select(models.TransactionLog).
            join(models.TransactionLog.user).
            outerjoin(related_user_alias, models.TransactionLog.related_user).
            join(models.TransactionLog.currency).
            filter(
                *filters
            ).
            options(
                contains_eager(models.TransactionLog.user),
                contains_eager(models.TransactionLog.related_user),
                contains_eager(models.TransactionLog.currency)
            ).
            order_by(desc(models.TransactionLog.created)).
            limit(10)
            # can't send too many logs at once
        # TODO - download all logs
        # also rewards
        )
        return stmt

    async def find_transactions_by(self, user_ids=None, symbols=None):
        filters = []
        if user_ids:
            filters.append(User.id.in_(user_ids))
        if symbols:
            filters.append(models.Currency.symbol.in_(symbols))
        stmt = self.get_transactions_query(filters)
        res = await self.session.execute(stmt)
        logs = res.scalars().all()
        return logs
    
    async def find_user_transactions(self, user_id, symbols=None):
        condition = User.id == user_id
        if symbols:
            filters = (condition, models.Currency.symbol.in_(symbols))
        else:
            filters = (condition,)
        stmt = self.get_transactions_query(filters)
        res = await self.session.execute(stmt)
        logs = res.scalars().all()
        return logs

    #
    # RewardLog:
    @staticmethod
    def get_rewards_query(filters=None):
        stmt = (
            select(models.RewardLog).
            join(models.RewardLog.user).
            join(models.RewardLog.currency).
            filter(
                *filters
            ).
            options(
                contains_eager(models.RewardLog.user),
                contains_eager(models.RewardLog.currency)
            ).
            order_by(desc(models.RewardLog.created)).
            limit(10)
            
        )
        # can't send too many logs at once
        # TODO - download all logs
        # also transactions
        return stmt
    
    async def find_rewards_by(self, user_ids=None, symbols=None):
        filters = []
        if user_ids:
            filters.append(User.id.in_(user_ids))
        if symbols:
            filters.append(models.Currency.symbol.in_(symbols))
        stmt = self.get_rewards_query(filters)
        res = await self.session.execute(stmt)
        logs = res.scalars().all()
        return logs
    
    async def find_user_rewards(self, user_id, symbols=None):
        condition = User.id == user_id
        if symbols:
            filters = (condition, models.Currency.symbol.in_(symbols))
        else:
            filters = (condition,)
        stmt = self.get_rewards_query(filters)
        res = await self.session.execute(stmt)
        logs = res.scalars().all()
        return logs