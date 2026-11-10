"""Usuario. Exemplo no docstring: import app.config"""
from typing import TYPE_CHECKING
import requests

try:
    import ujson as json
except ImportError:
    import json

if TYPE_CHECKING:
    from app.core import run  # so para tipo, mas e um import real

# from app import config
TEXTO = "from app import util"
S = '''
import app.util
'''


class User:
    pass
