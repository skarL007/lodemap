"""CLI única do Lodemap: python -m lodemap <comando>.

  instalar --perfil minimo|padrao [--aplicar] [--sem a,b] [--com x] [--forcar]
  reverter --manifesto <arquivo>          (sem --manifesto: o último)
  status
  plano [--repo .]                        (permissão: 0 tokens, módulos, custo e tempo, arquivos)
  consentir --escopos gerar,gancho,modelo,synapse [--orcamento-mensal X] [--repo .]
  revogar [--escopos ...] [--repo .]
  verificar --escopo modelo [--custo X] [--repo .]
  doctor [--repo .] [--json]              (diagnóstico do ambiente: 0 tokens, sem rede; apelido: diagnostico)
  --version
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lodemap import RAIZ, __version__, doctor, instalador, permissao


def _lista(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _home(a) -> Path:
    return Path(a.home) if a.home else Path.home()


def cmd_instalar(a) -> int:
    plano = instalador.planejar(a.perfil, _home(a), sem=_lista(a.sem), com=_lista(a.com), forcar=a.forcar,
                                python=a.python)
    print(f"perfil: {plano['perfil']}  opções: {', '.join(plano['opcoes'])}")
    print(f"HOME: {plano['home']}  modo: {'APLICAR' if a.aplicar else 'plano (nada é escrito; use --aplicar)'}")
    for op in plano["ops"]:
        resumo = {k: v for k, v in op.items() if k not in ("opcao", "tipo")}
        print(f"  + [{op['opcao']}] {op['tipo']}: {json.dumps(resumo, ensure_ascii=False)}")
    for c in plano["conflitos"]:
        print("  ! conflito:", c)
    print(f"{len(plano['ops'])} operação(ões), {len(plano['conflitos'])} conflito(s)")
    if a.aplicar:
        man = instalador.aplicar(plano)
        if man is None:
            print("nada a mudar")
        else:
            print("aplicado; manifesto:", man)
            print(f'para reverter: python -m lodemap reverter --manifesto "{man}"')
    return 1 if plano["conflitos"] else 0


def cmd_reverter(a) -> int:
    man = Path(a.manifesto) if a.manifesto else instalador.ultimo_manifesto(_home(a))
    if not man:
        print("nenhum manifesto encontrado")
        return 1
    for f in instalador.reverter(man):
        print("restaurado:", f)
    return 0


def cmd_status(a) -> int:
    home = _home(a)
    skill = home / ".claude" / "skills" / "lodemap"
    print(f"HOME alvo: {home}")
    print(f"repositório: {RAIZ}")
    print(f"skill: {'ok (aponta para este repositório)' if instalador._mesmo(skill, RAIZ) else 'não instalada aqui'}")
    for perfil in instalador.PERFIS:
        p = instalador.planejar(perfil, home, python=a.python)
        print(f"perfil {perfil}: {len(p['ops'])} operação(ões) pendente(s), {len(p['conflitos'])} conflito(s)")
    man = instalador.ultimo_manifesto(home)
    print("último manifesto:", man or "nenhum")
    return 0


def cmd_plano(a) -> int:
    p = permissao.plano(Path(a.repo), a.arq)
    if a.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0
    e = p["estimativa"]
    print(f"repositório: {p['repo']}  (mapa {'existe' if p['mapa_existe'] else 'ainda não existe'})")
    print(f"módulos: {p['modulos']['modulos']} ({p['modulos']['fonte']}; globs {p['modulos']['globs']})")
    if p.get("aviso"):
        print(f"AVISO: {p['aviso']}")
    print(f"custo estimado da 1ª geração: Sonnet ~US$ {e['sonnet_usd']} | Opus ~US$ {e['opus_usd_estimado']} | "
          f"Haiku ~US$ {e['haiku_usd_projecao_nao_medida']} (projeção não medida)")
    print(f"tempo ~{e['minutos']} min, ~{e['chamadas']} chamadas; atualização por commit: US$ "
          f"{e['checkpoint_por_commit_usd']} (só scripts)")
    print(f"método: {e['metodo']}; {e['tipo']}")
    print(f"arquivos: {p['a_criar']} a criar, {len(p['arquivos']) - p['a_criar']} já existem (mantidos)")
    for f in p["arquivos"][: (None if a.todos else 12)]:
        print(f"  {f['acao']:6} {f['caminho']}")
    if not a.todos and len(p["arquivos"]) > 12:
        print(f"  ... (+{len(p['arquivos']) - 12}; --todos lista tudo)")
    c = p["consentimento"]
    print("consentimento:", f"{c['escopos']} teto={c['orcamento_mensal_usd']} ({c['data']})" if c else "nenhum")
    print("este plano gastou 0 tokens. Para autorizar: python -m lodemap consentir --escopos gerar[,modelo] "
          "[--orcamento-mensal X]")
    return 0


def cmd_consentir(a) -> int:
    p = permissao.consentir(Path(a.repo), _lista(a.escopos), a.orcamento_mensal, a.arq)
    print("consentimento gravado:", p)
    return 0


def cmd_revogar(a) -> int:
    if permissao.ler_consentimento(Path(a.repo).resolve(), a.arq) is None:
        print("nenhum consentimento gravado neste repositório; nada a revogar")
        return 0
    r = permissao.revogar(Path(a.repo), _lista(a.escopos) or None, a.arq)
    print("consentimento revogado" if r is None else f"escopos restantes: {r['escopos']}")
    return 0


def cmd_verificar(a) -> int:
    ok, msg = permissao.verificar(Path(a.repo), a.escopo, a.custo, a.arq)
    print(msg)
    return 0 if ok else 3


def cmd_doctor(a) -> int:
    itens = doctor.diagnosticar(_home(a), Path(a.repo) if a.repo else None, a.arq)
    falhas = sum(1 for i in itens if i["estado"] == "falha")
    if a.json:
        print(json.dumps({"itens": itens, "falhas": falhas}, ensure_ascii=False, indent=2))
        return 1 if falhas else 0
    for i in itens:
        print(f"{i['estado']:5} {i['nome']}: {i['detalhe']}")
        if i["acao"] and i["estado"] != "ok":
            print(f"      o que fazer: {i['acao']}")
    avisos = sum(1 for i in itens if i["estado"] == "aviso")
    print(f"{len(itens)} item(ns): {falhas} falha(s), {avisos} aviso(s). Este diagnóstico gastou 0 tokens.")
    return 1 if falhas else 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m lodemap", description=__doc__.splitlines()[0])
    ap.add_argument("--version", action="version", version=f"lodemap {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comum(p):
        p.add_argument("--home", help="HOME alvo (padrão: o do usuário)")
        p.add_argument("--python", default=None, help="Python dos hooks (padrão: o atual)")
        return p

    p = comum(sub.add_parser("instalar"))
    p.add_argument("--perfil", choices=list(instalador.PERFIS), default="padrao")
    p.add_argument("--aplicar", action="store_true")
    p.add_argument("--sem")
    p.add_argument("--com")
    p.add_argument("--forcar", action="store_true")
    p.set_defaults(f=cmd_instalar)
    p = comum(sub.add_parser("reverter"))
    p.add_argument("--manifesto")
    p.set_defaults(f=cmd_reverter)
    p = comum(sub.add_parser("status"))
    p.set_defaults(f=cmd_status)
    p = comum(sub.add_parser("doctor", aliases=["diagnostico"]))
    p.add_argument("--repo", default=None)
    p.add_argument("--arq", default=permissao.ARQ_PADRAO)
    p.add_argument("--json", action="store_true")
    p.set_defaults(f=cmd_doctor)
    for nome, f in (("plano", cmd_plano), ("consentir", cmd_consentir), ("revogar", cmd_revogar),
                    ("verificar", cmd_verificar)):
        p = sub.add_parser(nome)
        p.add_argument("--repo", default=".")
        p.add_argument("--arq", default=permissao.ARQ_PADRAO)
        p.set_defaults(f=f)
        if nome == "plano":
            p.add_argument("--json", action="store_true")
            p.add_argument("--todos", action="store_true")
        if nome in ("consentir", "revogar"):
            p.add_argument("--escopos", required=nome == "consentir")
        if nome == "consentir":
            p.add_argument("--orcamento-mensal", type=float)
        if nome == "verificar":
            p.add_argument("--escopo", required=True, choices=list(permissao.ESCOPOS))
            p.add_argument("--custo", type=float, default=0.0)
    return ap


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    a = parser().parse_args(argv)
    try:
        return a.f(a)
    except ValueError as e:
        print("erro:", e)
        return 2
