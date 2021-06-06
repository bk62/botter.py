from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload

from .models import Currency, Denomination


# Query Helpers
def currency_from_denoms(denoms):
    '''Get currency row joined with related denominations given a list with currency symbol and/or denominations.'''
    stmt = (
        select(Currency).
        join(Currency.denominations).
        filter(
            or_(
                Currency.symbol.in_(denoms),
                Denomination.name.in_(denoms)
            )
        )
        # .options(
            # joinedload(Currency.denominations)
        # )
    )
    return stmt