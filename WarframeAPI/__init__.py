# WarframeAPI/__init__.py
# Это модифицированная библиотека. Оригинал: pylotus

import requests

session = requests.Session()

from .wf_api import *
from .response_classes import *
from .exceptions import *
