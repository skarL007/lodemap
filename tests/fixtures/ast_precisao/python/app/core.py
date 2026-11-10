import os, json
import types
from .models.user import User
from .models import user as user_mod
import app.config as cfg
from . import util, missing_name


def run():
    from app.config import DEBUG  # import preguicoso dentro da funcao
    return DEBUG, User, user_mod, cfg, util, types
