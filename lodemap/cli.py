"""Lodemap command line: python -m lodemap <command>.  (CLI única do Lodemap.)

Commands (the Portuguese names keep working as aliases):
  install   (instalar)  --profile minimo|padrao [--apply] [--without a,b] [--with x] [--force]
  revert    (reverter)  --manifest <file>        (without --manifest: the last one)
  status
  plan      (plano)     [--repo .]               (permission: 0 tokens, modules, cost and time, files)
  consent   (consentir) --scopes gerar,gancho,modelo [--monthly-budget X] [--repo .]
  revoke    (revogar)   [--scopes ...] [--repo .]
  check     (verificar) --scope modelo [--cost X] [--repo .]
  doctor    (diagnostico) [--repo .] [--json]    (environment diagnosis: 0 tokens, no network)
  --version

Language of the output: LODEMAP_IDIOMA=pt|en, else the map's lodemap.json "idioma", else the system locale, else English.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lodemap import RAIZ, __version__, doctor, instalador, permissao
from lodemap.idioma import idioma, opcao, t, usar_mapa


def _lista(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _home(a) -> Path:
    return Path(a.home) if a.home else Path.home()


# Valores de dado (chaves e rótulos gravados em arquivos ou no JSON) ficam como estão; só a exibição no terminal muda.
_ACAO = {"cria": "create", "troca": "replace", "troca (backup)": "replace (backup)", "mantém": "keep"}
_ESTADO = {"ok": "ok", "aviso": "warn", "falha": "fail"}
_ITEM = {"agentes": "agents", "mapa": "map", "consentimento": "consent"}


def _acao(valor: str) -> str:
    return valor if idioma() == "pt" else _ACAO.get(valor, valor)


def cmd_instalar(a) -> int:
    plano = instalador.planejar(a.perfil, _home(a), sem=_lista(a.sem), com=_lista(a.com), forcar=a.forcar,
                                python=a.python)
    print(t(f"perfil: {plano['perfil']}  opções: {', '.join(plano['opcoes'])}",
            f"profile: {plano['perfil']}  options: {', '.join(plano['opcoes'])}"))
    modo = (t("APLICAR", "APPLY") if a.aplicar
            else t("plano (nada é escrito; use --aplicar)", "plan (nothing is written; use --apply)"))
    print(t(f"HOME: {plano['home']}  modo: {modo}", f"HOME: {plano['home']}  mode: {modo}"))
    for op in plano["ops"]:
        resumo = {k: v for k, v in op.items() if k not in ("opcao", "tipo")}
        if "acao" in resumo:
            resumo["acao"] = _acao(resumo["acao"])
        print(f"  + [{op['opcao']}] {op['tipo']}: {json.dumps(resumo, ensure_ascii=False)}")
    for c in plano["conflitos"]:
        print(t("  ! conflito:", "  ! conflict:"), c)
    print(t(f"{len(plano['ops'])} operação(ões), {len(plano['conflitos'])} conflito(s)",
            f"{len(plano['ops'])} operation(s), {len(plano['conflitos'])} conflict(s)"))
    if a.aplicar:
        man = instalador.aplicar(plano)
        if man is None:
            print(t("nada a mudar", "nothing to change"))
        else:
            print(t("aplicado; manifesto:", "applied; manifest:"), man)
            print(t(f'para reverter: python -m lodemap reverter --manifesto "{man}"',
                    f'to revert: python -m lodemap revert --manifest "{man}"'))
    return 1 if plano["conflitos"] else 0


def cmd_reverter(a) -> int:
    man = Path(a.manifesto) if a.manifesto else instalador.ultimo_manifesto(_home(a))
    if not man:
        print(t("nenhum manifesto encontrado", "no manifest found"))
        return 1
    for f in instalador.reverter(man):
        print(t("restaurado:", "restored:"), f)
    return 0


def cmd_status(a) -> int:
    home = _home(a)
    skill = home / ".claude" / "skills" / "lodemap"
    print(t(f"HOME alvo: {home}", f"target HOME: {home}"))
    print(t(f"repositório: {RAIZ}", f"repository: {RAIZ}"))
    ok = instalador._mesmo(skill, RAIZ)
    print(t(f"skill: {'ok (aponta para este repositório)' if ok else 'não instalada aqui'}",
            f"skill: {'ok (points to this repository)' if ok else 'not installed here'}"))
    for perfil in instalador.PERFIS:
        p = instalador.planejar(perfil, home, python=a.python)
        print(t(f"perfil {perfil}: {len(p['ops'])} operação(ões) pendente(s), {len(p['conflitos'])} conflito(s)",
                f"profile {perfil}: {len(p['ops'])} pending operation(s), {len(p['conflitos'])} conflict(s)"))
    man = instalador.ultimo_manifesto(home)
    print(t("último manifesto:", "last manifest:"), man or t("nenhum", "none"))
    return 0


def cmd_plano(a) -> int:
    p = permissao.plano(Path(a.repo), a.arq)
    if a.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0
    e = p["estimativa"]
    print(t(f"repositório: {p['repo']}  (mapa {'existe' if p['mapa_existe'] else 'ainda não existe'})",
            f"repository: {p['repo']}  (map {'exists' if p['mapa_existe'] else 'does not exist yet'})"))
    print(t(f"módulos: {p['modulos']['modulos']} ({p['modulos']['fonte']}; globs {p['modulos']['globs']})",
            f"modules: {p['modulos']['modulos']} ({p['modulos']['fonte']}; globs {p['modulos']['globs']})"))
    if p.get("aviso"):
        print(t(f"AVISO: {p['aviso']}", f"WARNING: {p['aviso']}"))
    print(t(f"custo estimado da 1ª geração: Sonnet ~US$ {e['sonnet_usd']} | Opus ~US$ {e['opus_usd_estimado']} | "
            f"Haiku ~US$ {e['haiku_usd_projecao_nao_medida']} (projeção não medida)",
            f"estimated cost of the 1st generation: Sonnet ~US$ {e['sonnet_usd']} | Opus ~US$ "
            f"{e['opus_usd_estimado']} | Haiku ~US$ {e['haiku_usd_projecao_nao_medida']} (unmeasured projection)"))
    print(t(f"tempo ~{e['minutos']} min, ~{e['chamadas']} chamadas; atualização por commit: US$ "
            f"{e['checkpoint_por_commit_usd']} (só scripts)",
            f"time ~{e['minutos']} min, ~{e['chamadas']} calls; update per commit: US$ "
            f"{e['checkpoint_por_commit_usd']} (scripts only)"))
    print(t(f"método: {e['metodo']}; {e['tipo']}", f"method: {e['metodo']}; {e['tipo']}"))
    existem = len(p["arquivos"]) - p["a_criar"]
    print(t(f"arquivos: {p['a_criar']} a criar, {existem} já existem (mantidos)",
            f"files: {p['a_criar']} to create, {existem} already exist (kept)"))
    for f in p["arquivos"][: (None if a.todos else 12)]:
        print(f"  {_acao(f['acao']):6} {f['caminho']}")
    if not a.todos and len(p["arquivos"]) > 12:
        print(t(f"  ... (+{len(p['arquivos']) - 12}; --todos lista tudo)",
                f"  ... (+{len(p['arquivos']) - 12}; --all lists everything)"))
    c = p["consentimento"]
    print(t("consentimento:", "consent:"),
          f"{c['escopos']} {t('teto', 'cap')}={c['orcamento_mensal_usd']} ({c['data']})" if c
          else t("nenhum", "none"))
    print(t("este plano gastou 0 tokens. Para autorizar: python -m lodemap consentir --escopos gerar[,modelo] "
            "[--orcamento-mensal X]",
            "this plan spent 0 tokens. To authorize: python -m lodemap consent --scopes gerar[,modelo] "
            "[--monthly-budget X]"))
    return 0


def cmd_consentir(a) -> int:
    p = permissao.consentir(Path(a.repo), _lista(a.escopos), a.orcamento_mensal, a.arq)
    print(t("consentimento gravado:", "consent recorded:"), p)
    return 0


def cmd_revogar(a) -> int:
    if permissao.ler_consentimento(Path(a.repo).resolve(), a.arq) is None:
        print(t("nenhum consentimento gravado neste repositório; nada a revogar",
                "no consent recorded in this repository; nothing to revoke"))
        return 0
    r = permissao.revogar(Path(a.repo), _lista(a.escopos) or None, a.arq)
    print(t("consentimento revogado", "consent revoked") if r is None
          else t(f"escopos restantes: {r['escopos']}", f"remaining scopes: {r['escopos']}"))
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
    en = idioma() == "en"
    for i in itens:
        estado = _ESTADO.get(i["estado"], i["estado"]) if en else i["estado"]
        nome = _ITEM.get(i["nome"], i["nome"]) if en else i["nome"]
        print(f"{estado:5} {nome}: {i['detalhe']}")
        if i["acao"] and i["estado"] != "ok":
            print(f"      {t('o que fazer', 'what to do')}: {i['acao']}")
    avisos = sum(1 for i in itens if i["estado"] == "aviso")
    print(t(f"{len(itens)} item(ns): {falhas} falha(s), {avisos} aviso(s). Este diagnóstico gastou 0 tokens.",
            f"{len(itens)} item(s): {falhas} failure(s), {avisos} warning(s). This diagnosis spent 0 tokens."))
    return 1 if falhas else 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m lodemap",
                                 description=t("Lodemap: mapa de arquitetura vivo (linha de comando).",
                                               "Lodemap: living architecture map (command line)."))
    ap.add_argument("--version", action="version", version=f"lodemap {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True, title=t("comandos", "commands"),
                            metavar=t("{instalar,reverter,status,plano,consentir,revogar,verificar,doctor}",
                                      "{install,revert,status,plan,consent,revoke,check,doctor}"))

    def comando(en: str, pt: str, ajuda: str):
        """Subcomando com o nome do idioma ativo e o outro como apelido (os dois sempre valem)."""
        nome, apelido = opcao(en, pt)
        return sub.add_parser(nome, aliases=[apelido] if apelido != nome else [], help=ajuda, description=ajuda)

    def comum(p):
        p.add_argument("--home", help=t("HOME alvo (padrão: o do usuário)", "target HOME (default: the user's)"))
        p.add_argument("--python", default=None,
                       help=t("Python dos hooks (padrão: o atual)", "Python used by the hooks (default: the current one)"))
        return p

    def repo_arq(p):
        p.add_argument("--repo", default=".",
                       help=t("raiz do repositório (padrão: pasta atual)", "repository root (default: current folder)"))
        p.add_argument("--arq", "--arch", default=permissao.ARQ_PADRAO,
                       help=t("pasta do mapa dentro do repositório (padrão: %(default)s)",
                              "map folder inside the repository (default: %(default)s)"))

    p = comum(comando("install", "instalar",
                      t("instala a skill, os agentes e o hook (plano por padrão)",
                        "install the skill, the agents and the hook (a plan by default)")))
    p.add_argument(*opcao("--profile", "--perfil"), dest="perfil", choices=list(instalador.PERFIS), default="padrao",
                   help=t("perfil de instalação (padrão: %(default)s)", "install profile (default: %(default)s)"))
    p.add_argument(*opcao("--apply", "--aplicar"), dest="aplicar", action="store_true",
                   help=t("grava de verdade (sem isto, só mostra o plano)",
                          "really write (without it, only shows the plan)"))
    p.add_argument(*opcao("--without", "--sem"), dest="sem",
                   help=t("opções a desligar, separadas por vírgula (skill, aviso)",
                          "options to turn off, comma separated (skill, aviso)"))
    p.add_argument(*opcao("--with", "--com"), dest="com",
                   help=t("opções a ligar além do perfil, separadas por vírgula",
                          "options to turn on beyond the profile, comma separated"))
    p.add_argument(*opcao("--force", "--forcar"), dest="forcar", action="store_true",
                   help=t("troca o que é de outro dono (com backup)",
                          "replace what belongs to someone else (with backup)"))
    p.set_defaults(f=cmd_instalar)

    p = comum(comando("revert", "reverter",
                      t("desfaz uma instalação pelo manifesto", "undo an install using its manifest")))
    p.add_argument(*opcao("--manifest", "--manifesto"), dest="manifesto",
                   help=t("manifesto a reverter (padrão: o último)", "manifest to revert (default: the last one)"))
    p.set_defaults(f=cmd_reverter)

    p = comum(comando("status", "status", t("mostra o estado da instalação", "show the install state")))
    p.set_defaults(f=cmd_status)

    p = comum(comando("doctor", "diagnostico",
                      t("diagnóstico do ambiente: 0 tokens, sem rede", "environment diagnosis: 0 tokens, no network")))
    p.add_argument("--repo", default=None,
                   help=t("também confere este repositório (mapa e consentimento)",
                          "also check this repository (map and consent)"))
    p.add_argument("--arq", "--arch", default=permissao.ARQ_PADRAO,
                   help=t("pasta do mapa dentro do repositório (padrão: %(default)s)",
                          "map folder inside the repository (default: %(default)s)"))
    p.add_argument("--json", action="store_true", help=t("saída em JSON", "JSON output"))
    p.set_defaults(f=cmd_doctor)

    p = comando("plan", "plano",
                t("o que seria feito e quanto custa: 0 tokens", "what would be done and what it costs: 0 tokens"))
    repo_arq(p)
    p.add_argument("--json", action="store_true", help=t("saída em JSON", "JSON output"))
    p.add_argument(*opcao("--all", "--todos"), dest="todos", action="store_true",
                   help=t("lista todos os arquivos (padrão: os 12 primeiros)", "list every file (default: the first 12)"))
    p.set_defaults(f=cmd_plano)

    p = comando("consent", "consentir", t("grava o consentimento por escopo", "record the consent per scope"))
    repo_arq(p)
    p.add_argument(*opcao("--scopes", "--escopos"), dest="escopos", required=True,
                   help=t("escopos separados por vírgula: " + ", ".join(permissao.ESCOPOS),
                          "comma separated scopes: " + ", ".join(permissao.ESCOPOS)))
    p.add_argument(*opcao("--monthly-budget", "--orcamento-mensal"), dest="orcamento_mensal", type=float,
                   help=t("teto mensal em US$ para os passos com modelo",
                          "monthly cap in US$ for the steps that use a model"))
    p.set_defaults(f=cmd_consentir)

    p = comando("revoke", "revogar",
                t("revoga escopos (ou todo o consentimento)", "revoke scopes (or the whole consent)"))
    repo_arq(p)
    p.add_argument(*opcao("--scopes", "--escopos"), dest="escopos",
                   help=t("escopos a revogar, separados por vírgula (padrão: todos)",
                          "scopes to revoke, comma separated (default: all)"))
    p.set_defaults(f=cmd_revogar)

    p = comando("check", "verificar",
                t("diz se um escopo está autorizado (sai com 3 se não)",
                  "tell whether a scope is authorized (exit 3 if not)"))
    repo_arq(p)
    p.add_argument(*opcao("--scope", "--escopo"), dest="escopo", required=True, choices=list(permissao.ESCOPOS),
                   help=t("escopo a verificar", "scope to check"))
    p.add_argument(*opcao("--cost", "--custo"), dest="custo", type=float, default=0.0,
                   help=t("custo estimado em US$ do passo (padrão: %(default)s)",
                          "estimated cost in US$ of the step (default: %(default)s)"))
    p.set_defaults(f=cmd_verificar)
    return ap


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    usar_mapa(None)
    a = parser().parse_args(argv)
    if getattr(a, "repo", None):  # o comando aponta um repositório: o idioma do mapa dele entra na regra
        usar_mapa(Path(a.repo) / a.arq)
    try:
        return a.f(a)
    except ValueError as e:
        print(t("erro:", "error:"), e)
        return 2
