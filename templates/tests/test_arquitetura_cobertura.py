"""Cobertura da arquitetura: todo módulo do código precisa aparecer num caminho de código do modelo C4.

Os módulos vêm dos globs de "modulos" no lodemap.json (um glob terminado em "/" casa pastas; os outros
casam arquivos; a lista opcional "ignorar" tira do conjunto o candidato que casa algum glob dela, ex. ``**/*_test.go``).
Cada componente do modelo ({{ARQ_REL}}/model/*.dsl) declara a propriedade ``codigo`` com
caminhos separados por vírgula: um nome sem barra herda a pasta do caminho anterior ("src/a/b.py, c.py"), um trecho
entre parênteses é só comentário ("src/app.py (main)") e um caminho que termina em "/" cobre a pasta inteira.

Regras conferidas:
  1. cada módulo casado pelos globs está no ``codigo`` de algum componente (com ``politica.tolerancia_modulos`` > 0
     no lodemap.json, uns poucos podem esperar, registrados em pendentes.json por ``lodemap_decidir.py --adiar``,
     dentro de ``tolerancia_dias``; com 0 ou sem o bloco, nenhum espera);
  2. todo caminho citado por um componente existe no disco, salvo componente Planejado (só existe no design) ou com
     a propriedade ``ramo`` (o código mora em outro ramo);
  3. as exceções têm motivo, existem e ainda não estão cobertas (a lista não apodrece).

A raiz do código sozinha ("src/") não conta: cobriria tudo e não diria nada. Só componentes contam; o ``codigo``
dos containers é um resumo. Só usa a biblioteca padrão e não precisa do Java nem do Structurizr.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARQ = ROOT / "{{ARQ_REL}}"
MODELO = ARQ / "model"
CONFIG = json.loads((ARQ / "lodemap.json").read_text(encoding="utf-8-sig"))
RAIZ = CONFIG.get("raiz_codigo", "").strip("/")
IGNORAR = {"__pycache__", "node_modules", ".git", ".venv", "dist", "build"}
EN = CONFIG.get("idioma") == "en"


def _msg(pt: str, en: str) -> str:
    """Mensagem de falha no idioma do mapa: é o que a pessoa lê no CI."""
    return en if EN else pt


# Caminho relativo à raiz do repositório -> motivo. Ex.: "src/rascunho.py": "script de uso único, sai na versão 2".
EXCECOES: dict[str, str] = {}

_DECL = re.compile(r'^\s*(\w+)\s*=\s*(component|container|softwareSystem|person)\s+"([^"]*)"')
_PROP = re.compile(r'^\s*"(codigo|status|ramo)"\s+"([^"]*)"')


def _sem_strings(linha: str) -> str:
    return re.sub(r'"[^"]*"', '""', linha)


def elementos_do_modelo() -> list[dict]:
    saida: list[dict] = []
    for arquivo in sorted(MODELO.glob("*.dsl")):
        pilha: list[dict] = []
        profundidade = 0
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            m = _DECL.match(linha)
            limpa = _sem_strings(linha)
            if m and limpa.rstrip().endswith("{"):
                el = {"id": m.group(1), "tipo": m.group(2), "nivel": profundidade, "codigo": [], "status": "", "ramo": ""}
                pilha.append(el)
                saida.append(el)
            p = _PROP.match(linha)
            if p and pilha:
                if p.group(1) == "codigo":
                    pilha[-1]["codigo"].append(p.group(2))
                else:
                    pilha[-1][p.group(1)] = p.group(2)
            profundidade += limpa.count("{") - limpa.count("}")
            while pilha and profundidade <= pilha[-1]["nivel"]:
                pilha.pop()
    return saida


def caminhos(codigo: str) -> list[str]:
    codigo = re.sub(r"\([^)]*\)", "", codigo)
    pasta, out = "", []
    for parte in re.split(r"[,;]", codigo):
        parte = parte.strip().strip("`")
        if not parte:
            continue
        if "/" in parte:
            pasta = parte if parte.endswith("/") else parte.rsplit("/", 1)[0] + "/"
            out.append(parte)
        else:
            out.append(pasta + parte)
    return out


def caminhos_dos_componentes() -> list[tuple[str, dict]]:
    return [(c, el) for el in elementos_do_modelo() if el["tipo"] == "component"
            for cod in el["codigo"] for c in caminhos(cod)]


def quem_cobre(alvo: str, pares) -> str | None:
    for c, el in pares:
        if c.rstrip("/") == RAIZ:
            continue
        if any(ch in c for ch in "*?["):
            if fnmatch.fnmatch(alvo, c):
                return el["id"]
        elif c.endswith("/"):
            if alvo.startswith(c) or (alvo.endswith("/") and c.startswith(alvo)):
                return el["id"]
        elif c == alvo or (alvo.endswith("/") and c.startswith(alvo)):
            return el["id"]
    return None


def _glob_regex(glob: str) -> re.Pattern:
    """Cópia mínima do glob_regex do arq_comum.py (este teste é entregue sozinho): `**/` casa zero ou mais pastas,
    `*` e `?` não atravessam `/`. Um teste de paridade do Lodemap confere que as duas dão o mesmo resultado."""
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        elif glob[i] == "[" and "]" in glob[i + 1:]:
            j = glob.index("]", i + 1)
            out.append("[" + glob[i + 1:j].replace("\\", "\\\\") + "]")
            i = j + 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out), re.IGNORECASE if os.name == "nt" else 0)


def _globs_ignorar() -> list[str]:
    """Os globs de "ignorar" do lodemap.json: o candidato que casa algum não é módulo (ausente ou vazio = nenhum)."""
    bruto = CONFIG.get("ignorar") or []
    if isinstance(bruto, str):
        bruto = [bruto]
    return [g.strip().rstrip("/") for g in bruto if isinstance(g, str) and g.strip().rstrip("/")]


def alvos() -> list[str]:
    out = set()
    ignorar = [_glob_regex(g) for g in _globs_ignorar()]
    for padrao in CONFIG.get("modulos", []):
        pasta = padrao.endswith("/")
        for p in ROOT.glob(padrao.rstrip("/")):
            if any(parte in IGNORAR or parte.startswith(".") for parte in p.relative_to(ROOT).parts):
                continue
            if any(r.fullmatch(p.relative_to(ROOT).as_posix()) for r in ignorar):
                continue
            if pasta and p.is_dir():
                out.add(p.relative_to(ROOT).as_posix() + "/")
            elif not pasta and p.is_file():
                out.add(p.relative_to(ROOT).as_posix())
    return sorted(out)


def test_ha_modulos_e_componentes():
    assert alvos(), _msg("os globs de 'modulos' do lodemap.json não casam nada",
                         "the 'modulos' globs in lodemap.json match nothing")
    assert caminhos_dos_componentes(), _msg("nenhum componente com 'codigo' no modelo",
                                            "no component in the model has a 'codigo' property")


def _inteiro(nome: str, padrao: int) -> int:
    """Valor do bloco "politica" do lodemap.json: inteiro >= 0, senão o padrão."""
    politica = CONFIG.get("politica")
    v = politica.get(nome) if isinstance(politica, dict) else None
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else padrao


def _hoje() -> date:
    """Hoje; LODEMAP_HOJE (AAAA-MM-DD) vence, para os testes."""
    try:
        return date.fromisoformat((os.environ.get("LODEMAP_HOJE") or "").strip())
    except ValueError:
        return date.today()


def _pendentes() -> dict:
    """Módulos adiados em pendentes.json ({módulo: {"desde", "commit"}}); ausente ou ilegível = nenhum."""
    try:
        mods = json.loads((ARQ / "pendentes.json").read_text(encoding="utf-8-sig"))["modulos"]
        return {k: v for k, v in mods.items() if isinstance(v, dict)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def _vence(registro: dict, dias: int) -> date | None:
    try:
        return date.fromisoformat(str(registro.get("desde"))) + timedelta(days=dias)
    except ValueError:
        return None


def test_todo_modulo_esta_no_modelo():
    pares = caminhos_dos_componentes()
    fora = [a for a in alvos() if a not in EXCECOES and quem_cobre(a, pares) is None]
    onde = f"{ARQ.relative_to(ROOT).as_posix()}/model/*.dsl"
    tolerancia = _inteiro("tolerancia_modulos", 0)
    if tolerancia and fora:
        # Tolerância de módulos (politica no lodemap.json): os que esperam fora do modelo precisam estar em
        # pendentes.json, dentro do limite de quantidade e do prazo. Vale o primeiro caso que falhar.
        dias = _inteiro("tolerancia_dias", 14)
        pend = _pendentes()
        comando = f"python {ARQ.relative_to(ROOT).as_posix()}/scripts/lodemap_decidir.py --adiar"
        lista = "\n  ".join(fora)
        assert len(fora) <= tolerancia, _msg(
            f"{len(fora)} módulo(s) fora da arquitetura, acima da tolerância de {tolerancia}. Ligue pelo menos "
            f"{len(fora) - tolerancia} a um componente (propriedade codigo em {onde}):\n  ",
            f"{len(fora)} module(s) outside the architecture model, over the tolerance of {tolerancia}. Map at least "
            f"{len(fora) - tolerancia} to a component (property 'codigo' in {onde}):\n  ") + lista
        vencidos = [(m, _vence(pend[m], dias)) for m in fora if m in pend and _vence(pend[m], dias) is not None
                    and _hoje() > _vence(pend[m], dias)]
        assert not vencidos, _msg(
            "Prazo vencido para módulo(s) fora da arquitetura. Ligue cada um a um componente "
            f"(propriedade codigo em {onde}):\n  ",
            "Deadline passed for module(s) outside the architecture model. Map each one to a component "
            f"(property 'codigo' in {onde}):\n  ") + "\n  ".join(
                _msg(f"{m} (venceu em {v.isoformat()})", f"{m} (expired on {v.isoformat()})") for m, v in vencidos)
        sem_registro = [m for m in fora if m not in pend or _vence(pend[m], dias) is None]
        assert not sem_registro, _msg(
            f"{len(sem_registro)} módulo(s) fora da arquitetura sem prazo registrado em pendentes.json. Registre o "
            f"prazo com `{comando}` ou ligue cada um a um componente (propriedade codigo em {onde}):\n  ",
            f"{len(sem_registro)} module(s) outside the architecture model have no deadline in pendentes.json. Record "
            f"it with `{comando}` or map each one to a component (property 'codigo' in {onde}):\n  ") + "\n  ".join(sem_registro)
        return
    assert not fora, _msg(
        f"{len(fora)} módulo(s) fora da arquitetura. Ligue cada um a um componente (propriedade codigo em {onde}) "
        "ou, com motivo, em EXCECOES:\n  ",
        f"{len(fora)} module(s) outside the architecture model. Map each one to a component (property 'codigo' in "
        f"{onde}) or list it in EXCECOES with a reason:\n  ") + "\n  ".join(fora)


def test_excecoes_nao_apodrecem():
    pares = caminhos_dos_componentes()
    existentes = set(alvos())
    assert not [a for a in EXCECOES if a not in existentes], _msg("exceção de arquivo que não existe mais",
                                                                   "exception for a file that no longer exists")
    assert not [a for a in EXCECOES if quem_cobre(a, pares)], _msg("exceção que já está no modelo",
                                                                   "exception for a file the model already covers")
    assert all(m.strip() for m in EXCECOES.values()), _msg("toda exceção precisa de motivo",
                                                           "every exception needs a reason")


def test_caminhos_citados_existem():
    faltando = []
    for c, el in caminhos_dos_componentes():
        if el["status"] in ("Planejado", "Planned") or el["ramo"]:  # "Planned" com "idioma": "en"
            continue
        existe = any(ROOT.glob(c)) if any(ch in c for ch in "*?[") else (ROOT / c.rstrip("/")).exists()
        if not existe:
            faltando.append(f"{el['id']}: {c}")
    assert not faltando, _msg("Caminhos que não existem (corrija o DSL ou marque ramo/Planejado):\n  ",
                              "Paths that do not exist (fix the DSL, or mark the component with 'ramo' or Planned):"
                              "\n  ") + "\n  ".join(faltando)
