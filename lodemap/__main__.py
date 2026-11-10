import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.version_info < (3, 11):
    from lodemap.idioma import t  # noqa: E402  (só stdlib; roda em Python antigo para dar a mensagem)

    sys.exit(t("lodemap precisa de Python 3.11 ou mais novo (testado na 3.11 e na 3.12)",
               "lodemap needs Python 3.11 or newer (tested on 3.11 and 3.12)"))

from lodemap.cli import main  # noqa: E402

sys.exit(main())
