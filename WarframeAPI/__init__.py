# WarframeAPI/__init__.py
# Это модифицированная библиотека. Оригинал: pylotus

import requests
from .wf_api import *
from .response_classes import *
from .exceptions import *

session = requests.Session()
