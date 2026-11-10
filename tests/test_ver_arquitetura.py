"""ver_arquitetura.py: argumentos, portas do lodemap.json, dados atrasados, decisão de porta e o servidor de verdade."""
from __future__ import annotations

import contextlib
import importlib.util
import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from lodemap import RAIZ

ARQUIVO = RAIZ / "templates" / "structurizr" / "scripts" / "ver_arquitetura.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("lodemap_ver_arquitetura", ARQUIVO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


va = _carregar()


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def outro_programa():
    """Um programa qualquer escutando numa porta: aceita a conexão e fecha, sem falar HTTP. Entrega a porta."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    parar = threading.Event()

    def servir():
        srv.settimeout(0.2)
        while not parar.is_set():
            try:
                c, _ = srv.accept()
                c.close()
            except OSError:
                pass

    t = threading.Thread(target=servir, daemon=True)
    t.start()
    try:
        yield srv.getsockname()[1]
    finally:
        parar.set()
        t.join(timeout=2)
        srv.close()


def _get(url: str):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=5) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


@pytest.fixture(autouse=True)
def encerrar_servidores():
    """Os servidores são destacados de propósito; o teste não pode deixar nenhum no ar."""
    yield
    for p in va.PROCESSOS:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=10)
            except Exception:
                p.kill()
    va.PROCESSOS.clear()


def _arq(tmp_path: Path, config: str | None = None) -> Path:
    """Arquitetura mínima e em dia: fontes mais velhas que os dados.js (nada a regenerar)."""
    arq = tmp_path / "arq"
    (arq / "scripts").mkdir(parents=True)
    (arq / "explorador").mkdir()
    (arq / "leitor").mkdir()
    (arq / "workspace.dsl").write_text("workspace {}\n", encoding="utf-8")
    if config is not None:
        (arq / "lodemap.json").write_text(config, encoding="utf-8")
    for pasta in ("explorador", "leitor"):
        (arq / pasta / "index.html").write_text('<html><script src="dados.js"></script></html>', encoding="utf-8")
        (arq / pasta / "dados.js").write_text("window.DADOS = {};\n", encoding="utf-8")
    antigo = time.time() - 100
    for f in (arq / "workspace.dsl", arq / "lodemap.json"):
        if f.exists():
            os.utime(f, (antigo, antigo))
    return arq


def _args(*extra: str):
    return va.parse_args(["--python", sys.executable, "--sem-navegador", *extra], env={})


# ------------------------------------------------------------------------------------------------ argumentos

def test_argumentos_padrao_e_ambiente(tmp_path):
    a = va.parse_args([], env={})
    assert a.abrir == "explorador" and not a.com_lite and not a.sem_navegador
    assert a.porta == 0 and a.porta_explorador == 0
    assert a.ferramentas == str(Path.home() / ".structurizr") and a.python == sys.executable
    a = va.parse_args([], env={"STRUCTURIZR_FERRAMENTAS": str(tmp_path), "LODEMAP_PYTHON": "py3"})
    assert (a.ferramentas, a.python) == (str(tmp_path), "py3")


def test_flags_espelham_os_parametros_do_ps1_e_abrir_aceita_qualquer_caixa():
    a = va.parse_args(["--abrir", "Leitor", "--com-lite", "--porta", "1", "--porta-explorador", "2", "--sem-navegador",
                       "--ferramentas", "F", "--python", "P"], env={})
    assert (a.abrir, a.com_lite, a.porta, a.porta_explorador, a.sem_navegador, a.ferramentas, a.python) == (
        "leitor", True, 1, 2, True, "F", "P")
    for v in ("explorador", "leitor", "lite", "ambos"):
        assert va.parse_args(["--abrir", v.upper()], env={}).abrir == v


def test_abrir_invalido_sai_com_codigo_2(capsys):
    with pytest.raises(SystemExit) as e:
        va.parse_args(["--abrir", "xyz"], env={})
    assert e.value.code == 2


# ----------------------------------------------------------------------------------------- portas do config

def test_porta_do_config_le_lodemap_json_inclusive_com_bom(tmp_path):
    arq = _arq(tmp_path)
    (arq / "lodemap.json").write_bytes(b'\xef\xbb\xbf{"lite": "http://localhost:9001", "explorador": "http://127.0.0.1:9002/x"}')
    assert va.porta_do_config(arq, "lite", 8790) == 9001
    assert va.porta_do_config(arq, "explorador", 8791) == 9002


@pytest.mark.parametrize("conteudo", [None, "{quebrado", '{"lite": "sem porta"}', "[]"])
def test_porta_do_config_cai_no_padrao(tmp_path, conteudo):
    arq = _arq(tmp_path, conteudo)
    assert va.porta_do_config(arq, "lite", 8790) == 8790


# ------------------------------------------------------------------------------------------ dados atrasados

def test_dados_em_dia_nao_regeneram(tmp_path):
    assert va.dados_atrasados(_arq(tmp_path)) is False


def test_dados_faltando_ou_mais_velhos_que_a_fonte_regeneram(tmp_path):
    arq = _arq(tmp_path)
    futuro = time.time() + 50
    os.utime(arq / "workspace.dsl", (futuro, futuro))
    assert va.dados_atrasados(arq) is True
    arq2 = _arq(tmp_path / "b")
    (arq2 / "leitor" / "dados.js").unlink()
    assert va.dados_atrasados(arq2) is True


def test_pastas_geradas_e_workspace_json_nao_contam_como_fonte(tmp_path):
    arq = _arq(tmp_path)
    futuro = time.time() + 50
    for rel in ("workspace.json", "site/x.md", ".lodemap/estado.json", "explorador/notas.md", "leitor/x.json",
                ".structurizr/a.json", "scripts/__pycache__/m.py"):
        f = arq / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x", encoding="utf-8")
        os.utime(f, (futuro, futuro))
    assert va.dados_atrasados(arq) is False
    doc = arq / "docs" / "01.md"
    doc.parent.mkdir()
    doc.write_text("x", encoding="utf-8")
    os.utime(doc, (futuro, futuro))
    assert va.dados_atrasados(arq) is True


def test_atualizar_dados_chama_o_atualizar_py_com_ferramentas_e_python(tmp_path):
    arq = _arq(tmp_path)
    marca = tmp_path / "argv.txt"
    (arq / "scripts" / "atualizar.py").write_text(
        f"import sys, pathlib\npathlib.Path({str(marca)!r}).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')\n",
        encoding="utf-8")
    va.atualizar_dados(arq, arq / "scripts", sys.executable, "/ferr")
    assert marca.read_text(encoding="utf-8").splitlines() == ["--ferramentas", "/ferr", "--python", sys.executable]


def test_atualizar_que_falha_so_avisa(tmp_path, capsys):
    arq = _arq(tmp_path)
    (arq / "scripts" / "atualizar.py").write_text("raise SystemExit(5)\n", encoding="utf-8")
    va.atualizar_dados(arq, arq / "scripts", sys.executable, "/ferr")
    assert "código 5" in capsys.readouterr().err


# ---------------------------------------------------------------------------------------- decisão de porta

def test_decidir_servidor_livre_ocupada_e_no_ar(tmp_path):
    livre = porta_livre()
    assert va.decidir_servidor(livre) == "subir"
    with outro_programa() as ocupada:  # outro programa qualquer escutando, que não é a arquitetura
        assert va.decidir_servidor(ocupada) == "ocupada"
    arq = _arq(tmp_path)
    va.subir_servidor(sys.executable, livre, arq)
    for _ in range(40):
        if va.decidir_servidor(livre) == "no_ar":
            break
        time.sleep(0.25)
    assert va.decidir_servidor(livre) == "no_ar"


# ------------------------------------------------------------------------------------ servidor de verdade

def test_executar_sobe_o_servidor_e_serve_o_explorador_sem_abrir_navegador(tmp_path, monkeypatch, capsys):
    arq = _arq(tmp_path)
    abertos = []
    monkeypatch.setattr(va.webbrowser, "open", lambda alvo: abertos.append(alvo))
    porta = porta_livre()
    assert va.executar(_args("--porta-explorador", str(porta)), arq / "scripts") == 0
    status, corpo = _get(f"http://127.0.0.1:{porta}/explorador/")
    assert status == 200 and "dados.js" in corpo
    assert _get(f"http://127.0.0.1:{porta}/leitor/")[0] == 200
    assert abertos == [], "--sem-navegador não abre nada"
    assert f"127.0.0.1:{porta}/explorador/" in capsys.readouterr().out
    assert (arq / ".lodemap" / "explorador-http.log").exists()


def test_segunda_chamada_reaproveita_o_servidor_e_abre_so_o_navegador(tmp_path, monkeypatch):
    arq = _arq(tmp_path)
    abertos = []
    monkeypatch.setattr(va.webbrowser, "open", lambda alvo: abertos.append(alvo))
    porta = porta_livre()
    args = ["--porta-explorador", str(porta)]
    va.executar(_args(*args), arq / "scripts")
    assert len(va.PROCESSOS) == 1
    a = va.parse_args(["--python", sys.executable, "--abrir", "leitor", *args], env={})
    assert va.executar(a, arq / "scripts") == 0
    assert len(va.PROCESSOS) == 1, "a arquitetura já estava no ar: não sobe outro servidor"
    assert abertos == [f"http://127.0.0.1:{porta}/leitor/index.html"]


def test_porta_ocupada_por_outro_programa_avisa_e_abre_o_arquivo_local(tmp_path, monkeypatch, capsys):
    arq = _arq(tmp_path)
    abertos = []
    monkeypatch.setattr(va.webbrowser, "open", lambda alvo: abertos.append(alvo))
    with outro_programa() as porta:
        a = va.parse_args(["--python", sys.executable, "--porta-explorador", str(porta)], env={})
        assert va.executar(a, arq / "scripts") == 0
    assert va.PROCESSOS == [], "nada é encerrado nem iniciado quando a porta é de outro programa"
    assert abertos == [(arq / "explorador" / "index.html").as_uri()]
    assert f"A porta {porta} está ocupada" in capsys.readouterr().err


def test_porta_do_explorador_vem_do_lodemap_json(tmp_path, monkeypatch):
    porta = porta_livre()
    arq = _arq(tmp_path, f'{{"explorador": "http://127.0.0.1:{porta}"}}')
    monkeypatch.setattr(va.webbrowser, "open", lambda alvo: None)
    assert va.executar(_args(), arq / "scripts") == 0
    assert _get(f"http://127.0.0.1:{porta}/explorador/index.html")[0] == 200


# ------------------------------------------------------------------------------------------ Structurizr Lite

def test_lite_sem_o_war_sai_com_1_e_explica(tmp_path, capsys):
    arq = _arq(tmp_path)
    ferr = tmp_path / "ferr"
    ferr.mkdir()
    a = va.parse_args(["--python", sys.executable, "--sem-navegador", "--abrir", "lite", "--porta", str(porta_livre()),
                       "--ferramentas", str(ferr)], env={})
    assert va.executar(a, arq / "scripts") == 1
    assert "structurizr-lite.war" in capsys.readouterr().err
    assert va.PROCESSOS == []


def test_achar_dot_e_path_do_processo_filho(tmp_path, monkeypatch):
    ferr = tmp_path / "ferr"
    nome = "dot.exe" if os.name == "nt" else "dot"
    (ferr / "graphviz" / "bin").mkdir(parents=True)
    dot = ferr / "graphviz" / "bin" / nome
    dot.write_text("", encoding="utf-8")
    assert va.achar_dot(ferr) == dot
    assert va.achar_dot(tmp_path / "vazio") is None
    arq = _arq(tmp_path)
    env = va.env_do_lite(arq, dot, base={"PATH": "/x"})
    assert env["PATH"].split(os.pathsep)[0] == str(dot.parent) and env["PATH"].endswith("/x")
    if os.name == "nt":  # o Lite junta o caminho à pasta padrão dele: relativo, sem a letra da unidade
        assert env["STRUCTURIZR_WORKSPACE_PATH"] == "..\\..\\.." + str(arq)[len(arq.drive):]
    else:
        assert env["STRUCTURIZR_WORKSPACE_PATH"] == str(arq)
    assert "STRUCTURIZR_WORKSPACE_PATH" not in os.environ or os.environ["STRUCTURIZR_WORKSPACE_PATH"] != env["STRUCTURIZR_WORKSPACE_PATH"]


def test_graphviz_ausente_avisa(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(va.shutil, "which", lambda *a, **k: None)
    va.env_do_lite(_arq(tmp_path), None, base={"PATH": ""})
    assert "Graphviz não encontrado" in capsys.readouterr().err


def test_lite_com_workspace_distingue_pagina_de_erro(tmp_path, monkeypatch):
    respostas = {"ok": (200, "<html>Diagrams</html>"), "erro": (200, "<h1 class='x'>Error</h1>"),
                 "vazio": (200, "Workspace does not exist"), "500": (500, "x")}
    atual = {}
    monkeypatch.setattr(va, "_abrir_http", lambda url, t: respostas[atual["k"]])
    esperado = {"ok": True, "erro": False, "vazio": False, "500": False}
    for k, v in esperado.items():
        atual["k"] = k
        assert va.lite_com_workspace("http://localhost:1") is v, k
