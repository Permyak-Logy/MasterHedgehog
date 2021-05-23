# pylotus/wf_api.py

from . import session
from .exceptions import *


# noinspection PyPep8Naming
class wf_api(object):
    _platforms = ['pc', 'ps4', 'xb1', 'swi']
    _languages = ["de", "es", "fr", "it", "ko", "pl", "pt", "ru", "zh", "en"]

    @staticmethod
    def get_platforms():
        return wf_api._platforms

    @staticmethod
    def get_languages():
        return wf_api._languages

    def __init__(self, platform, language='ru'):
        if platform not in self._platforms:
            raise NonPlatformError(platform)
        self.platform = platform

        if language not in self._languages:
            raise NonLanguageError(language)
        self.language = language

    def get_all_worldstate_info(self):
        path = 'https://api.warframestat.us/{platform}'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_all_worldstate_info')
        return response.json()

    def get_alert_info(self):
        path = 'https://api.warframestat.us/{platform}/alerts'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_alert_info')
        return response.json()

    def get_cetus_info(self):
        path = 'https://api.warframestat.us/{platform}/cetusCycle'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_cetus_info')
        return response.json()

    def get_conclave_challenge_info(self):
        path = 'https://api.warframestat.us/{platform}/conclaveChallenges'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_conclave_challenge_info')
        return response.json()

    def get_construction_progress_info(self):
        path = 'https://api.warframestat.us/{platform}/constructionProgress'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_construction_progress_info')
        return response.json()

    def get_daily_deals_info(self):
        path = 'https://api.warframestat.us/{platform}/dailyDeals'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_daily_deals_info')
        return response.json()

    def get_event_info(self):
        path = 'https://api.warframestat.us/{platform}/events'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_event_info')
        return response.json()

    def get_fissure_info(self):
        path = 'https://api.warframestat.us/{platform}/fissures'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_fissure_info')
        return response.json()

    def get_flash_sale_info(self):
        path = 'https://api.warframestat.us/{platform}/flashSales'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_flash_sale_info')
        return response.json()

    def get_invasion_info(self):
        path = 'https://api.warframestat.us/{platform}/invasions'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_invasion_info')
        return response.json()

    def get_news_info(self):
        path = 'https://api.warframestat.us/{platform}/news'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_news_info')
        return response.json()

    def get_nightwave_info(self):
        path = 'https://api.warframestat.us/{platform}/nightwave'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_nightwave_info')
        return response.json()

    def get_persistent_enemy_info(self):
        path = 'https://api.warframestat.us/{platform}/persistentEnemies'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_persistent_enemy_info')
        return response.json()

    def get_riven_info(self):
        path = 'https://api.warframestat.us/{platform}/rivens'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_riven_info')
        return response.json()

    def get_specific_riven_info(self, weaponName):
        path = 'https://api.warframestat.us/{platform}/rivens/search/{query}'.format(platform=self.platform,
                                                                                     query=weaponName)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_specific_riven_info')
        return response.json()

    def get_sentient_outpost_info(self):
        path = 'https://api.warframestat.us/{platform}/sentientOutposts'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_sentient_outpost_info')
        return response.json()

    def get_sanctuary_status_info(self):
        path = 'https://api.warframestat.us/{platform}/simaris'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_sanctuary_status_info')
        return response.json()

    def get_sortie_info(self):
        path = 'https://api.warframestat.us/{platform}/sortie'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_sortie_info')
        return response.json()

    def get_syndicate_info(self):
        path = 'https://api.warframestat.us/{platform}/syndicateMissions'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_syndicate_info')
        return response.json()

    def get_timestamp_info(self):
        path = 'https://api.warframestat.us/{platform}/timestamp'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_timestamp_info')
        return response.json()

    def get_vallis_info(self):
        path = 'https://api.warframestat.us/{platform}/vallisCycle'.format(platform=self.platform)
        response = session.get(path)
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_vallis_info')
        return response.json()

    def get_void_trader_info(self):
        path = 'https://api.warframestat.us/{platform}/voidTrader'.format(platform=self.platform)
        response = session.get(path, params={'language': self.language})
        if response.status_code != 200:
            raise StatusCodeError(response.status_code, 'get_void_trader_info')
        return response.json()
