from typing import Type

from PLyBot import Cog
from cogs import PermissionsCog, EconomyCog


class API:
    def __init__(self, cls_cog: Type[Cog]):
        self.cls_cog = 0


if __name__ == '__main__':
    API(EconomyCog)
    print(EconomyCog.cls_config)
