#!/usr/bin/env python3
"""Lodemap: abre a arquitetura do projeto (explorador e leitor em localhost; o Structurizr Lite só com --com-lite).

Equivalente multiplataforma (Windows, Linux e macOS) do ver-arquitetura.ps1: Python 3.10+, só a biblioteca padrão.
O ver-arquitetura.ps1 continua existindo como invólucro fino que chama este arquivo.

O explorador é o visualizador (diagramas, fluxos e inspetor) e o leitor mostra a documentação e as decisões; os dois
são servidos por "python -m http.server --bind 127.0.0.1" na pasta da arquitetura (http://127.0.0.1:8791/explorador/
e /leitor/), num processo destacado que sobrevive a este script. Se a porta já tem a arquitetura no ar, só abre o
navegador; se está ocupada por outro programa, avisa e abre o arquivo local, sem encerrar nada. Se algum .dsl,
documento, ADR ou o script de enriquecimento mudou depois dos dados gerados, roda o atualizar.py antes.

O Structurizr Lite (opcional) usa a pasta de ferramentas (env STRUCTURIZR_FERRAMENTAS, senão ~/.structurizr) com o
structurizr-lite.war ("java -jar") e o Graphviz portátil; o Graphviz entra no PATH só do processo filho. Se o Lite já
estiver no ar com o modelo carregado, só abre o navegador; se estiver no ar com erro, reinicia.

Uso (de qualquer pasta; a raiz é a pasta acima de scripts/):
  python scripts/ver_arquitetura.py
  python scripts/ver_arquitetura.py --abrir leitor
  python scripts/ver_arquitetura.py --com-lite --ferramentas ~/.structurizr

Mapeamento dos parâmetros do ver-arquitetura.ps1 para as flags:

  -Abrir Explorador|Leitor|Lite|Ambos   --abrir explorador|leitor|lite|ambos   (padrão: explorador)
  -ComLite                              --com-lite
  -Porta <n>                            --porta <n>               (Lite; padrão: campo "lite" do lodemap.json, 8790)
  -PortaExplorador <n>                  --porta-explorador <n>    (campo "explorador" do lodemap.json, 8791)
  -Ferramentas <pasta>                  --ferramentas <pasta>     env STRUCTURIZR_FERRAMENTAS, senão ~/.structurizr
  -Python <exe>                         --python <exe>            env LODEMAP_PYTHON, senão o Python que roda este script
  -SemNavegador                         --sem-navegador

Código de saída: 0 em caso normal; 1 se o Lite foi pedido e não subiu (sem o .war, sem o java ou sem carregar o modelo).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Todo texto que o usuário lê está aqui (um lugar só para traduzir). Os marcadores {x} são preenchidos por _dizer.
MSG = {
    "atualizar_falhou": "Não consegui atualizar os dados gerados ({motivo}). Abrindo a versão anterior.",
    "porta_ocupada": "A porta {porta} está ocupada por outro programa; abrindo como arquivo local.",
    "servidor_mudo": "O servidor não respondeu; abrindo o arquivo local.",
    "servidor_nao_subiu": "Não consegui iniciar o servidor ({motivo}); abrindo o arquivo local.",
    "so_explorador": "Explorador em {exp}/explorador/ e documentação em {exp}/leitor/",
    "sem_war": "Não achei {war}. Baixe o structurizr-lite.war em {ferramentas}.",
    "sem_java": "Não achei o java no PATH nem JAVA_HOME; o Structurizr Lite precisa do Java 17 ou mais novo.",
    "sem_graphviz": "Graphviz não encontrado: o autolayout não vai funcionar.",
    "lite_falhou": "O Lite não carregou o workspace em {url}. Veja {log} e {log}.err.",
    "lite_nao_subiu": "Não consegui iniciar o Lite ({motivo}).",
    "tudo": "Arquitetura em {exp}/explorador/ (explorador), {exp}/leitor/ (documentação) e {url} (Lite)",
}
PORTA_LITE = 8790
PORTA_EXPLORADOR = 8791
IGNORADAS = {"site", "explorador", "leitor", ".structurizr", ".lodemap", "__pycache__"}
EXTENSOES_FONTE = {".dsl", ".groovy", ".md", ".json", ".py"}
# Processos destacados que este módulo iniciou (os testes os encerram; no uso normal ficam no ar de propósito).
PROCESSOS: list[subprocess.Popen] = []


def _windows() -> bool:
    return os.name == "nt"


def _dizer(chave: str, **kw) -> str:
    return MSG[chave].format(**kw)


def info(chave: str, **kw) -> None:
    print(_dizer(chave, **kw), flush=True)


def aviso(chave: str, **kw) -> None:
    print("AVISO: " + _dizer(chave, **kw), file=sys.stderr, flush=True)


def erro(chave: str, **kw) -> None:
    print("ERRO: " + _dizer(chave, **kw), file=sys.stderr, flush=True)


# --------------------------------------------------------------------------------------------- argumentos

def parse_args(argv=None, env=None) -> argparse.Namespace:
    env = os.environ if env is None else env
    ferr = env.get("STRUCTURIZR_FERRAMENTAS") or str(Path.home() / ".structurizr")
    ap = argparse.ArgumentParser(prog="ver_arquitetura.py", description=__doc__.splitlines()[0])
    ap.add_argument("--abrir", type=str.lower, choices=["explorador", "leitor", "lite", "ambos"], default="explorador",
                    help="o que abrir (ambos = explorador e Lite; o mesmo que --com-lite)")
    ap.add_argument("--com-lite", action="store_true", help="sobe e abre também o Structurizr Lite")
    ap.add_argument("--porta", type=int, default=0, help="porta do Lite (padrão: a do lodemap.json, senão 8790)")
    ap.add_argument("--porta-explorador", type=int, default=0,
                    help="porta do servidor do explorador e do leitor (padrão: a do lodemap.json, senão 8791)")
    ap.add_argument("--sem-navegador", action="store_true", help="sobe os servidores e não abre o navegador")
    ap.add_argument("--ferramentas", default=ferr, help="pasta com structurizr-lite.war e graphviz/ (padrão: %(default)s)")
    ap.add_argument("--python", default=env.get("LODEMAP_PYTHON") or sys.executable,
                    help="executável do Python do servidor e do atualizar.py (padrão: %(default)s)")
    return ap.parse_args(argv)


def porta_do_config(raiz: Path, campo: str, padrao: int) -> int:
    """Porta gravada em lodemap.json (campo "lite" ou "explorador", ex.: "http://localhost:8790"); `padrao` se faltar."""
    try:
        cfg = json.loads((raiz / "lodemap.json").read_text(encoding="utf-8-sig"))
        m = re.search(r":(\d+)", str(cfg.get(campo, "")))
        if m:
            return int(m.group(1))
    except (OSError, ValueError, AttributeError):
        pass
    return padrao


# ------------------------------------------------------------------------------------- dados gerados atrasados

def fontes_do_workspace(raiz: Path):
    """Arquivos que alimentam os dados gerados (modelo, documentos, ADRs, enriquecimento), sem as pastas geradas."""
    for pasta, subs, nomes in os.walk(raiz):
        subs[:] = [s for s in subs if s not in IGNORADAS]
        for n in nomes:
            if Path(n).suffix in EXTENSOES_FONTE and n != "workspace.json":
                yield Path(pasta) / n


def dados_atrasados(raiz: Path) -> bool:
    """True se explorador/dados.js ou leitor/dados.js faltam ou são mais velhos que a fonte mais nova."""
    gerados = [raiz / "explorador" / "dados.js", raiz / "leitor" / "dados.js"]
    if any(not g.is_file() for g in gerados):
        return True
    tempos = []
    for f in fontes_do_workspace(raiz):
        try:
            tempos.append(f.stat().st_mtime)
        except OSError:
            pass
    mais_nova = max(tempos, default=0.0)
    return any(g.stat().st_mtime < mais_nova for g in gerados)


def atualizar_dados(raiz: Path, scripts: Path, python: str, ferramentas: str) -> None:
    try:
        r = subprocess.run([python, str(scripts / "atualizar.py"), "--ferramentas", ferramentas, "--python", python],
                           cwd=str(raiz))
        if r.returncode != 0:
            aviso("atualizar_falhou", motivo=f"código {r.returncode}")
    except OSError as e:
        aviso("atualizar_falhou", motivo=str(e))


# ------------------------------------------------------------------------------------------------------- rede

def _abrir_http(url: str, timeout: float):
    """GET sem proxy (127.0.0.1 nunca deve passar por proxy corporativo). Devolve (status, texto)."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=timeout) as r:
        return r.status, r.read(2_000_000).decode("utf-8", errors="replace")


