from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import exc, or_

from economy import models


class CurrencyRepository:
    def __init__(self, session):
        self.session = session
    
    def add(currency):
        self.session.add(currency)

    def get_query(filters=None, load_denoms=True):
        stmt = select(models.Currency)
        if filters:
            stmt = stmt.filter(*filters)
        if load_denoms:
            stmt = stmt.options(selectinload(models.Currency.denominations))
        return stmt
    
    async def get(symbol, **kwargs):
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
    
    async def find_by(filters=None, **kwargs):
        stmt = self.get_query(filters, **kwargs)
        res = await self.session.execute(stmt)
        currencies = res.scalars().all()

    async def find_currencies_by_denoms(denoms):
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
        res = await session.execute(stmt)
        currency = res.unique().scalar_one()
        return currency