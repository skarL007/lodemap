import sys
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit("lodemap precisa de Python 3.11 ou mais novo (testado na 3.11 e na 3.12)")

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lodemap.cli import main  # noqa: E402

sys.exit(main())
