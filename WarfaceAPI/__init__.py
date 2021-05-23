import re
from typing import Optional, Union, List

import requests


class UserStats:
    class Sum:
        def __init__(self, data_string: str):
            self.real = data_string

        def __str__(self):
            return self.real

        def tag(self, tag: str):
            result = re.search(fr'\[{tag}]\S+', self.real)
            if result:
                return self.real[result.start():result.end()].replace(f'[{tag}]', '', 1).strip()
            return ""

        @property
        def val(self):
            result = re.search(r'= \d+', self.real)
            return int(result.string[result.start():result.end()].replace('= ', ''))

        @property
        def mode(self):
            return self.tag("mode")

        @property
        def stat(self):
            return self.tag("stat")

        @property
        def difficulty(self):
            return self.tag("difficulty")

        @property
        def item_type(self):
            return self.tag("item_type")

        @property
        def class_(self):
            return self.tag("class")

    stats: List[Sum]

    user_id: str
    nickname: str
    experience: int
    rank_id: int
    is_transparent: bool
    clan_id: int
    clan_name: str
    kill: int
    friendly_kills: int
    kills: int
    death: int
    pvp: float
    pve_kill: int
    pve_friendly_kills: int
    pve_kills: int
    pve_death: int
    pve: float
    playtime: int
    playtime_h: int
    playtime_m: int
    favoritPVP: str
    favoritPVE: str
    pve_wins: int
    pvp_wins: int
    pvp_lost: int
    pve_lost: int
    pve_all: int
    pvp_all: int
    pvpwl: float
    full_response: str

    def __init__(self, name: str, server: int):
        if not isinstance(server, int):
            raise TypeError(f"Значение server неверного типа. Получен тип '{type(server)}' необходим 'int'")
        if server not in range(1, 4 + 1):
            raise ValueError("Значение server должно быть в целых пределах от 1 до 4 включительно")

        for key, val in self.get_data(name=name, server=server).items():
            setattr(self, key, val)

        self.stats = list(map(self.Sum, self.full_response.strip().split('\n')))

    def findall(self, **params) -> List[Sum]:
        param_type = Union[str, int, bool, None]

        stat: param_type = params.pop('stat', None)
        class_: param_type = params.pop('class_', None)
        item_type: param_type = params.pop('item_type', None)
        mode: param_type = params.pop('mode', None)
        difficulty: param_type = params.pop('difficulty', None)
        val: param_type = params.pop('val', None)
        if len(params) > 0:
            raise TypeError(f"""findall got an unexpected keyword arguments {"'" + "', '".join(params.keys()) + "'"}""")
        simple_check = lambda s, v: s is None or (s == "" and v) or s == v

        return list(filter(lambda x: (
                simple_check(stat, x.stat) and
                simple_check(class_, x.class_) and
                simple_check(item_type, x.item_type) and
                simple_check(mode, x.mode) and
                simple_check(difficulty, x.difficulty) and
                simple_check(val, x.val)
        ), self.stats))

    def search(self, **params) -> Optional[Sum]:
        result = self.findall(**params)
        if result:
            return result[0]
        return None

    @staticmethod
    def get_data(**params) -> Optional[dict]:
        name = params.pop('name')
        server = params.pop('server')
        response = requests.get(url=f'http://api.warface.ru/user/stat', params={'name': name, 'server': server})
        if response.status_code // 100 == 2:
            return response.json()
        return None