def tem_arquitetura(url_exp: str) -> bool:
    """As duas páginas carregam o seu dados.js; outro programa na porta não responde com isso."""
    for pagina in ("leitor", "explorador"):
        try:
            status, corpo = _abrir_http(f"{url_exp}/{pagina}/index.html", 2)
            if status == 200 and "dados.js" in corpo:
                return True
        except Exception:
            continue
    return False


def porta_ocupada(porta: int) -> bool:
    """True se alguém aceita conexões em 127.0.0.1:porta."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def decidir_servidor(porta: int) -> str:
    """'no_ar' (a arquitetura já responde), 'ocupada' (outro programa na porta) ou 'subir' (porta livre)."""
    if not porta_ocupada(porta):
        return "subir"
    return "no_ar" if tem_arquitetura(f"http://127.0.0.1:{porta}") else "ocupada"


def _destacado(cmd: list[str], saida: Path, cwd: str | None = None, env: dict | None = None) -> subprocess.Popen:
    """Inicia `cmd` desligado deste processo (sem console, em outro grupo/sessão), com a saída em saida e saida.err."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    extra: dict = {}
    if _windows():
        extra["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        extra["start_new_session"] = True
    with open(saida, "ab") as out, open(str(saida) + ".err", "ab") as err:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                             close_fds=True, **extra)
    PROCESSOS.append(p)
    return p


