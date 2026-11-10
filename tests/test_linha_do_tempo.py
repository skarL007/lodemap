"""scripts/linha_do_tempo.py: a linha do tempo da arquitetura, lida do histórico git do mapa (0 tokens).

Cada teste monta um repositório git sintético no tmp com três versões do mapa. Cada versão grava o `explorador/dados.js`
no formato do `gerar_explorador.py` (`window.ARQ = {...};`) e uma linha nova no registro de atualizações. As três
versões cobrem, uma a uma, as categorias do diff:

  v1  criação do mapa (tudo entra)
  v2  componente adicionado, descrição alterada, status alterado, relação nova, fluxo alterado (passo novo)
  v3  componente removido, container alterado, tecnologia alterada, relação nova e removida, fluxo adicionado,
      removido e alterado

Os ids numéricos do Structurizr mudam de uma versão para a outra (o v2 insere um componente no começo da lista, o v3
tira um do meio): o diff tem de seguir o identificador do DSL, nunca o id.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lodemap import RAIZ

SCRIPT = RAIZ / "scripts" / "linha_do_tempo.py"
ATUALIZAR = RAIZ / "templates" / "structurizr" / "scripts" / "atualizar.py"
PASTA = Path("docs") / "arq"


def lt():
    """Carrega o script na hora do uso: sem ele, cada teste cai aqui, com o motivo à vista."""
    spec = importlib.util.spec_from_file_location("lodemap_linha_do_tempo", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------------------------ repositório sintético

def _env(data: str | None = None) -> dict:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_NOSYSTEM="1", PYTHONIOENCODING="utf-8",
               LODEMAP_IDIOMA="pt")
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    if data:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = data
    return env


def git(repo: Path, *args: str, data: str | None = None) -> str:
    r = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "core.autocrlf=false",
                        "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", env=_env(data))
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


def commit(repo: Path, assunto: str, data: str, tag: str | None = None) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", assunto, data=data)
    if tag:
        git(repo, "tag", tag)
    return git(repo, "rev-parse", "HEAD")


def E(ident, nome, tipo="Componente", pai=None, desc="", tech="", status="Pronto", area="AreaA", codigo=""):
    return dict(ident=ident, nome=nome, tipo=tipo, pai=pai, desc=desc, tech=tech, status=status, area=area, codigo=codigo)


def escrever_mapa(repo: Path, elementos, relacoes, fluxos, registro: list[str], idioma="pt", nome="Lib",
                  com_dados=True) -> Path:
    """Grava o mapa em repo/docs/arq no formato do gerar_explorador.py. Os ids são sequenciais pela ordem da lista."""
    mapa = repo / PASTA
    (mapa / "explorador").mkdir(parents=True, exist_ok=True)
    (mapa / "docs").mkdir(parents=True, exist_ok=True)
    (mapa / "lodemap.json").write_text(json.dumps({"idioma": idioma}), encoding="utf-8")
    cab = "# Registro de atualizações\n\n| Data | O que mudou | Motivo |\n|---|---|---|\n"
    (mapa / "docs" / "99-registro-de-atualizacoes.md").write_text(cab + "\n".join(registro) + "\n", encoding="utf-8")
    if not com_dados:
        return mapa
    ids = {e["ident"]: str(i) for i, e in enumerate(elementos, 1)}
    els = []
    for e in elementos:
        props = {"structurizr.dsl.identifier": e["ident"], "area": e["area"], "codigo": e["codigo"]}
        if e["status"]:
            props["status"] = e["status"]
        els.append({"id": ids[e["ident"]], "ident": e["ident"], "nome": e["nome"], "tipo": e["tipo"],
                    "pai": ids[e["pai"]] if e["pai"] else None, "grupo": e["area"], "desc": e["desc"],
                    "tech": e["tech"], "tags": ["Element"], "props": props, "url": ""})
    rels, rel_id = [], {}
    for n, (de, para, desc, tech) in enumerate(relacoes, len(els) + 1):
        rels.append({"id": str(n), "de": ids[de], "para": ids[para], "desc": desc, "tech": tech, "tags": ["Relationship"]})
        rel_id.setdefault((de, para), str(n))
    visoes = [{"chave": "Contexto", "tipo": "estatica", "titulo": "Contexto", "desc": "", "elementos": [], "relacoes": [],
               "passos": []}]
    for chave, f in fluxos.items():
        visoes.append({"chave": chave, "tipo": "dinamica", "titulo": f["titulo"], "desc": f.get("desc", ""),
                       "elementos": sorted({ids[p[0]] for p in f["passos"]} | {ids[p[1]] for p in f["passos"]}),
                       "relacoes": [rel_id[(p[0], p[1])] for p in f["passos"]],
                       "fluxo": [{"rel": rel_id[(p[0], p[1])], "ordem": str(i), "desc": p[2], "resposta": False}
                                 for i, p in enumerate(f["passos"], 1)]})
    dados = {"idioma": idioma, "nome": nome, "descricao": "", "arqRel": PASTA.as_posix(), "elementos": els,
             "relacoes": rels, "visoes": visoes, "adrs": [], "documentos": [], "metricas": [],
             "mudancas": {"geradoEm": "2026-01-01T00:00:00-03:00"}, "qualidade": None,
             "prova": {"geradoEm": "2026-01-01T00:00:00-03:00"}, "memoria": None}
    (mapa / "explorador" / "dados.js").write_text(
        "// Gerado por scripts/gerar_explorador.py a partir do workspace.json. Não edite à mão.\nwindow.ARQ = "
        + json.dumps(dados, ensure_ascii=False) + ";\n", encoding="utf-8")
    return mapa


BASE = [E("sis", "Lib", "Sistema"),
        E("lib", "Pacote", "Container", "sis"),
        E("lib2", "Pacote auxiliar", "Container", "sis")]


def modelo_v1():
    els = BASE + [
        E("api", "API", pai="lib", desc="Ponto de entrada da biblioteca.", tech="JavaScript", codigo="lib/api.js"),
        E("core", "Núcleo", pai="lib", desc="Despacha a requisição.", tech="JavaScript", codigo="lib/core.js"),
        E("http", "Adaptador HTTP", pai="lib", desc="Fala HTTP.", tech="Node.js", codigo="lib/http.js")]
    rels = [("api", "core", "Chama", "chamada de função"), ("core", "http", "Envia", "Node.js http")]
    fluxos = {"FlowRequest": {"titulo": "Fluxo: requisição",
                              "passos": [("api", "core", "Chama o núcleo"), ("core", "http", "Envia pela rede")]},
              "FlowLegacy": {"titulo": "Fluxo legado", "passos": [("api", "core", "Chama o núcleo")]}}
    return els, rels, fluxos


def modelo_v2():
    els, rels, fluxos = modelo_v1()
    cache = E("cache", "Cache", pai="lib", desc="Guarda respostas.", tech="JavaScript", status="Em andamento",
              codigo="lib/cache.js")
    els = BASE + [cache] + els[len(BASE):]  # entra no começo: todos os ids seguintes mudam
    for e in els:
        if e["ident"] == "api":
            e["status"] = "Em andamento"
        if e["ident"] == "core":
            e["desc"] = "Despacha a requisição e consulta o cache."
    rels = rels + [("api", "cache", "Consulta", "chamada de função")]
    fluxos["FlowRequest"] = {"titulo": "Fluxo: requisição", "passos": [
        ("api", "core", "Chama o núcleo"), ("api", "cache", "Consulta o cache"), ("core", "http", "Envia pela rede")]}
    return els, rels, fluxos


def modelo_v3():
    els, rels, fluxos = modelo_v2()
    els = [e for e in els if e["ident"] != "http"]  # sai do meio da lista: os ids seguintes mudam de novo
    for e in els:
        if e["ident"] == "core":
            e["pai"] = "lib2"
        if e["ident"] == "cache":
            e["tech"] = "TypeScript"
    rels = [r for r in rels if r[:2] != ("core", "http")] + [("core", "cache", "Lê e grava", "chamada de função")]
    fluxos = {"FlowRequest": {"titulo": "Fluxo: requisição", "passos": [
        ("api", "core", "Chama o núcleo"), ("api", "cache", "Consulta o cache")]},
        "FlowCache": {"titulo": "Fluxo do cache", "passos": [("core", "cache", "Lê e grava")]}}
    return els, rels, fluxos


R1 = "| 2026-01-11 | Modelo criado. | Primeira versão. |"
R2 = "| 2026-02-02 | Cache adicionado ao modelo. | Latência alta. |"
R3 = "| 2026-03-02 | Adaptador HTTP removido. | Foi extraído para outro pacote. |"
ASSUNTOS = ["docs(arq): mapa v1.0.0", "docs(arq): mapa v1.1.0", "docs(arq): mapa v2.0.0"]


@pytest.fixture
def historico(tmp_path):
    """Repositório com 3 versões do mapa, commits de código no meio e tags v1.0.0 e v1.1.0 no código."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "codigo.txt").write_text("v1\n", encoding="utf-8")
    commit(repo, "feat: código v1", "2026-01-10T10:00:00-03:00", tag="v1.0.0")
    escrever_mapa(repo, *modelo_v1(), [R1])
    c1 = commit(repo, ASSUNTOS[0], "2026-01-11T10:00:00-03:00")
    (repo / "codigo.txt").write_text("v2\n", encoding="utf-8")
    commit(repo, "feat: código v2", "2026-02-01T10:00:00-03:00", tag="v1.1.0")
    escrever_mapa(repo, *modelo_v2(), [R2, R1])
    c2 = commit(repo, ASSUNTOS[1], "2026-02-02T10:00:00-03:00")
    (repo / "codigo.txt").write_text("v3\n", encoding="utf-8")
    commit(repo, "feat: código v3", "2026-03-01T10:00:00-03:00")
    escrever_mapa(repo, *modelo_v3(), [R3, R2, R1])
    c3 = commit(repo, ASSUNTOS[2], "2026-03-02T10:00:00-03:00")
    return type("H", (), {"repo": repo, "mapa": repo / PASTA, "shas": [c1, c2, c3]})


