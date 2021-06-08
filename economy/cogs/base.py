from base import BaseCog
from economy.services import EconomyService


class BaseEconomyCog(BaseCog):
    def __init__(self, *args, service_cls=None, **kwargs):
        super().__init__(*args, **kwargs)

        if service_cls is None:
            service_cls = EconomyService
        self._service = service_cls()

    @property
    def service(self):
        return self._service
