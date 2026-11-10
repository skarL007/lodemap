#!/usr/bin/env python3
"""Lodemap: valida o modelo, exporta o JSON e regenera os documentos derivados, o leitor e o explorador.

Equivalente multiplataforma (Windows, Linux e macOS) do atualizar.ps1: Python 3.10+, só a biblioteca padrão.
O atualizar.ps1 continua existindo como invólucro fino que chama este arquivo.

Uso (de qualquer pasta; a raiz é a pasta acima de scripts/):
  python scripts/atualizar.py
  python scripts/atualizar.py --incremental --checkpoint "merge feat/x"
  python scripts/atualizar.py --com-site

Mapeamento dos parâmetros do atualizar.ps1 para as flags (os padrões via ambiente são os mesmos):

  -Ferramentas <pasta>   --ferramentas <pasta>   env STRUCTURIZR_FERRAMENTAS, senão ~/.structurizr
  -Python <exe>          --python <exe>          env LODEMAP_PYTHON, senão o Python que roda este script
  -Template <pasta>      --template <pasta>      env LODEMAP_TEMPLATE, senão <LODEMAP_SKILL>/templates/structurizr,
                                                 senão ~/.claude/skills/lodemap/templates/structurizr
  -Checkpoint <texto>    --checkpoint <texto>    (--checkpoint-env lê o rótulo de LODEMAP_CHECKPOINT)
  -ComSite               --com-site
  -SemExtensoes          --sem-extensoes
  -SemSite               --sem-site              (compatibilidade: o site já fica de fora sem --com-site)
  -Incremental           --incremental
  (novo)                 --cli <arquivo>         força o structurizr.bat / structurizr.sh

Structurizr CLI (structurizr.bat no Windows, structurizr.sh nos outros sistemas), nesta ordem:
  1. env STRUCTURIZR_CLI (o arquivo, ou a pasta que o contém);
  2. <ferramentas>/cli/ (padrão ~/.structurizr/cli/);
  3. o PATH.
Sem ele, o script para com a explicação de como instalar. O Graphviz (dot) é procurado em <ferramentas>/graphviz
e depois no PATH (shutil.which); só o site estático (--com-site) precisa dele.

Etapas, na ordem: [incremental] páginas fixas faltantes; 1 validate; 2 export json; 3 gerar_docs; 4 gerar_leitor;
5 codegraph_ponte --relacoes e gerar_explorador; 6 extensões locais ("extensoes" do lodemap.json e env
LODEMAP_EXTENSOES, separada por ";" e, fora do Windows, também por ":"); 7 site estático (--com-site);
por fim lodemap_diff --marcar e, se o script da skill existir, a linha do tempo da arquitetura (linha_do_tempo.py,
lida do git; sem repositório git ela é pulada com aviso). Falha de etapa obrigatória (1 a 5): código 1. Falha de
extensão, da ponte, do site, do --marcar ou da linha do tempo: só aviso.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

NOME_CLI_WINDOWS = ("structurizr.bat",)
NOME_CLI_OUTROS = ("structurizr.sh", "structurizr", "structurizr-cli")
FIXOS = (Path("explorador") / "index.html", Path("explorador") / "vendor",
         Path("leitor") / "index.html", Path("leitor") / "vendor")


class Falha(Exception):
    """Etapa obrigatória que não passou: o script termina com este código."""

    def __init__(self, mensagem: str, codigo: int = 1):
        super().__init__(mensagem)
        self.codigo = codigo


def _windows() -> bool:
    return os.name == "nt"


_EN = False  # o executar() liga quando o lodemap.json (ou LODEMAP_IDIOMA) pede inglês


def _idioma_en(raiz: Path, env=None) -> bool:
    """Idioma do mapa: LODEMAP_IDIOMA vence o "idioma" do lodemap.json; qualquer coisa fora "en" é português."""
    i = ((env if env is not None else os.environ).get("LODEMAP_IDIOMA") or "").strip().lower()
    if not i:
        try:
            i = str(json.loads((raiz / "lodemap.json").read_text(encoding="utf-8")).get("idioma") or "")
        except (OSError, ValueError, AttributeError):
            i = ""
    return i == "en"


def aviso(texto: str, en: str | None = None) -> None:
    print(f"WARNING: {en}" if _EN and en else f"AVISO: {texto}", file=sys.stderr, flush=True)


def info(texto: str, en: str | None = None) -> None:
    print(en if _EN and en else texto, flush=True)


def _t(pt: str, en: str) -> str:
    """O texto no idioma do mapa (para mensagens que não passam por aviso/info, como as de Falha)."""
    return en if _EN else pt


# --------------------------------------------------------------------------------------------- argumentos

def parse_args(argv=None, env=None) -> argparse.Namespace:
    env = os.environ if env is None else env
    ferr = env.get("STRUCTURIZR_FERRAMENTAS") or str(Path.home() / ".structurizr")
    skill = Path(env["LODEMAP_SKILL"]).expanduser() if env.get("LODEMAP_SKILL") else Path.home() / ".claude" / "skills" / "lodemap"
    tpl = env.get("LODEMAP_TEMPLATE") or str(skill / "templates" / "structurizr")
    en = _idioma_en(Path(__file__).resolve().parent.parent, env)  # a ajuda sai no idioma do mapa
    ap = argparse.ArgumentParser(prog="atualizar.py",
                                 description=("Regenerates the architecture map: validate, export, docs, reader, explorer."
                                              if en else __doc__.splitlines()[0]))
    ap.add_argument("--ferramentas", "--tools", default=ferr,
                    help=("folder with cli/ and graphviz/ (default: %(default)s)" if en
                          else "pasta com cli/ e graphviz/ (padrão: %(default)s)"))
    ap.add_argument("--python", default=env.get("LODEMAP_PYTHON") or sys.executable,
                    help=("Python executable used by the generators (default: %(default)s)" if en
                          else "executável do Python dos geradores (padrão: %(default)s)"))
    ap.add_argument("--template", default=tpl,
                    help=("the skill's templates/structurizr folder (default: %(default)s)" if en
                          else "pasta templates/structurizr da skill (padrão: %(default)s)"))
    ap.add_argument("--cli", default="",
                    help=("path of structurizr.bat / structurizr.sh (wins over the search)" if en
                          else "caminho do structurizr.bat / structurizr.sh (vence a busca)"))
    ap.add_argument("--checkpoint", default="",
                    help=("checkpoint label, for estado.json and the extensions" if en
                          else "rótulo do checkpoint, para o estado.json e as extensões"))
    ap.add_argument("--checkpoint-env", action="store_true",
                    help=("read the label from the LODEMAP_CHECKPOINT variable (accents intact, not through the "
                          "command line)" if en
                          else "lê o rótulo da variável LODEMAP_CHECKPOINT (acentos intactos, sem passar pela linha de comando)"))
    ap.add_argument("--com-site", "--with-site", action="store_true",
                    help=("also export the static site to ../site" if en else "exporta também o site estático em ../site"))
    ap.add_argument("--sem-site", "--without-site", action="store_true",
                    help=("compatibility (the git hook passes it)" if en else "compatibilidade (o gancho do git o passa)"))
    ap.add_argument("--sem-extensoes", "--without-extensions", action="store_true",
                    help=("do not run the local extensions" if en else "não roda as extensões locais"))
    ap.add_argument("--incremental", action="store_true",
                    help=("exit without regenerating if nothing changed since the last run" if en
                          else "sai sem regenerar se nada mudou desde a última geração"))
    a = ap.parse_args(argv)
    if a.checkpoint_env and not a.checkpoint:
        a.checkpoint = env.get("LODEMAP_CHECKPOINT", "")
    return a


# --------------------------------------------------------------------------------------------- descoberta

def _cli_em(pasta: Path, windows: bool) -> Path | None:
    for nome in (NOME_CLI_WINDOWS if windows else NOME_CLI_OUTROS):
        c = pasta / nome
        if c.is_file():
            return c
    return None


def localizar_cli(ferramentas: str | Path, env=None, which=shutil.which, windows: bool | None = None,
                  explicito: str = "") -> Path:
    """Acha o Structurizr CLI: --cli, env STRUCTURIZR_CLI, <ferramentas>/cli, PATH. Sem ele, levanta Falha."""
    env = os.environ if env is None else env
    windows = _windows() if windows is None else windows
    tentados: list[str] = []
    for origem, valor in (("--cli", explicito), ("STRUCTURIZR_CLI", env.get("STRUCTURIZR_CLI", ""))):
        if not valor:
            continue
        p = Path(valor).expanduser()
        achado = p if p.is_file() else (_cli_em(p, windows) if p.is_dir() else None)
        if achado:
            return achado
        tentados.append(f"{origem}={valor} ({_t('não existe', 'does not exist')})")
        aviso(f"{origem} aponta para {valor}, que não é o Structurizr CLI; sigo procurando.",
              f"{origem} points to {valor}, which is not the Structurizr CLI; I keep looking.")
    pasta = Path(ferramentas).expanduser() / "cli"
    achado = _cli_em(pasta, windows)
    if achado:
        return achado
    tentados.append(f"{pasta}")
    for nome in (NOME_CLI_WINDOWS if windows else NOME_CLI_OUTROS):
        achado = which(nome, path=env.get("PATH"))
        if achado:
            return Path(achado)
    tentados.append("PATH")
    nome_cli = "structurizr.bat" if windows else "structurizr.sh"
    destino = str(Path(ferramentas).expanduser() / "cli")
    if _EN:
        raise Falha(
            f"I could not find the Structurizr CLI ({nome_cli}).\n"
            "  Looked in: " + "; ".join(tentados) + ".\n"
            "  How to install: download structurizr-cli.zip from https://github.com/structurizr/cli/releases, extract it to "
            + destino + " (needs Java 17+),\n"
            f"  or point the STRUCTURIZR_CLI variable at {nome_cli}.")
    raise Falha(
        f"Não achei o Structurizr CLI ({nome_cli}).\n"
        "  Procurei em: " + "; ".join(tentados) + ".\n"
        "  Como instalar: baixe structurizr-cli.zip em https://github.com/structurizr/cli/releases, extraia em "
        + destino + " (precisa do Java 17+),\n"
        "  ou aponte a variável STRUCTURIZR_CLI para o structurizr.bat / structurizr.sh.")


def comando_cli(cli: Path, windows: bool | None = None) -> list[str]:
    """Prefixo do comando. .sh sem permissão de execução roda por bash (Linux e macOS)."""
    windows = _windows() if windows is None else windows
    if not windows and cli.suffix == ".sh" and not os.access(cli, os.X_OK):
        return [shutil.which("bash") or "bash", str(cli)]
    return [str(cli)]


def achar_dot(ferramentas: str | Path, which=shutil.which, windows: bool | None = None) -> str | None:
    """dot empacotado em <ferramentas>/graphviz (como o .ps1 fazia) ou o do PATH (shutil.which)."""
    windows = _windows() if windows is None else windows
    base = Path(ferramentas).expanduser() / "graphviz"
    if base.is_dir():
        for c in sorted(base.rglob("dot.exe" if windows else "dot")):
            if c.is_file():
                return str(c)
    return which("dot")


# --------------------------------------------------------------------------------------------- subprocessos

def _rodar(cmd: list[str], env: dict | None = None, capturar: bool = False, descartar: bool = False,
           cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Único ponto onde o script cria processos: lista de argumentos, nunca shell, UTF-8."""
    kw: dict = {"env": env, "cwd": str(cwd) if cwd else None, "encoding": "utf-8", "errors": "replace"}
    if capturar:
        kw.update(capture_output=True)
    elif descartar:
        kw.update(stdout=subprocess.DEVNULL)
    return subprocess.run(cmd, **kw)


