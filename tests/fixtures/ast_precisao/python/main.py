"""Ponto de entrada. Menciona `import app.util` so no docstring."""
import os
import app
from app import core
from app.core import run
from pkg_ns.mod import feito
import importlib

# from app import config   <- comentario
TEXTO = "import app.config"

__import__("app.util")
importlib.import_module("app.config")
