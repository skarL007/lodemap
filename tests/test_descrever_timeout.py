"""Limites de chamadas usando somente processos Python locais, sem modelos ou rede."""
from __future__ import annotations

import os
import ctypes
from ctypes import wintypes
import json
import re
import subprocess
import sys
import time

import pytest

from lodemap import RAIZ

sys.path.insert(0, str(RAIZ / "scripts"))
import descrever  # noqa: E402
from test_descrever import _preparar, projeto  # noqa: E402,F401


@pytest.mark.skipif(os.name != "nt", reason="regressão de communicate no Windows")
def test_timeout_nao_espera_descendente_fechar_pipes(tmp_path):
    filho = tmp_path / "filho.py"
    filho.write_text("import time\ntime.sleep(3)\n", encoding="utf-8")
    pid_filho = tmp_path / "filho.pid"
    pai = (
        "import subprocess, sys, time; "
        "p = subprocess.Popen([sys.executable, sys.argv[1]]); "
        "open(sys.argv[2], 'w').write(str(p.pid)); time.sleep(10)"
    )
    # Outro Python não pertence à árvore da chamada e deve continuar vivo.
    independente = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    try:
        inicio = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired):
            descrever.chamar([sys.executable, "-c", pai, str(filho), str(pid_filho)], "", tmp_path, limite_s=0.3)
        assert time.monotonic() - inicio < 2, "timeout aguardou o descendente fechar stdout/stderr"
        assert independente.poll() is None, "encerramento atingiu processo fora da árvore"
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, int(pid_filho.read_text()))
        if handle:
            try:
                assert kernel.WaitForSingleObject(handle, 0) == 0, "descendente permaneceu vivo após timeout"
            finally:
                kernel.CloseHandle(handle)
        else:
            assert ctypes.get_last_error() == 87, "PID encerrado deve deixar de existir"
    finally:
        independente.kill()
        independente.wait(timeout=5)


@pytest.mark.skipif(os.name != "nt", reason="regressão da escrita síncrona de stdin no Windows")
def test_timeout_inclui_entrada_que_processo_nao_le(tmp_path):
    inicio = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        descrever.chamar(
            [sys.executable, "-c", "import time; time.sleep(3)"], "x" * 1_000_000,
            tmp_path, limite_s=0.3,
        )
    assert time.monotonic() - inicio < 2, "escrita bloqueada em stdin ultrapassou o timeout"


@pytest.mark.parametrize("falha_limpeza", [False, True])
def test_timeout_de_um_lote_nao_e_reenviado_quando_outros_passam(projeto, tmp_path, monkeypatch, falha_limpeza):
    arq, _ = _preparar(projeto, tmp_path, monkeypatch)
    chamar_local = descrever.chamar
    indices = []

    def chamar(cmd, texto, cwd):
        indice = int(re.search(r"### i=(\d+)", texto).group(1))
        indices.append(indice)
        if indice == 0:
            try:
                raise subprocess.TimeoutExpired(cmd, 900)
            except subprocess.TimeoutExpired as e:
                if falha_limpeza:
                    raise RuntimeError("claude -p excedeu 900 s; falha no encerramento dos descendentes") from e
                raise
        return chamar_local(cmd, texto, cwd)

    monkeypatch.setattr(descrever, "chamar", chamar)
    rel = descrever.descrever(arq, projeto, lote=1, conferir_com=None)
    assert indices == [0, 1, 2], "falha do CLI não deve consumir outro limite de 900 s"
    assert rel["reenviados"] == 0 and rel["descritos"] == 2
    assert "900" in rel["para_modelador"][0]["motivo"]
    assert "900" in rel["chamadas"][0]["erro"]
    assert "seg" in rel["chamadas"][0]


@pytest.mark.parametrize("erro", [RuntimeError("falha transitória"),
                                 json.JSONDecodeError("JSON incompleto", "{", 1),
                                 OSError("falha transitória de execução")], ids=["runtime", "json", "oserror"])
def test_falha_transitoria_de_um_lote_e_reenviada_quando_outros_passam(projeto, tmp_path, monkeypatch, erro):
    arq, _ = _preparar(projeto, tmp_path, monkeypatch)
    chamar_local = descrever.chamar
    indices = []

    def chamar(cmd, texto, cwd):
        indice = int(re.search(r"### i=(\d+)", texto).group(1))
        indices.append(indice)
        if len(indices) == 1:
            raise erro
        return chamar_local(cmd, texto, cwd)

    monkeypatch.setattr(descrever, "chamar", chamar)
    rel = descrever.descrever(arq, projeto, lote=1, conferir_com=None)
    assert indices == [0, 1, 2, 0], "falha transitória mantém o reenvio quando outro lote teve sucesso"
    assert rel["reenviados"] == 1 and rel["descritos"] == 3 and rel["para_modelador"] == []


def test_conferencia_registra_timeout_legivel_sem_comando_truncado(monkeypatch):
    def chamar(cmd, texto, cwd):
        raise subprocess.TimeoutExpired(cmd, 900)

    monkeypatch.setattr(descrever, "chamar", chamar)
    vereditos, chamadas = descrever.conferir([(0, "modulo.py", "Frase", "codigo")], "pt", "haiku")
    assert vereditos == {}
    assert "900" in chamadas[0]["erro"]
    assert "seg" in chamadas[0]
    assert "--json-schema" not in chamadas[0]["erro"]


@pytest.mark.skipif(os.name != "nt", reason="fallback de taskkill do Windows")
def test_falha_de_taskkill_mata_pai_e_informa_limite_da_limpeza(tmp_path, monkeypatch):
    def taskkill(cmd, **kwargs):
        assert cmd[0] == "taskkill" and "/PID" in cmd and "/IM" not in cmd
        assert kwargs["timeout"] == 5
        raise subprocess.TimeoutExpired(cmd, 5)

    monkeypatch.setattr(descrever.subprocess, "run", taskkill)
    inicio = time.monotonic()
    with pytest.raises(RuntimeError, match="excedeu 0.3 s;.*descendentes") as erro:
        descrever.chamar([sys.executable, "-c", "import time; time.sleep(3)"], "", tmp_path, limite_s=0.3)
    assert isinstance(erro.value.__cause__, subprocess.TimeoutExpired)
    assert time.monotonic() - inicio < 2