def _env_filho(dot: str | None, checkpoint: str | None = None) -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if dot:
        env["PATH"] = str(Path(dot).parent) + os.pathsep + env.get("PATH", "")
    if checkpoint is not None:
        env["LODEMAP_CHECKPOINT"] = checkpoint
    return env


# --------------------------------------------------------------------------------------------- extensões

def reunir_extensoes(raiz: Path, env=None, windows: bool | None = None) -> list[str]:
    """Extensões do lodemap.json ("extensoes") e da env LODEMAP_EXTENSOES (";", e ":" fora do Windows)."""
    env = os.environ if env is None else env
    windows = _windows() if windows is None else windows
    lista: list[str] = []
    cfg_arq = raiz / "lodemap.json"
    if cfg_arq.is_file():
        try:
            cfg = json.loads(cfg_arq.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            aviso(f"Não consegui ler {cfg_arq}: {e}", f"Could not read {cfg_arq}: {e}")
            cfg = {}
        ext = cfg.get("extensoes") if isinstance(cfg, dict) else None
        if isinstance(ext, str):
            ext = [ext]
        if isinstance(ext, list):
            lista += [e for e in ext if isinstance(e, str) and e]
    bruto = env.get("LODEMAP_EXTENSOES", "")
    if bruto:
        if not windows:
            bruto = bruto.replace(":", ";")
        lista += [e for e in bruto.split(";") if e]
    return lista


def rodar_extensoes(extensoes: list[str], python: str, json_ws: Path, raiz: Path, repo: Path,
                    checkpoint: str, dot: str | None = None) -> int:
    """Roda cada extensão com o workspace.json, --arq e --repo. Falha vira aviso. Devolve quantas falharam."""
    env = _env_filho(dot, checkpoint)
    falhas = 0
    for ext in extensoes:
        caminho = Path(os.path.expandvars(os.path.expanduser(ext)))
        if not caminho.exists():
            aviso(f"Extensão não encontrada: {caminho}", f"Extension not found: {caminho}")
            falhas += 1
            continue
        try:
            r = _rodar([python, str(caminho), str(json_ws), "--arq", str(raiz), "--repo", str(repo)], env=env)
            rc = r.returncode
        except OSError as e:
            aviso(f"Não consegui iniciar a extensão {caminho}: {e}", f"Could not start the extension {caminho}: {e}")
            falhas += 1
            continue
        if rc != 0:
            aviso(f"A extensão {caminho} falhou (código {rc}); o resto está pronto.",
                  f"The extension {caminho} failed (code {rc}); everything else is ready.")
            falhas += 1
    return falhas


# --------------------------------------------------------------------------------------------- pipeline

def _copiar_fixos(raiz: Path, template: Path) -> bool:
    """Copia do template as páginas fixas que faltarem. Devolve se o template é utilizável."""
    try:
        tpl_ok = template.is_dir() and template.resolve() != raiz.resolve()
    except OSError:
        tpl_ok = False
    for rel in FIXOS:
        destino = raiz / rel
        if destino.exists():
            continue
        origem = template / rel
        if tpl_ok and origem.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            if origem.is_dir():
                shutil.copytree(origem, destino)
            else:
                shutil.copy2(origem, destino)
            info(f"copiado do template: {rel.as_posix()}", f"copied from the template: {rel.as_posix()}")
        else:
            aviso(f"Falta {rel.as_posix()} e não achei o template em {template} (use --template ou LODEMAP_TEMPLATE).",
                  f"{rel.as_posix()} is missing and I did not find the template at {template} (use --template or "
                  "LODEMAP_TEMPLATE).")
    return tpl_ok


def _raiz_do_repo(raiz: Path, env: dict) -> Path:
    try:
        r = _rodar(["git", "-C", str(raiz), "rev-parse", "--show-toplevel"], env=env, capturar=True)
        topo = (r.stdout or "").strip()
        if r.returncode == 0 and topo:
            return Path(topo)
    except OSError:
        pass
    return (raiz / ".." / ".." / "..").resolve()


def executar(a: argparse.Namespace, scripts: Path, env_proc=None) -> int:
    """O pipeline. `scripts` é a pasta scripts/ do projeto (a raiz da arquitetura é a pasta acima)."""
    global _EN
    raiz = scripts.parent
    _EN = _idioma_en(raiz, env_proc)
    dsl = raiz / "workspace.dsl"
    template = Path(a.template).expanduser()
    diff = scripts / "lodemap_diff.py"
    py = a.python
    fazer_site = a.com_site and not a.sem_site

    cli = localizar_cli(a.ferramentas, env=env_proc, explicito=a.cli)
    prefixo = comando_cli(cli)
    if shutil.which("java") is None and not os.environ.get("JAVA_HOME"):
        aviso("Não achei o java no PATH nem JAVA_HOME; o Structurizr CLI precisa do Java 17 ou mais novo.",
              "Java is on neither PATH nor JAVA_HOME; the Structurizr CLI needs Java 17 or newer.")

    if a.incremental:
        if _rodar([py, str(diff), "--relevante", "--arq", str(raiz)]).returncode != 0:
            info("Nada mudou desde a última geração; nada a fazer.", "Nothing changed since the last run; nothing to do.")
            return 0

    tpl_ok = _copiar_fixos(raiz, template)
    dot = achar_dot(a.ferramentas)
    env = _env_filho(dot)

    saida = raiz / ".structurizr" / "export"
    saida.mkdir(parents=True, exist_ok=True)

    info("1/7 validando", "1/7 validating the model")
    if _rodar([*prefixo, "validate", "-workspace", str(dsl)], env=env).returncode != 0:
        raise Falha(_t("O modelo não valida. Corrija os .dsl e rode de novo.",
                       "The model does not validate. Fix the .dsl files and run again."))

    info("2/7 exportando JSON", "2/7 exporting JSON")
    if _rodar([*prefixo, "export", "-workspace", str(dsl), "-format", "json", "-output", str(saida)], env=env).returncode != 0:
        raise Falha(_t("Falha ao exportar o JSON.", "Failed to export the JSON."))
    ws = saida / "workspace.json"

    if a.incremental:
        # Depois de exportar: o diff lê o workspace.json, e antes da exportação ele ainda é o do modelo anterior.
        # Medido no axios: com os 3 módulos novos já no DSL, o aviso saía mesmo assim, contra o próprio teste.
        d = _rodar([py, str(diff), "--arq", str(raiz), "--trabalho"], capturar=True)
        try:
            sem = (json.loads(d.stdout or "{}") or {}).get("semComponente") or []
        except ValueError:
            sem = []
        if sem:
            aviso("Módulos sem componente no modelo (o teste de cobertura vai falhar): " + ", ".join(sem),
                  "Modules with no component in the model (the coverage test will fail): " + ", ".join(sem))

    info("3/7 gerando os documentos derivados (02, 90, 91 e o índice de decisões 92)",
         "3/7 generating the derived docs (02, 90, 91 and the decision index 92)")
    if _rodar([py, str(scripts / "gerar_docs.py"), str(ws), str(raiz / "docs")], env=env).returncode != 0:
        raise Falha(_t("Falha ao gerar os documentos.", "Failed to generate the documents."))

    info("4/7 gerando o leitor de documentação (docs e ADRs)", "4/7 generating the docs reader (docs and ADRs)")
    if _rodar([py, str(scripts / "gerar_leitor.py"), str(ws), str(raiz / "leitor")], env=env).returncode != 0:
        raise Falha(_t("Falha ao gerar o leitor.", "Failed to generate the reader."))

    info("5/7 atualizando a prova das relacoes no codigo e gerando os dados do explorador interativo",
         "5/7 refreshing the code proof of each relationship and generating the explorer data")
    ponte = template / ".." / ".." / "scripts" / "codegraph_ponte.py"
    if tpl_ok and ponte.is_file():
        if _rodar([py, str(ponte), "--relacoes", "--arq", str(raiz)], env=env, descartar=True).returncode != 0:
            aviso("A prova das relacoes nao foi atualizada; o explorador usa a anterior, se existir.",
                  "The code proof was not refreshed; the explorer uses the previous one, if any.")
    else:
        info("  sem a ponte do codigo (use --template ou LODEMAP_TEMPLATE): relacoes-codigo.json fica como esta",
             "  code bridge not found (use --template or LODEMAP_TEMPLATE): relacoes-codigo.json is left as is")
    repo = _raiz_do_repo(raiz, env)
    if _rodar([py, str(scripts / "gerar_explorador.py"), str(ws), str(raiz / "explorador"), str(repo)],
              env=env).returncode != 0:
        raise Falha(_t("Falha ao gerar o explorador.", "Failed to generate the explorer."))

    extensoes = [] if a.sem_extensoes else reunir_extensoes(raiz, env=env_proc)
    if extensoes:
        info(f"6/7 rodando {len(extensoes)} extensão(ões) local(is)", f"6/7 running {len(extensoes)} local extension(s)")
        rodar_extensoes(extensoes, py, ws, raiz, repo, a.checkpoint, dot)
    else:
        info("6/7 sem extensões locais", "6/7 no local extensions")

    if fazer_site:
        info("7/7 exportando o site estático", "7/7 exporting the static site")
        if not dot:
            aviso("O Graphviz (dot) não está no PATH nem em <ferramentas>/graphviz; o site estático pode sair incompleto.",
                  "Graphviz (dot) is on neither PATH nor <ferramentas>/graphviz; the static site may come out incomplete.")
        try:
            rc = _rodar([*prefixo, "export", "-workspace", str(dsl), "-format", "static", "-output", str(raiz / "site")],
                        env=env).returncode
        except OSError as e:
            aviso(f"O site estático não rodou: {e}", f"The static site did not run: {e}")
            rc = 0
        if rc != 0:
            aviso("O site estático falhou; o resto está pronto.", "The static site failed; everything else is ready.")
    else:
        info("7/7 site estático fora do padrão (use --com-site)", "7/7 static site skipped (off by default; use --com-site)")

    # Geração verde: marca o commit e o checkpoint para o modo incremental (rótulo por env: acentos intactos).
    marca = _rodar([py, str(diff), "--arq", str(raiz), "--marcar", "--checkpoint-env"], env=_env_filho(dot, a.checkpoint))
    if marca.returncode != 0:
        aviso(r"Não consegui gravar .lodemap/estado.json (o próximo diff será completo).",
              r"Could not write .lodemap/estado.json (the next diff will be a full one).")

    # Linha do tempo da arquitetura (0 tokens): última etapa, nunca obrigatória. Sem o script da skill, segue calada.
    linha = template / ".." / ".." / "scripts" / "linha_do_tempo.py"
    if tpl_ok and linha.is_file():
        info("linha do tempo da arquitetura (histórico git)", "architecture timeline (git history)")
        try:
            rc = _rodar([py, str(linha), "--mapa", str(raiz)], env=env, capturar=True).returncode
        except OSError as e:
            aviso(f"A linha do tempo não rodou: {e}", f"The timeline did not run: {e}")
            rc = 0
        if rc == 3:
            aviso("A linha do tempo não foi gerada: a pasta não está num repositório git.",
                  "The timeline was not generated: the folder is not in a git repository.")
        elif rc != 0:
            aviso(f"A linha do tempo falhou (código {rc}); o resto está pronto.",
                  f"The timeline failed (code {rc}); everything else is ready.")

    info("Pronto. Leitor em leitor/index.html; registre a mudança em docs/99-registro-de-atualizacoes.md.",
         "Done. Reader at leitor/index.html; log the change in docs/99-registro-de-atualizacoes.md.")
    return 0


def main(argv=None, scripts: Path | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure") and not fluxo.isatty():
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    a = parse_args(argv)
    scripts = scripts or Path(__file__).resolve().parent
    try:
        return executar(a, scripts)
    except Falha as e:
        print(f"{_t('ERRO', 'ERROR')}: {e}", file=sys.stderr, flush=True)
        return e.codigo
    except OSError as e:
        print(f"{_t('ERRO', 'ERROR')}: " + _t(f"não consegui rodar um programa: {e}", f"could not run a program: {e}"),
              file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
