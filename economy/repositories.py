from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import exc, or_

from economy import models


class BaseRepository:
    def __init__(self, session):
        self.session = session
    
    def add(*args):
        self.session.add_all(*currency)


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