def subir_servidor(python: str, porta: int, raiz: Path) -> subprocess.Popen:
    return _destacado([python, "-m", "http.server", str(porta), "--bind", "127.0.0.1", "--directory", str(raiz)],
                      raiz / ".lodemap" / "explorador-http.log")


def abrir_url(alvo: str, sem_navegador: bool) -> None:
    if not sem_navegador:
        webbrowser.open(alvo)


# ------------------------------------------------------------------------------------ explorador e leitor (http)

def servir_explorador(a: argparse.Namespace, raiz: Path, porta_exp: int, pagina: str) -> None:
    url_exp = f"http://127.0.0.1:{porta_exp}"
    arquivo_local = (raiz / pagina).as_uri()
    alvo = f"{url_exp}/{pagina}"
    estado = decidir_servidor(porta_exp)
    if estado == "ocupada":
        aviso("porta_ocupada", porta=porta_exp)
        alvo = arquivo_local
    elif estado == "subir":
        try:
            subir_servidor(a.python, porta_exp, raiz)
            for _ in range(20):
                if tem_arquitetura(url_exp):
                    break
                time.sleep(0.5)
            else:
                aviso("servidor_mudo")
                alvo = arquivo_local
        except OSError as e:
            aviso("servidor_nao_subiu", motivo=str(e))
            alvo = arquivo_local
    abrir_url(alvo, a.sem_navegador)


# ----------------------------------------------------------------------------- Structurizr Lite (opcional)

def lite_responde(url: str) -> bool:
    try:
        return _abrir_http(url, 2)[0] == 200
    except Exception:
        return False


def lite_com_workspace(url: str) -> bool:
    """O Lite devolve 200 até na página de erro; o que vale é o conteúdo."""
    try:
        status, corpo = _abrir_http(url, 5)
    except Exception:
        return False
    return status == 200 and not re.search(r"does not exist|<h1[^>]*>\s*Error", corpo)


def _pids_lite(porta: int) -> list[int]:
    """PIDs do java do Structurizr Lite. POSIX: `ps` com structurizr-lite na linha de comando. Windows: o dono da porta,
    se for java (sem PowerShell nem wmic)."""
    pids: list[int] = []
    try:
        if _windows():
            r = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True)
            for linha in r.stdout.splitlines():
                c = linha.split()
                # escuta = endereço remoto ":0" (a palavra do estado muda com o idioma do Windows)
                if len(c) >= 5 and c[2].endswith(":0") and c[1].endswith(f":{porta}") and c[4].isdigit():
                    t = subprocess.run(["tasklist", "/FI", f"PID eq {c[4]}", "/FO", "CSV", "/NH"],
                                       capture_output=True, text=True)
                    if t.stdout.lower().lstrip('"').startswith("java"):
                        pids.append(int(c[4]))
        else:
            r = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True)
            for linha in r.stdout.splitlines():
                p, _, args = linha.strip().partition(" ")
                if p.isdigit() and "structurizr-lite" in args and "java" in args and int(p) != os.getpid():
                    pids.append(int(p))
    except OSError:
        pass
    return pids


