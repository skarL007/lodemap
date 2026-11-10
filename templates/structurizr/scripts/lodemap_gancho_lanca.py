"""Lançador do gancho do git do Lodemap. Fica em .git/hooks, que o git não versiona: um `git pull` não o altera.

O gancho executa scripts que moram no repositório (atualizar.ps1, lodemap_gancho.py). Quem puxa um commit alheio
poderia trocar esses scripts e ganhar execução de código no próximo commit. Por isso este lançador só repassa a
chamada se a pasta de scripts ainda tiver o mesmo hash que o dono aprovou ao rodar instalar-gancho.ps1. Se mudou,
não executa nada, avisa em .lodemap/ultimo-atualizar.log e sai com código 0 (o git nunca é bloqueado).

  python lodemap_gancho_lanca.py --aprovar <pasta de scripts>   # grava o hash aprovado (feito pelo instalar-gancho.ps1)
  python lodemap_gancho_lanca.py post-commit --ferramentas X   # chamada do gancho

Só usa a biblioteca padrão.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PIN = AQUI / "lodemap-gancho.pin.json"
EXTENSOES = (".py", ".ps1")


def digest(pasta: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(pasta.rglob("*")):
        if f.is_file() and f.suffix in EXTENSOES and "__pycache__" not in f.parts:
            h.update(f.relative_to(pasta).as_posix().encode("utf-8") + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def aprovar(pasta: Path) -> None:
    pasta = pasta.resolve()
    PIN.write_text(json.dumps({"scripts": str(pasta), "sha256": digest(pasta)}, indent=2) + "\n", encoding="utf-8")


def _avisar(pasta: Path, texto: str) -> None:
    log = pasta.parent / ".lodemap" / "ultimo-atualizar.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {texto}\n")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--aprovar"] and len(argv) == 2:
        aprovar(Path(argv[1]))
        print("aprovado:", PIN)
        return 0
    try:
        pin = json.loads(PIN.read_text(encoding="utf-8"))
        pasta = Path(pin["scripts"])
        if digest(pasta) != pin["sha256"]:
            _avisar(pasta, "scripts do Lodemap alterados desde a aprovação; não executei. "
                           "Confira o que mudou (git diff) e rode instalar-gancho.ps1 para aprovar de novo.")
            return 0
        subprocess.run([sys.executable, str(pasta / "lodemap_gancho.py"), *argv], check=False)
    except Exception:  # sem aprovação ou erro: o gancho nunca derruba o git
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
