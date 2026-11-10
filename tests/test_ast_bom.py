"""Arquivos .py salvos com BOM (comum no Windows) precisam entrar no inventário e nas relações com prova no código."""
from __future__ import annotations

import sys
from collections import defaultdict

from lodemap import RAIZ

sys.path.insert(0, str(RAIZ / "scripts"))
import codegraph_ponte  # noqa: E402
import inventario  # noqa: E402

BOM = "\ufeff"


def _escrever(p, texto, com_bom):
    p.write_bytes(((BOM if com_bom else "") + texto).encode("utf-8"))


def test_inventario_le_docstring_de_arquivo_com_bom(tmp_path):
    for com_bom in (False, True):
        arq = tmp_path / f"m{int(com_bom)}.py"
        _escrever(arq, '"""Calcula o frete por região."""\nx = 1\n', com_bom)
        assert inventario.resumo(arq) == "Calcula o frete por região.", f"bom={com_bom}"


def test_relacao_por_import_aparece_com_e_sem_bom(tmp_path):
    for com_bom in (False, True):
        repo = tmp_path / f"r{int(com_bom)}"
        repo.mkdir()
        _escrever(repo / "a.py", "import b\n", com_bom)
        _escrever(repo / "b.py", "X = 1\n", com_bom)
        saida = defaultdict(lambda: defaultdict(int))
        codegraph_ponte.arestas_ast_python(repo, "a.py", {"a.py", "b.py"}, saida)
        assert saida[("a.py", "b.py")]["imports"] == 1, f"bom={com_bom}"


def test_inventario_ast_lista_simbolos_de_arquivo_com_bom(tmp_path):
    _escrever(tmp_path / "mod.py", "def pagar():\n    return 1\n", True)
    itens = codegraph_ponte.inventario_ast(tmp_path)
    assert any("pagar" in str(i) for i in itens)