def parar_lite(porta: int) -> None:
    for pid in _pids_lite(porta):
        try:
            if _windows():
                subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True)
            else:
                os.kill(pid, 15)
        except OSError:
            pass
    time.sleep(2)


def achar_dot(ferramentas: Path) -> Path | None:
    nome = "dot.exe" if _windows() else "dot"
    pasta = ferramentas / "graphviz"
    if pasta.is_dir():
        for f in sorted(pasta.rglob(nome)):
            if f.is_file():
                return f
    return None


def env_do_lite(raiz: Path, dot: Path | None, base: dict | None = None) -> dict:
    env = dict(os.environ if base is None else base)
    if dot:
        env["PATH"] = str(dot.parent) + os.pathsep + env.get("PATH", "")
    elif shutil.which("dot", path=env.get("PATH")) is None:
        aviso("sem_graphviz")
    if _windows():
        # O Lite junta o caminho à pasta padrão dele (<unidade>:\usr\local\structurizr), então um caminho absoluto com
        # letra de unidade quebra. Passamos o caminho relativo a essa pasta, com a unidade do workspace como atual.
        unidade = raiz.drive
        env["STRUCTURIZR_WORKSPACE_PATH"] = "..\\..\\.." + str(raiz)[len(unidade):]
    else:
        env["STRUCTURIZR_WORKSPACE_PATH"] = str(raiz)
    return env


def subir_lite(a: argparse.Namespace, raiz: Path, porta: int, sonda: str, url: str) -> bool:
    ferramentas = Path(a.ferramentas).expanduser()
    war = ferramentas / "structurizr-lite.war"
    if not war.is_file():
        erro("sem_war", war=war, ferramentas=ferramentas)
        return False
    if shutil.which("java") is None and not os.environ.get("JAVA_HOME"):
        erro("sem_java")
        return False
    env = env_do_lite(raiz, achar_dot(ferramentas))
    log = ferramentas / "lite.log"
    try:
        _destacado(["java", f"-Dserver.port={porta}", "-jar", str(war)], log, cwd=raiz.anchor or None, env=env)
    except OSError as e:
        erro("lite_nao_subiu", motivo=str(e))
        return False
    for _ in range(60):
        if lite_com_workspace(sonda):
            return True
        time.sleep(1)
    erro("lite_falhou", url=url, log=log)
    return False


def servir_lite(a: argparse.Namespace, raiz: Path, porta: int, url_exp: str) -> int:
    url = f"http://localhost:{porta}"  # o que o navegador abre
    sonda = f"http://127.0.0.1:{porta}"  # o que este script consulta (localhost tenta o IPv6 antes e demora no Windows)
    # Instância antiga com o workspace errado (ou sem o modelo): derruba e sobe de novo.
    if lite_responde(sonda) and not lite_com_workspace(sonda):
        parar_lite(porta)
    if not lite_responde(sonda) and not subir_lite(a, raiz, porta, sonda, url):
        return 1
    info("tudo", exp=url_exp, url=url)
    abrir_url(f"{url}/workspace/diagrams", a.sem_navegador)
    return 0


# ----------------------------------------------------------------------------------------------------- principal

def executar(a: argparse.Namespace, scripts: Path) -> int:
    """`scripts` é a pasta scripts/ do projeto (a raiz da arquitetura é a pasta acima)."""
    raiz = scripts.parent
    quer_lite = a.com_lite or a.abrir in ("lite", "ambos")
    porta_lite = a.porta or porta_do_config(raiz, "lite", PORTA_LITE)
    porta_exp = a.porta_explorador or porta_do_config(raiz, "explorador", PORTA_EXPLORADOR)
    url_exp = f"http://127.0.0.1:{porta_exp}"

    if dados_atrasados(raiz):
        atualizar_dados(raiz, scripts, a.python, a.ferramentas)
    if a.abrir != "lite":
        servir_explorador(a, raiz, porta_exp, "leitor/index.html" if a.abrir == "leitor" else "explorador/index.html")
    if not quer_lite:
        info("so_explorador", exp=url_exp)
        return 0
    return servir_lite(a, raiz, porta_lite, url_exp)


def main(argv=None, scripts: Path | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure") and not fluxo.isatty():
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    a = parse_args(argv)
    return executar(a, scripts or Path(__file__).resolve().parent)


if __name__ == "__main__":
    sys.exit(main())
