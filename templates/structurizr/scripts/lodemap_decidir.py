"""Política de atualização da lodemap: mede a "dívida do mapa" e diz a ação mais barata que basta, sem gastar token.

Uso (na pasta da arquitetura):
  python scripts/lodemap_decidir.py                      # JSON com a decisão (acao, motivos, divida, lote, proximo)
  python scripts/lodemap_decidir.py --resumo             # uma linha, no idioma do mapa
  python scripts/lodemap_decidir.py --adiar              # registra em pendentes.json os módulos fora do modelo
  python scripts/lodemap_decidir.py --gancho post-commit # sai 0 se o gancho deve regenerar por scripts agora
  python scripts/lodemap_decidir.py --skill <pasta>      # pasta da skill Lodemap (padrão: LODEMAP_SKILL, ou
                                                         # ~/.claude/skills/lodemap se existir)

Ações, da mais barata à mais cara: nada, scripts (atualizar.py, 0 tokens), adiar (0 tokens: só registra o prazo),
descrever (uma sessão de modelo só para as descrições), modelar (uma sessão para componentes e relações) e gerar
(primeira geração). Só descrever, modelar e gerar chamam modelo; o resto roda por script.

A política é o bloco opcional "politica" do lodemap.json (valor inválido ou negativo cai no padrão):
  tolerancia_modulos (0)         quantos módulos podem esperar fora do modelo; 0 = estrito, como antes
  tolerancia_dias (14)           por quanto tempo um módulo adiado pode esperar
  revisoes_para_atualizar (10)   descrições a revisar (superfície pública mudou) que justificam uma sessão
  relacoes_para_atualizar (10)   relações novas que justificam uma sessão
  commits_para_regenerar (10)    commits de código desde a última geração antes de regenerar por scripts

Os módulos adiados ficam em <arq>/pendentes.json (versionado, de propósito fora de .lodemap/, que o git ignora): é o
prazo que o teste de cobertura lê. Só usa a biblioteca padrão. LODEMAP_HOJE (AAAA-MM-DD) troca a data de hoje (testes).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arq_comum import caminhos_quebrados, elementos_dsl, fora_do_modelo  # noqa: E402
from lodemap_diff import _en, diff, fontes_mudaram, git, ler_estado, raiz_repo, relevante  # noqa: E402

PENDENTES = "pendentes.json"
PADROES = {
    "tolerancia_modulos": 0,
    "tolerancia_dias": 14,
    "revisoes_para_atualizar": 10,
    "relacoes_para_atualizar": 10,
    "commits_para_regenerar": 10,
}
USAM_MODELO = ("descrever", "modelar", "gerar")
TEMPO_SKILL = 120  # segundos


# ---------------------------------------------------------------- política e datas

def politica(cfg: dict) -> dict:
    """Valores efetivos do bloco "politica": inteiro >= 0, senão o padrão."""
    bloco = cfg.get("politica") if isinstance(cfg.get("politica"), dict) else {}
    out = {}
    for nome, padrao in PADROES.items():
        v = bloco.get(nome)
        out[nome] = v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else padrao
    return out


def hoje() -> date:
    """Hoje; LODEMAP_HOJE (AAAA-MM-DD) vence, para os testes."""
    bruto = (os.environ.get("LODEMAP_HOJE") or "").strip()
    if bruto:
        try:
            return date.fromisoformat(bruto)
        except ValueError:
            pass
    return date.today()


def _data(valor) -> date | None:
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None


def ler_config(arq: Path) -> dict:
    return json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------- pendentes.json

def ler_pendentes(arq: Path, estrito: bool = False) -> dict:
    """{módulo: {"desde", "commit"}}. Arquivo ausente ou ilegível vira {} (com estrito=True, o ilegível levanta)."""
    en = _en(arq)
    p = arq / PENDENTES
    if not p.is_file():
        return {}
    try:
        dados = json.loads(p.read_text(encoding="utf-8-sig"))
        mods = dados["modulos"]
        if not isinstance(mods, dict):
            raise ValueError("'modulos' is not an object" if en else "modulos não é um objeto")
        return {k: v for k, v in mods.items() if isinstance(v, dict)}
    except (OSError, ValueError, KeyError, TypeError) as e:
        if estrito:
            raise ValueError(f"{p} unreadable: {e}" if en else f"{p} ilegível: {e}") from e
        return {}


def gravar_pendentes(arq: Path, modulos: dict) -> None:
    """Chaves ordenadas, UTF-8, LF e uma quebra de linha no fim; sem módulos, apaga o arquivo."""
    p = arq / PENDENTES
    if not modulos:
        p.unlink(missing_ok=True)
        return
    texto = json.dumps({"versao": 1, "modulos": modulos}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    p.write_text(texto, encoding="utf-8", newline="\n")


def _head_curto(repo: Path) -> str:
    cod, out = git(repo, "rev-parse", "--short", "HEAD")
    return out.strip() if cod == 0 else ""


# ---------------------------------------------------------------- sinais da skill (opcionais)

def resolver_skill(skill: str | Path | None = None) -> Path | None:
    """Pasta da skill: argumento, senão LODEMAP_SKILL, senão ~/.claude/skills/lodemap. None sem scripts/esqueleto.py."""
    cand = skill or os.environ.get("LODEMAP_SKILL") or ""
    pasta = Path(cand) if cand else Path.home() / ".claude" / "skills" / "lodemap"
    return pasta if (pasta / "scripts" / "esqueleto.py").is_file() else None


def sinais_skill(arq: Path, skill: Path | None, t) -> tuple[int | None, int | None, str]:
    """(revisoes, relacoes_novas, motivo). Sem skill, com falha ou sem decisões: (None, None, motivo "n/d"). Nunca inventa."""
    if skill is None:
        return None, None, t("n/d: skill do Lodemap não encontrada (use --skill ou LODEMAP_SKILL); revisões e relações novas ficam sem medida",
                             "n/a: Lodemap skill not found (use --skill or LODEMAP_SKILL); reviews and new relationships are not measured")
    cmd = [sys.executable, str(skill / "scripts" / "esqueleto.py"), "pendencias", "--arq", str(arq)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TEMPO_SKILL,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None, None, t(f"n/d: esqueleto.py pendencias passou de {TEMPO_SKILL} s",
                             f"n/a: esqueleto.py pendencias took more than {TEMPO_SKILL} s")
    except OSError as e:
        return None, None, t(f"n/d: não consegui rodar o esqueleto.py ({e})", f"n/a: could not run esqueleto.py ({e})")
    try:
        dados = json.loads(r.stdout)
        if r.returncode or not isinstance(dados, dict):
            raise ValueError(f"exit code {r.returncode}" if _en(arq) else f"código {r.returncode}")
        if dados.get("sem_decisoes"):
            return None, None, t("n/d: ainda não há .lodemap/decisoes-modelo.json; revisões e relações novas ficam sem medida",
                                 "n/a: there is no .lodemap/decisoes-modelo.json yet; reviews and new relationships are not measured")
        return len(dados.get("componentes_revisar") or []), len(dados.get("relacoes_novas") or []), ""
    except (ValueError, TypeError) as e:
        return None, None, t(f"n/d: esqueleto.py pendencias falhou ({e})", f"n/a: esqueleto.py pendencias failed ({e})")


# ---------------------------------------------------------------- decisão

def decidir(arq: Path, skill: str | Path | None = None, usar_skill: bool = True, data: date | None = None) -> dict:
    arq = Path(arq).resolve()
    en = _en(arq)

    def t(pt: str, ingles: str) -> str:
        return ingles if en else pt

    cfg = ler_config(arq)
    pol = politica(cfg)
    data = data or hoje()
    repo = raiz_repo(arq)
    d = diff(arq, trabalho=True)
    fora = fora_do_modelo(arq, repo)
    quebrados = caminhos_quebrados(arq, repo)
    pend = ler_pendentes(arq)

    # módulos fora do modelo que já têm prazo registrado, e os que passaram dele
    adiados, vencidos, sem_registro = [], [], []
    for m in fora:
        desde = _data((pend.get(m) or {}).get("desde"))
        if desde is None:
            sem_registro.append(m)
            continue
        vence = desde + timedelta(days=pol["tolerancia_dias"])
        item = {"modulo": m, "desde": desde.isoformat(), "vence": vence.isoformat()}
        adiados.append(item)
        if data > vence:
            vencidos.append(item)

    estado = ler_estado(arq)
    de = estado.get("ultimoCommit")
    commits_desde = None
    if de:
        cod, out = git(repo, "rev-list", "--count", f"{de}..HEAD")
        commits_desde = int(out.strip()) if cod == 0 and out.strip().isdigit() else None
    dias_desde = None
    try:
        dias_desde = (data - datetime.fromisoformat(str(estado["geradoEm"])).date()).days
    except (KeyError, ValueError, TypeError):
        pass

    novos = d.get("modulosNovos", [])
    mudados = d.get("modulosMudados", [])
    removidos = d.get("modulosRemovidos", [])
    n_mudados = len(novos) + len(mudados) + len(removidos)

    revisoes = relacoes = None
    motivo_nd = ""
    if usar_skill:
        revisoes, relacoes, motivo_nd = sinais_skill(arq, resolver_skill(skill), t)

    motivos: list[str] = []
    escolha: dict = {"acao": None}

    def achar(motivo: str, acao: str | None = None) -> None:
        """Registra um motivo; o primeiro que traz uma ação a define, e o seu motivo vai para o começo da lista."""
        if acao and escolha["acao"] is None:
            escolha["acao"] = acao
            motivos.insert(0, motivo)
        else:
            motivos.append(motivo)

    # 1. sem modelo: primeira geração. Sem geração registrada mas com modelo (clone novo, CI: .lodemap/ fica fora do
    #    git), as regras 2 a 4 valem primeiro; só se nenhuma pedir ação é que basta regenerar por scripts (fim da função).
    if d["modo"] == "completo" and not any(e["tipo"] == "component" for e in elementos_dsl(arq)):
        achar(t("o modelo ainda não tem nenhum componente: primeira geração", "the model has no component yet: first generation"), "gerar")
    # 2. caminho citado que não existe
    if quebrados:
        achar(t(f"{len(quebrados)} caminho(s) citado(s) por componente não existe(m): {', '.join(quebrados)}",
                f"{len(quebrados)} path(s) cited by components do(es) not exist: {', '.join(quebrados)}"), "modelar")
    # 3. módulos fora do modelo
    n = len(fora)
    tol = pol["tolerancia_modulos"]
    if n:
        lista = ", ".join(fora)
        if tol == 0:
            achar(t(f"{n} módulo(s) fora do modelo (tolerância 0): {lista}", f"{n} module(s) outside the model (tolerance 0): {lista}"), "modelar")
        elif n > tol:
            achar(t(f"{n} módulo(s) fora do modelo, acima da tolerância de {tol}: {lista}",
                    f"{n} module(s) outside the model, over the tolerance of {tol}: {lista}"), "modelar")
        if vencidos:
            achar(t("prazo vencido para: " + ", ".join(f"{v['modulo']} (venceu em {v['vence']})" for v in vencidos),
                    "deadline passed for: " + ", ".join(f"{v['modulo']} (expired on {v['vence']})" for v in vencidos)), "modelar")
        if tol and n <= tol and not vencidos:
            if sem_registro:
                achar(t(f"{len(sem_registro)} módulo(s) fora do modelo cabem na tolerância ({n} de {tol}) mas ainda não têm prazo: "
                        + ", ".join(sem_registro), f"{len(sem_registro)} module(s) outside the model fit the tolerance ({n} of {tol}) "
                        "but have no deadline yet: " + ", ".join(sem_registro)), "adiar")
            else:
                ate = min(v["vence"] for v in adiados)
                achar(t(f"{n} módulo(s) fora do modelo podem esperar até {ate}", f"{n} module(s) outside the model may wait until {ate}"))
    # 4. sinais da skill
    if motivo_nd:
        achar(motivo_nd)
    if relacoes is not None and relacoes >= pol["relacoes_para_atualizar"]:
        achar(t(f"{relacoes} relação(ões) nova(s) no código (limite {pol['relacoes_para_atualizar']})",
                f"{relacoes} new relationship(s) in the code (limit {pol['relacoes_para_atualizar']})"), "modelar")
    if revisoes is not None and revisoes >= pol["revisoes_para_atualizar"]:
        achar(t(f"{revisoes} descrição(ões) a revisar, superfície pública mudou (limite {pol['revisoes_para_atualizar']})",
                f"{revisoes} description(s) to review, public surface changed (limit {pol['revisoes_para_atualizar']})"), "descrever")
    # 5. regenerar por scripts
    if d["modo"] == "incremental":
        fontes = fontes_mudaram(arq, d["de"])
        cadencia = pol["commits_para_regenerar"]
        if fontes:
            achar(t("arquivos-fonte da arquitetura mudaram desde a última geração", "architecture source files changed since the last generation"), "scripts")
        if novos or removidos:
            achar(t(f"o conjunto de módulos mudou ({len(novos)} novo(s), {len(removidos)} removido(s))",
                    f"the module set changed ({len(novos)} new, {len(removidos)} removed)"), "scripts")
        if n_mudados and commits_desde is not None and commits_desde >= cadencia:
            achar(t(f"{n_mudados} módulo(s) mudaram e já são {commits_desde} commit(s) desde a última geração (cadência {cadencia})",
                    f"{n_mudados} module(s) changed and it has been {commits_desde} commit(s) since the last generation (cadence {cadencia})"), "scripts")
        # 6. e 7. nada a fazer agora
        if escolha["acao"] is None:
            if n_mudados:
                cd = "n/d" if commits_desde is None else commits_desde
                achar(t(f"{cd} commit(s) desde a última geração; regenera em {cadencia}",
                        f"{cd} commit(s) since the last generation; regenerates at {cadencia}"), "nada")
            else:
                achar(t("nada mudou desde a última geração", "nothing changed since the last generation"), "nada")
    elif escolha["acao"] is None:
        achar(t(f"sem geração anterior registrada ({d.get('motivo', '')})", f"no previous generation recorded ({d.get('motivo', '')})"), "scripts")
    acao = escolha["acao"] or "nada"
    usa_modelo = acao in USAM_MODELO

    divida = {
        "modulos_fora": fora,
        "adiados": adiados,
        "vencidos": vencidos,
        "caminhos_quebrados": quebrados,
        "revisoes": revisoes,
        "relacoes_novas": relacoes,
        "modulos_mudados": n_mudados,
        "commits_desde": commits_desde,
        "dias_desde": dias_desde,
    }
    lote = {"modulos_fora": fora, "caminhos_quebrados": quebrados, "revisoes": revisoes, "relacoes_novas": relacoes} if usa_modelo else None
    return {"acao": acao, "usa_modelo": usa_modelo, "motivos": motivos, "divida": divida, "lote": lote,
            "politica": pol, "proximo": _proximo(arq, repo, acao, lote, t)}


def _proximo(arq: Path, repo: Path, acao: str, lote: dict | None, t) -> list[str]:
    if acao == "adiar":
        return ["python scripts/lodemap_decidir.py --adiar"]
    if acao == "scripts":
        rotulo = f"lodemap_decidir {_head_curto(repo)}".strip()
        return [f'python scripts/atualizar.py --incremental --checkpoint "{rotulo}"']
    if acao == "gerar":
        return [t("Rode a geração completa do Lodemap (a skill) uma vez: o modelo ainda não tem componentes.",
                  "Run the full Lodemap generation (the skill) once: the model has no components yet.")]
    if lote is not None:
        def num(v):
            return "n/d" if v is None else str(v)
        return [t(f"Rode a atualização incremental da skill Lodemap uma vez para o lote todo: {len(lote['modulos_fora'])} módulo(s) fora do modelo, "
                  f"{len(lote['caminhos_quebrados'])} caminho(s) quebrado(s), {num(lote['revisoes'])} revisão(ões), {num(lote['relacoes_novas'])} relação(ões) nova(s).",
                  f"Run the Lodemap skill's incremental update once for the whole lot: {len(lote['modulos_fora'])} module(s) outside the model, "
                  f"{len(lote['caminhos_quebrados'])} broken path(s), {num(lote['revisoes'])} review(s), {num(lote['relacoes_novas'])} new relationship(s).")]
    return []


def resumo(dec: dict, en: bool) -> str:
    """Uma linha: a ação, o motivo principal e o que espera."""
    linha = f"Lodemap: {dec['acao']}"
    if dec["motivos"]:
        linha += f" - {dec['motivos'][0]}"
    esperam = dec["divida"]["adiados"]
    if esperam and dec["acao"] not in ("modelar", "adiar"):
        ate = min(a["vence"] for a in esperam)
        linha += f" | {'waiting' if en else 'esperam'}: {len(esperam)} {'module(s) until' if en else 'módulo(s) até'} {ate}"
    return linha


# ---------------------------------------------------------------- --adiar

def adiar(arq: Path) -> tuple[int, str]:
    """Registra os módulos fora do modelo em pendentes.json. Devolve (código de saída, mensagem)."""
    arq = Path(arq).resolve()
    en = _en(arq)

    def t(pt: str, ingles: str) -> str:
        return ingles if en else pt

    pol = politica(ler_config(arq))
    tol = pol["tolerancia_modulos"]
    if tol == 0:
        return 1, t("politica.tolerancia_modulos é 0 no lodemap.json: nada pode esperar fora do modelo. Ligue os módulos a componentes "
                    "ou defina uma tolerância; nada foi gravado.",
                    "politica.tolerancia_modulos is 0 in lodemap.json: nothing may wait outside the model. Map the modules to components "
                    "or set a tolerance; nothing was written.")
    repo = raiz_repo(arq)
    fora = fora_do_modelo(arq, repo)
    if len(fora) > tol:
        return 1, t(f"{len(fora)} módulo(s) fora do modelo, acima da tolerância de {tol}; nada foi gravado. Modele pelo menos "
                    f"{len(fora) - tol}: " + ", ".join(fora),
                    f"{len(fora)} module(s) outside the model, over the tolerance of {tol}; nothing was written. Model at least "
                    f"{len(fora) - tol}: " + ", ".join(fora))
    try:
        antes = ler_pendentes(arq, estrito=True)
    except ValueError as e:
        return 1, t(f"{e}; nada foi gravado.", f"{e}; nothing was written.")
    commit, hoje_ = _head_curto(repo), hoje().isoformat()
    depois, novos = {}, []
    for m in fora:
        velho = antes.get(m)
        if velho is not None and _data(velho.get("desde")) is not None:
            depois[m] = velho  # o prazo nunca se estende rodando de novo
        else:
            depois[m] = {"desde": hoje_, "commit": commit}
            novos.append(m)
    podados = sorted(set(antes) - set(depois))
    if depois != antes:
        gravar_pendentes(arq, depois)
    ate = (date.fromisoformat(hoje_) + timedelta(days=pol["tolerancia_dias"])).isoformat()
    partes = [t(f"{len(novos)} módulo(s) adiado(s) (valem até {ate}), {len(podados)} entrada(s) podada(s); {len(depois)} em {PENDENTES}",
                f"{len(novos)} module(s) deferred (valid until {ate}), {len(podados)} entr(y/ies) pruned; {len(depois)} in {PENDENTES}")]
    if novos:
        partes.append(", ".join(novos))
    return 0, "\n".join(partes)


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    en = _en(Path(__file__).resolve().parent.parent)
    ap = argparse.ArgumentParser(description=("Update policy of the lodemap: measures the map's debt and names the cheapest "
                                              "action that is enough, spending no tokens." if en
                                              else __doc__.splitlines()[0]))
    ap.add_argument("--arq", "--arch", default=str(Path(__file__).resolve().parent.parent),
                    help=("the architecture folder (default: the one above scripts/)" if en
                          else "pasta da arquitetura (padrão: a acima de scripts/)"))
    ap.add_argument("--skill", help=("Lodemap skill folder (default: LODEMAP_SKILL, or ~/.claude/skills/lodemap)" if en
                                     else "pasta da skill Lodemap (padrão: LODEMAP_SKILL, ou ~/.claude/skills/lodemap)"))
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument("--resumo", "--summary", action="store_true",
                      help=("one line with the action, the reason and what it expects" if en
                            else "uma linha com a ação, o motivo e o que espera"))
    modo.add_argument("--adiar", "--defer", action="store_true",
                      help=("record the modules outside the model in pendentes.json" if en
                            else "registra os módulos fora do modelo em pendentes.json"))
    modo.add_argument("--gancho", "--hook", choices=["post-commit", "post-merge"],
                      help=("exit 0 if the hook should regenerate by scripts now, 1 if not" if en
                            else "sai 0 se o gancho deve regenerar por scripts agora, 1 se não"))
    a = ap.parse_args(argv)
    arq = Path(a.arq).resolve()
    try:
        if a.adiar:
            codigo, msg = adiar(arq)
            print(msg)
            return codigo
        if a.gancho == "post-merge":
            return 0 if relevante(arq) else 1
        if a.gancho == "post-commit":
            dec = decidir(arq, usar_skill=False)
            if dec["acao"] == "scripts":
                return 0
            print(resumo(dec, _en(arq)))
            return 1
        dec = decidir(arq, a.skill)
        if a.resumo:
            print(resumo(dec, _en(arq)))
        else:
            print(json.dumps(dec, ensure_ascii=False, indent=2))
        return 0
    except SystemExit:
        raise
    except Exception as e:  # mensagem curta em vez de traceback; o gancho trata o código 1 como "não regenere"
        print(f"lodemap_decidir: {e!r}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