def idents(lista):
    return [x["ident"] for x in lista]


def passos(lista):
    return [(p["de"], p["para"], p["desc"]) for p in lista]


# ------------------------------------------------------------------------------------------------ metadados das versões

def test_so_os_commits_que_tocaram_a_pasta_do_mapa_viram_versao(historico):
    r = lt().construir(historico.mapa)
    assert r["total_versoes"] == 3 == len(r["versoes"])  # os 3 commits de código não entram
    vs = r["versoes"]
    assert [v["sha_completo"] for v in vs] == historico.shas  # da mais antiga para a mais nova
    assert [v["sha"] for v in vs] == [s[:7] for s in historico.shas]
    assert [v["assunto"] for v in vs] == ASSUNTOS
    assert [v["indice"] for v in vs] == [1, 2, 3]
    assert [v["data"] for v in vs] == ["2026-01-11", "2026-02-02", "2026-03-02"]
    assert all(v["commitado"] and v["dados"] for v in vs)
    assert r["mapa"]["nome"] == "Lib" and r["mapa"]["pasta"] == "docs/arq"


def test_tag_do_codigo_mais_proxima_por_git_describe(historico):
    vs = lt().construir(historico.mapa)["versoes"]
    # v3: depois da tag v1.1.0 vieram o commit do mapa v2, o código v3 e o mapa v3
    assert [(v["tag"], v["tag_distancia"]) for v in vs] == [("v1.0.0", 1), ("v1.1.0", 1), ("v1.1.0", 3)]


