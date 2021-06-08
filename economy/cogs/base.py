from base import BaseCog
from economy.services import EconomyService


class BaseEconomyCog(BaseCog):
    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)

        if service is None:
            service = EconomyService()
        self.service = service