def test_sem_nenhuma_tag_o_campo_e_nulo(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    escrever_mapa(repo, *modelo_v1(), [R1])
    commit(repo, "docs: mapa", "2026-01-11T10:00:00-03:00")
    v = lt().construir(repo / PASTA)["versoes"][0]
    assert v["tag"] is None and v["tag_distancia"] is None


# ------------------------------------------------------------------------------------------------ diff por versão

def test_v1_e_a_criacao_do_mapa_tudo_entra(historico):
    v = lt().construir(historico.mapa)["versoes"][0]
    assert v["inicial"] is True and v["base"] is None
    assert sorted(idents(v["componentes"]["adicionados"])) == ["api", "core", "http", "lib", "lib2", "sis"]
    assert v["componentes"]["removidos"] == [] and v["componentes"]["alterados"] == []
    assert sorted((r["de"], r["para"]) for r in v["relacoes"]["novas"]) == [("api", "core"), ("core", "http")]
    assert sorted(f["chave"] for f in v["fluxos"]["adicionados"]) == ["FlowLegacy", "FlowRequest"]
    assert v["fluxos"]["removidos"] == [] and v["fluxos"]["alterados"] == []
    assert v["resumo"]["total"] == 6 + 2 + 2


def test_v2_diff_exato(historico):
    v = lt().construir(historico.mapa)["versoes"][1]
    assert v["inicial"] is False and v["base"] == historico.shas[0][:7]
    c = v["componentes"]
    assert idents(c["adicionados"]) == ["cache"] and idents(c["removidos"]) == []
    assert c["adicionados"][0] == {"ident": "cache", "nome": "Cache", "tipo": "Componente", "container": "lib",
                                   "area": "AreaA", "status": "Em andamento"}
    por = {a["ident"]: a for a in c["alterados"]}
    assert sorted(por) == ["api", "core"]  # os ids de todos os componentes mudaram e nada mais aparece
    assert por["api"]["campos"] == {"status": {"antes": "Pronto", "depois": "Em andamento"}}
    assert por["core"]["campos"] == {"desc": {"antes": "Despacha a requisição.",
                                              "depois": "Despacha a requisição e consulta o cache."}}
    assert por["core"]["nome"] == "Núcleo" and por["core"]["tipo"] == "Componente"
    r = v["relacoes"]
    assert [(x["de"], x["para"], x["desc"], x["tech"]) for x in r["novas"]] == [
        ("api", "cache", "Consulta", "chamada de função")]
    assert r["novas"][0]["de_nome"] == "API" and r["novas"][0]["para_nome"] == "Cache"
    assert r["removidas"] == []
    f = v["fluxos"]
    assert f["adicionados"] == [] and f["removidos"] == []
    assert [x["chave"] for x in f["alterados"]] == ["FlowRequest"]
    alt = f["alterados"][0]
    assert alt["titulo"] == "Fluxo: requisição" and alt["campos"] == ["passos"]
    assert alt["passos"]["antes"] == 2 and alt["passos"]["depois"] == 3 and alt["passos"]["reordenado"] is False
    assert passos(alt["passos"]["adicionados"]) == [("api", "cache", "Consulta o cache")]
    assert alt["passos"]["removidos"] == []
    assert v["resumo"] == {"componentes_adicionados": 1, "componentes_removidos": 0, "componentes_alterados": 2,
                           "relacoes_novas": 1, "relacoes_removidas": 0, "fluxos_adicionados": 0,
                           "fluxos_removidos": 0, "fluxos_alterados": 1, "total": 5}


def test_v3_diff_exato(historico):
    v = lt().construir(historico.mapa)["versoes"][2]
    assert v["base"] == historico.shas[1][:7]
    c = v["componentes"]
    assert idents(c["adicionados"]) == [] and idents(c["removidos"]) == ["http"]
    assert c["removidos"][0] == {"ident": "http", "nome": "Adaptador HTTP", "tipo": "Componente", "container": "lib",
                                 "area": "AreaA", "status": "Pronto"}
    por = {a["ident"]: a["campos"] for a in c["alterados"]}
    assert por == {"cache": {"tech": {"antes": "JavaScript", "depois": "TypeScript"}},
                   "core": {"container": {"antes": "lib", "depois": "lib2"}}}
    r = v["relacoes"]
    assert [(x["de"], x["para"], x["desc"]) for x in r["novas"]] == [("core", "cache", "Lê e grava")]
    assert [(x["de"], x["para"], x["desc"]) for x in r["removidas"]] == [("core", "http", "Envia")]
    f = v["fluxos"]
    assert [x["chave"] for x in f["adicionados"]] == ["FlowCache"]
    assert [x["chave"] for x in f["removidos"]] == ["FlowLegacy"]
    assert f["removidos"][0]["titulo"] == "Fluxo legado"
    assert [x["chave"] for x in f["alterados"]] == ["FlowRequest"]
    alt = f["alterados"][0]
    assert passos(alt["passos"]["removidos"]) == [("core", "http", "Envia pela rede")] and alt["passos"]["adicionados"] == []
    assert (alt["passos"]["antes"], alt["passos"]["depois"]) == (3, 2)
    assert v["resumo"]["total"] == 0 + 1 + 2 + 1 + 1 + 1 + 1 + 1 == 8


def test_o_diff_nao_depende_do_id_numerico_do_structurizr(historico):
    """Mesmo modelo, ids embaralhados: nada muda. Só o identificador do DSL conta."""
    els, rels, fluxos = modelo_v3()
    escrever_mapa(historico.repo, list(reversed(els)), rels, fluxos, [R3, R2, R1])
    commit(historico.repo, "docs(arq): reordenou a exportação", "2026-03-03T10:00:00-03:00")
    v = lt().construir(historico.mapa)["versoes"][3]
    assert v["resumo"]["total"] == 0


def test_um_passo_de_fluxo_so_reordenado_aparece_como_reordenado(historico):
    els, rels, fluxos = modelo_v3()
    fluxos["FlowRequest"]["passos"] = list(reversed(fluxos["FlowRequest"]["passos"]))
    escrever_mapa(historico.repo, els, rels, fluxos, [R3, R2, R1])
    commit(historico.repo, "docs(arq): inverte a ordem", "2026-03-03T10:00:00-03:00")
    alt = lt().construir(historico.mapa)["versoes"][3]["fluxos"]["alterados"][0]
    assert alt["chave"] == "FlowRequest" and alt["campos"] == ["passos"]
    assert alt["passos"]["adicionados"] == [] and alt["passos"]["removidos"] == []
    assert alt["passos"]["reordenado"] is True


def test_titulo_e_nome_alterados_sao_campos(historico):
    els, rels, fluxos = modelo_v3()
    for e in els:
        if e["ident"] == "api":
            e["nome"], e["area"], e["codigo"] = "Interface", "AreaB", "lib/interface.js"
    fluxos["FlowRequest"]["titulo"] = "Fluxo: ciclo da requisição"
    escrever_mapa(historico.repo, els, rels, fluxos, [R3, R2, R1])
    commit(historico.repo, "docs(arq): renomeia", "2026-03-03T10:00:00-03:00")
    v = lt().construir(historico.mapa)["versoes"][3]
    api = v["componentes"]["alterados"][0]
    assert api["ident"] == "api" and sorted(api["campos"]) == ["area", "codigo", "nome"]
    assert api["campos"]["nome"] == {"antes": "API", "depois": "Interface"}
    assert v["fluxos"]["alterados"][0]["campos"] == ["titulo"]


# ------------------------------------------------------------------------------------------------ registro de atualizações

def test_cada_versao_traz_so_as_linhas_novas_do_registro(historico):
    vs = lt().construir(historico.mapa)["versoes"]
    assert vs[0]["registro"] == [{"data": "2026-01-11", "mudou": "Modelo criado.", "motivo": "Primeira versão."}]
    assert vs[1]["registro"] == [{"data": "2026-02-02", "mudou": "Cache adicionado ao modelo.", "motivo": "Latência alta."}]
    assert vs[2]["registro"] == [{"data": "2026-03-02", "mudou": "Adaptador HTTP removido.",
                                  "motivo": "Foi extraído para outro pacote."}]


def test_registro_com_barra_escapada_e_sem_registro(historico):
    mapa = historico.mapa
    reg = mapa / "docs" / "99-registro-de-atualizacoes.md"
    reg.write_text(reg.read_text(encoding="utf-8") + "| 2026-03-05 | Troca `a \\| b` por `c`. | Clareza. |\n", encoding="utf-8")
    commit(historico.repo, "docs(arq): registro", "2026-03-05T10:00:00-03:00")
    v = lt().construir(mapa)["versoes"][3]
    assert v["registro"] == [{"data": "2026-03-05", "mudou": "Troca `a \\| b` por `c`.", "motivo": "Clareza."}]
    reg.unlink()
    commit(historico.repo, "docs(arq): sem registro", "2026-03-06T10:00:00-03:00")
    assert lt().construir(mapa)["versoes"][4]["registro"] == []


def test_linha_do_registro_reescrita_no_mesmo_dia_nao_conta_como_entrada_nova(historico):
    """Traduzir ou corrigir o texto de uma linha antiga não cria entrada: só a linha de um dia novo entra."""
    traduzidas = ["| 2026-03-02 | Adaptador HTTP removed. | Extraído. |", "| 2026-02-02 | Cache added. | Latency. |",
                  "| 2026-01-11 | Model created. | First. |"]
    escrever_mapa(historico.repo, *modelo_v3(), ["| 2026-03-09 | Traduzido. | Idioma. |"] + traduzidas)
    commit(historico.repo, "docs(arq): traduz", "2026-03-09T10:00:00-03:00")
    assert lt().construir(historico.mapa)["versoes"][3]["registro"] == [
        {"data": "2026-03-09", "mudou": "Traduzido.", "motivo": "Idioma."}]


# ------------------------------------------------------------------------------------------------ bordas

def test_mapa_com_um_unico_commit_gera_uma_versao(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    escrever_mapa(repo, *modelo_v1(), [R1])
    commit(repo, "docs: mapa", "2026-01-11T10:00:00-03:00")
    r = lt().construir(repo / PASTA)
    assert r["total_versoes"] == 1
    v = r["versoes"][0]
    assert v["inicial"] and v["commitado"] and v["resumo"]["total"] == 10


def test_mapa_ainda_nao_commitado_vira_uma_versao_da_arvore_de_trabalho(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    commit(repo, "chore: x", "2026-01-10T10:00:00-03:00")
    escrever_mapa(repo, *modelo_v1(), [R1])
    r = lt().construir(repo / PASTA)
    assert r["total_versoes"] == 1
    v = r["versoes"][0]
    assert v["commitado"] is False and v["sha"] is None and v["sha_completo"] is None and v["assunto"] is None
    assert v["inicial"] and v["resumo"]["total"] == 10


def test_repositorio_sem_nenhum_commit_tambem_funciona(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    escrever_mapa(repo, *modelo_v1(), [R1])
    r = lt().construir(repo / PASTA)
    assert r["total_versoes"] == 1 and r["versoes"][0]["commitado"] is False


def test_alteracao_nao_commitada_vira_a_ultima_versao(historico):
    els, rels, fluxos = modelo_v3()
    els.append(E("novo", "Novo", pai="lib", desc="Recém-gerado.", tech="JavaScript"))
    escrever_mapa(historico.repo, els, rels, fluxos, [R3, R2, R1])  # sem commit
    r = lt().construir(historico.mapa)
    assert r["total_versoes"] == 4
    v = r["versoes"][3]
    assert v["commitado"] is False and v["sha"] is None and v["base"] == historico.shas[2][:7]
    assert idents(v["componentes"]["adicionados"]) == ["novo"] and v["resumo"]["total"] == 1


def test_arvore_igual_ao_ultimo_commit_nao_cria_versao_extra(historico):
    """Só o carimbo de geração mudou (o atualizar.py regrava o dados.js a cada rodada): não há versão nova."""
    dados = historico.mapa / "explorador" / "dados.js"
    dados.write_text(dados.read_text(encoding="utf-8").replace("2026-01-01T00:00:00-03:00", "2026-07-07T07:07:07-03:00"),
                     encoding="utf-8")
    assert git(historico.repo, "status", "--short")  # o arquivo está mesmo modificado
    assert lt().construir(historico.mapa)["total_versoes"] == 3


def test_max_versoes_guarda_as_mais_novas_e_o_diff_continua_contra_a_anterior(historico):
    cheio = lt().construir(historico.mapa)["versoes"]
    r = lt().construir(historico.mapa, max_versoes=2)
    assert r["total_versoes"] == 2
    assert [v["sha"] for v in r["versoes"]] == [cheio[1]["sha"], cheio[2]["sha"]]
    assert r["versoes"][0]["inicial"] is False and r["versoes"][0]["base"] == cheio[0]["sha"]
    assert r["versoes"][0]["componentes"] == cheio[1]["componentes"]
    assert r["versoes"][0]["resumo"] == cheio[1]["resumo"]
    assert [v["indice"] for v in r["versoes"]] == [1, 2]
    assert lt().construir(historico.mapa, max_versoes=1)["versoes"][0]["sha"] == cheio[2]["sha"]


def test_commit_que_nao_muda_a_arquitetura_fica_com_total_zero_e_pode_ser_omitido(historico):
    (historico.mapa / "docs" / "01-visao.md").write_text("texto\n", encoding="utf-8")
    commit(historico.repo, "docs(arq): só texto", "2026-03-10T10:00:00-03:00")
    mod = lt()
    r = mod.construir(historico.mapa)
    assert r["total_versoes"] == 4 and r["versoes"][3]["resumo"]["total"] == 0
    assert r["versoes"][3]["registro"] == []
    r = mod.construir(historico.mapa, omitir_sem_mudanca=True)
    assert r["total_versoes"] == 3 and [v["indice"] for v in r["versoes"]] == [1, 2, 3]


def test_versao_sem_dados_js_nao_quebra_e_a_seguinte_nao_e_inicial_falsa(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    escrever_mapa(repo, *modelo_v1(), [R1], com_dados=False)
    commit(repo, "docs: só o registro", "2026-01-11T10:00:00-03:00")
    escrever_mapa(repo, *modelo_v1(), [R1])
    commit(repo, "docs: mapa", "2026-01-12T10:00:00-03:00")
    vs = lt().construir(repo / PASTA)["versoes"]
    assert vs[0]["dados"] is False and vs[0]["resumo"] is None and vs[0]["componentes"] == {
        "adicionados": [], "removidos": [], "alterados": []}
    assert vs[1]["dados"] is True and vs[1]["inicial"] is True and vs[1]["base"] is None
    assert vs[1]["resumo"]["total"] == 10


def test_dados_js_corrompido_vira_versao_sem_dados_e_nao_derruba(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    mapa = escrever_mapa(repo, *modelo_v1(), [R1])
    commit(repo, "docs: mapa", "2026-01-11T10:00:00-03:00")
    (mapa / "explorador" / "dados.js").write_text("window.ARQ = {quebrado\n", encoding="utf-8")
    commit(repo, "docs: dados quebrado", "2026-01-12T10:00:00-03:00")
    escrever_mapa(repo, *modelo_v2(), [R2, R1])
    commit(repo, "docs: dados refeito", "2026-01-13T10:00:00-03:00")
    vs = lt().construir(mapa)["versoes"]
    assert [v["dados"] for v in vs] == [True, False, True]
    assert vs[1]["erro"]
    assert vs[2]["base"] == vs[0]["sha"] and vs[2]["resumo"]["componentes_adicionados"] == 1


def test_troca_de_idioma_e_marcada(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    escrever_mapa(repo, *modelo_v1(), [R1], idioma="en")
    commit(repo, "docs: map", "2026-01-11T10:00:00-03:00")
    els, rels, fluxos = modelo_v1()
    for e in els:
        e["desc"] = e["desc"] + " (traduzido)"
    escrever_mapa(repo, els, rels, fluxos, [R1], idioma="pt")
    commit(repo, "docs: pt", "2026-01-12T10:00:00-03:00")
    vs = lt().construir(repo / PASTA)["versoes"]
    assert vs[0]["idioma"] == "en" and vs[0]["mudou_idioma"] is None
    assert vs[1]["idioma"] == "pt" and vs[1]["mudou_idioma"] == {"de": "en", "para": "pt"}


def test_rev_le_outro_ramo_sem_trocar_de_ramo(historico):
    git(historico.repo, "branch", "-f", "demo", historico.shas[1])
    atual = git(historico.repo, "rev-parse", "--abbrev-ref", "HEAD")
    r = lt().construir(historico.mapa, rev="demo")
    assert r["total_versoes"] == 2 and r["mapa"]["rev"] == "demo"
    assert git(historico.repo, "rev-parse", "--abbrev-ref", "HEAD") == atual


def test_fora_de_um_repositorio_git_levanta_sem_git(tmp_path):
    mapa = tmp_path / "solto"
    mapa.mkdir()
    (mapa / "explorador").mkdir()
    mod = lt()
    ceiling = os.environ.get("GIT_CEILING_DIRECTORIES")
    os.environ["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    try:
        with pytest.raises(mod.SemGit):
            mod.construir(mapa)
    finally:
        if ceiling is None:
            del os.environ["GIT_CEILING_DIRECTORIES"]
        else:
            os.environ["GIT_CEILING_DIRECTORIES"] = ceiling


# ------------------------------------------------------------------------------------------------ CLI e arquivos gerados

def cli(*args, idioma="pt", cwd=None, extra_env=None):
    env = _env()
    env["LODEMAP_IDIOMA"] = idioma
    env.update(extra_env or {})
    # -I ignora PYTHONIOENCODING; -X utf8 faz o filho falar UTF-8 no pipe, como o teste lê
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8",
                          env=env, cwd=cwd, timeout=60)


def test_cli_grava_js_e_json_iguais_e_o_js_passa_no_node_check(historico):
    r = cli("--mapa", str(historico.mapa))
    assert r.returncode == 0, r.stdout + r.stderr
    js = historico.mapa / "explorador" / "linha-do-tempo.js"
    js_json = historico.mapa / "explorador" / "linha-do-tempo.json"
    assert js.is_file() and js_json.is_file()
    texto = js.read_text(encoding="utf-8")
    assert texto.splitlines()[0].startswith("//") and "window.LODEMAP_LINHA_DO_TEMPO = " in texto
    corpo = texto.split("window.LODEMAP_LINHA_DO_TEMPO = ", 1)[1].rstrip().removesuffix(";")
    dados = json.loads(js_json.read_text(encoding="utf-8"))
    assert json.loads(corpo) == dados
    assert dados["formato"] == 1 and dados["total_versoes"] == 3
    assert dados["versoes"][1]["componentes"]["adicionados"][0]["ident"] == "cache"
    assert "3" in r.stdout and "versões" in r.stdout
    if shutil.which("node"):
        n = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True, encoding="utf-8")
        assert n.returncode == 0, n.stderr


def test_js_com_script_de_fechamento_no_texto_nao_quebra_o_html(historico):
    els, rels, fluxos = modelo_v3()
    els[3]["desc"] = "Texto com </script> e   separador."
    escrever_mapa(historico.repo, els, rels, fluxos, [R3, R2, R1])
    commit(historico.repo, "docs(arq): texto estranho", "2026-03-03T10:00:00-03:00")
    assert cli("--mapa", str(historico.mapa)).returncode == 0
    js = historico.mapa / "explorador" / "linha-do-tempo.js"
    texto = js.read_text(encoding="utf-8")
    assert "</script" not in texto.lower() and " " not in texto
    corpo = texto.split("window.LODEMAP_LINHA_DO_TEMPO = ", 1)[1].rstrip().removesuffix(";")
    alt = json.loads(corpo)["versoes"][3]["componentes"]["alterados"][0]["campos"]["desc"]["depois"]
    assert alt == "Texto com </script> e   separador."  # o JSON volta ao texto original
    if shutil.which("node"):
        assert subprocess.run(["node", "--check", str(js)], capture_output=True).returncode == 0


def test_cli_saida_e_max_versoes_e_resumo(historico, tmp_path):
    saida = tmp_path / "fora"
    r = cli("--mapa", str(historico.mapa), "--saida", str(saida), "--max-versoes", "2", "--resumo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (saida / "linha-do-tempo.js").is_file() and (saida / "linha-do-tempo.json").is_file()
    assert not (historico.mapa / "explorador" / "linha-do-tempo.js").exists()
    assert json.loads((saida / "linha-do-tempo.json").read_text(encoding="utf-8"))["total_versoes"] == 2
    assert "v1.1.0" in r.stdout and "v1.0.0" not in r.stdout  # a tabela só lista as 2 versões mantidas
    assert r.stdout.count("docs(arq)") == 2


def test_cli_rodar_duas_vezes_da_o_mesmo_arquivo(historico):
    assert cli("--mapa", str(historico.mapa)).returncode == 0
    js = historico.mapa / "explorador" / "linha-do-tempo.json"
    antes = js.read_bytes()
    assert cli("--mapa", str(historico.mapa)).returncode == 0
    assert js.read_bytes() == antes  # sem carimbo de hora: nada de diff à toa no git


def test_cli_fora_de_repositorio_git_sai_com_3_e_explica(tmp_path):
    mapa = tmp_path / "solto"
    (mapa / "explorador").mkdir(parents=True)
    r = cli("--mapa", str(mapa), extra_env={"GIT_CEILING_DIRECTORIES": str(tmp_path)})
    assert r.returncode == 3, r.stdout + r.stderr
    assert "git" in r.stderr and "Traceback" not in r.stderr
    assert not (mapa / "explorador" / "linha-do-tempo.js").exists()
    r = cli("--mapa", str(mapa), idioma="en", extra_env={"GIT_CEILING_DIRECTORIES": str(tmp_path)})
    assert r.returncode == 3 and "repository" in r.stderr.lower()


def test_cli_pasta_inexistente_sai_com_2_sem_traceback(tmp_path):
    r = cli("--mapa", str(tmp_path / "nao-existe"))
    assert r.returncode == 2 and "Traceback" not in r.stderr and r.stderr.strip()


def test_cli_help_em_ingles_sem_portugues():
    r = cli("--help", idioma="en")
    assert r.returncode == 0, r.stderr
    assert "--mapa" in r.stdout and "--max-versions" in r.stdout and "timeline" in r.stdout.lower()
    for pt in ("padrão", "pasta do", "caminho do", "obrigatório"):
        assert pt not in r.stdout, (pt, r.stdout)


# ------------------------------------------------------------------------------------------------ ligação ao atualizar.py

def _atualizar():
    spec = importlib.util.spec_from_file_location("lodemap_atualizar_lt", ATUALIZAR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def projeto(tmp_path, monkeypatch):
    raiz = tmp_path / "repo" / "docs" / "arq"
    (raiz / "scripts").mkdir(parents=True)
    (raiz / "workspace.dsl").write_text("workspace {}\n", encoding="utf-8")
    tpl = tmp_path / "skill" / "templates" / "structurizr"
    for rel in ("explorador/index.html", "leitor/index.html", "explorador/vendor/lib.js", "leitor/vendor/lib.js"):
        (tpl / rel).parent.mkdir(parents=True, exist_ok=True)
        (tpl / rel).write_text("x", encoding="utf-8")
    (tmp_path / "skill" / "scripts").mkdir(parents=True)
    (tmp_path / "skill" / "scripts" / "codegraph_ponte.py").write_text("pass\n", encoding="utf-8")
    cli_falso = tmp_path / "ferr" / "cli" / ("structurizr.bat" if os.name == "nt" else "structurizr.sh")
    cli_falso.parent.mkdir(parents=True)
    cli_falso.write_text("fake", encoding="utf-8")
    os.chmod(cli_falso, 0o755)
    monkeypatch.delenv("LODEMAP_EXTENSOES", raising=False)
    monkeypatch.delenv("STRUCTURIZR_CLI", raising=False)
    return type("P", (), {"raiz": raiz, "scripts": raiz / "scripts", "tpl": tpl, "cli": cli_falso, "tmp": tmp_path,
                          "script_lt": tmp_path / "skill" / "scripts" / "linha_do_tempo.py"})


class Gravador:
    def __init__(self, topo: Path, rc_lt: int = 0, explode: bool = False):
        self.chamadas, self.topo, self.rc_lt, self.explode = [], topo, rc_lt, explode

    def __call__(self, cmd, **kw):
        self.chamadas.append((list(cmd), kw))
        if cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, 0, stdout=str(self.topo) + "\n", stderr="")
        if "linha_do_tempo.py" in " ".join(map(str, cmd)):
            if self.explode:
                raise OSError("sem permissão")
            return subprocess.CompletedProcess(cmd, self.rc_lt, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def lt(self):
        return [c for c, _ in self.chamadas if "linha_do_tempo.py" in " ".join(map(str, c))]


def _rodar_atualizar(projeto, monkeypatch, grav):
    at = _atualizar()
    monkeypatch.setattr(at.subprocess, "run", grav)
    return at.main(["--template", str(projeto.tpl), "--cli", str(projeto.cli), "--ferramentas", str(projeto.tmp / "ferr"),
                    "--python", "PY"], scripts=projeto.scripts)


def test_atualizar_roda_a_linha_do_tempo_como_ultima_etapa(projeto, monkeypatch, capsys):
    projeto.script_lt.write_text("pass\n", encoding="utf-8")
    grav = Gravador(projeto.tmp / "repo")
    assert _rodar_atualizar(projeto, monkeypatch, grav) == 0
    chamadas = [c for c, _ in grav.chamadas]
    assert grav.lt() == [["PY", str(projeto.tpl / ".." / ".." / "scripts" / "linha_do_tempo.py"),
                          "--mapa", str(projeto.raiz)]]
    marcar = max(i for i, c in enumerate(chamadas) if "--marcar" in c)
    assert chamadas.index(grav.lt()[0]) > marcar  # depois de marcar o commit: é a última etapa
    out = capsys.readouterr().out
    assert "Pronto." in out and out.index("linha do tempo") < out.index("Pronto.")


@pytest.mark.parametrize("rc,explode,trecho", [(3, False, "git"), (1, False, "falhou"), (0, True, "não rodou")])
def test_atualizar_nao_falha_quando_a_linha_do_tempo_falha_so_avisa(projeto, monkeypatch, capsys, rc, explode, trecho):
    projeto.script_lt.write_text("pass\n", encoding="utf-8")
    assert _rodar_atualizar(projeto, monkeypatch, Gravador(projeto.tmp / "repo", rc_lt=rc, explode=explode)) == 0
    cap = capsys.readouterr()
    assert "AVISO" in cap.err and "linha do tempo" in cap.err and trecho in cap.err
    assert "Pronto." in cap.out


def test_atualizar_sem_o_script_da_skill_segue_sem_a_etapa(projeto, monkeypatch, capsys):
    assert not projeto.script_lt.exists()
    grav = Gravador(projeto.tmp / "repo")
    assert _rodar_atualizar(projeto, monkeypatch, grav) == 0
    assert grav.lt() == []
    assert "Pronto." in capsys.readouterr().out
