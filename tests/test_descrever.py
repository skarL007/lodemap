"""Rota enxuta de descrições (scripts/descrever.py) com um claude falso: nenhum token gasto, nenhuma rede."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from lodemap import RAIZ

sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
import descrever  # noqa: E402
import esqueleto  # noqa: E402
from test_esqueleto import _arq, projeto  # noqa: E402,F401

FALSO = r'''
import json, os, re, sys
args = sys.argv[1:]
open(os.environ["LODEMAP_FALSO_LOG"], "a", encoding="utf-8").write(json.dumps(args) + "\n")
modo = os.environ.get("LODEMAP_FALSO_MODO", "ok")
if modo == "erro":
    print("sem login", file=sys.stderr); sys.exit(1)
sch = json.loads(args[args.index("--json-schema") + 1])
sys.stdin.reconfigure(encoding="utf-8"); sys.stdout.reconfigure(encoding="utf-8")
texto = sys.stdin.read()
uso = {"input_tokens": 3, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0, "output_tokens": 50}
if "veredito" in sch["properties"]["itens"]["items"]["properties"]:
    conf = os.environ.get("LODEMAP_FALSO_CONFERIR", "ok")
    itens = []
    for i, mod in re.findall(r"### i=(\d+)\n(?:Módulo|Module): (\S+)", texto):
        if conf == "ok" or not mod.endswith("regras.py"):
            itens.append({"i": int(i), "veredito": "ok", "afirmacao": "", "correcao": "", "evidencia": []})
        elif conf == "falsa":
            itens.append({"i": int(i), "veredito": "falsa", "afirmacao": "o módulo não lê o repositório",
                          "correcao": "Define calcular, que devolve o valor da regra local sem tocar em estado global.",
                          "evidencia": ["def calcular"]})
        else:
            itens.append({"i": int(i), "veredito": "falsa", "afirmacao": "o módulo não lê o repositório",
                          "correcao": "Chama `buscarNoBanco` para ler as regras do repositório remoto antes de calcular.",
                          "evidencia": ["def calcular"]})
    print(json.dumps({"type": "result", "is_error": False, "num_turns": 2, "structured_output": {"itens": itens},
                      "usage": uso}))
    sys.exit(0)
area = sch["properties"]["itens"]["items"]["properties"]["area"]["enum"][0]
retry = "reprovada" in texto
itens = []
blocos = re.split(r"(?=### i=\d+\n)", texto)
atual = {}
for b in blocos:
    m = re.match(r"### i=(\d+)\n", b)
    a = re.search(r"Descrição atual \(escrita antes de o módulo mudar\): (.+)", b)
    if m and a:
        atual[int(m.group(1))] = a.group(1).strip()
for i, mod in re.findall(r"### i=(\d+)\nMódulo: (\S+)", texto):
    base = mod.strip("/").split("/")[-1].replace(".py", "")
    if modo == "mantem" and int(i) in atual:
        itens.append({"i": int(i), "nome": "Outro nome", "descricao": atual[int(i)], "area": area,
                      "evidencia": [f"Módulo: {mod}"]})
        continue
    if modo == "generico" and not retry:
        d = "Este componente faz coisas de forma eficiente para o sistema inteiro funcionar bem."
    else:
        d = f"Calcula {base} a partir das regras locais e devolve o valor para quem chama, sem estado global."
    ev = ["trecho que não está em lugar nenhum da ficha"] if modo == "sem_prova" and not retry else [f"Módulo: {mod}"]
    itens.append({"i": int(i), "nome": f"Peça {base}", "descricao": d, "area": area, "evidencia": ev})
print(json.dumps({"type": "result", "is_error": False, "num_turns": 2, "structured_output": {"itens": itens},
                  "usage": {"input_tokens": 3, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0,
                            "output_tokens": 50 * len(itens)}}))
'''


def _preparar(projeto, tmp_path, monkeypatch, modo="ok", conferir="ok"):
    arq = _arq(projeto)
    d = esqueleto.rascunho(projeto, arq, fonte="ast")
    d["areas"] = {"AreaNucleo": "Núcleo"}
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    falso = tmp_path / "claude_falso.py"
    falso.write_text(FALSO, encoding="utf-8")
    log = tmp_path / "chamadas.log"
    monkeypatch.setenv("LODEMAP_CLAUDE", str(falso))
    monkeypatch.setenv("LODEMAP_FALSO_LOG", str(log))
    monkeypatch.setenv("LODEMAP_FALSO_MODO", modo)
    monkeypatch.setenv("LODEMAP_FALSO_CONFERIR", conferir)
    return arq, log


def _so_descrever(chamadas):
    return [a for a in chamadas if "veredito" not in a[a.index("--json-schema") + 1]]


def _chamadas(log: Path) -> list[list[str]]:
    return [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []


def test_descreve_os_pendentes_numa_chamada_enxuta(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    rel = descrever.descrever(arq, projeto)
    assert rel["alvos"] == 3 and rel["descritos"] == 3 and rel["para_modelador"] == []
    chamadas = _chamadas(log)
    assert len(chamadas) == 2, "uma chamada para descrever e uma para conferir"
    assert "veredito" in chamadas[1][chamadas[1].index("--json-schema") + 1]
    assert rel["conferencia"] == {"modelo": "haiku", "conferidas": 3, "falsas": 0, "corrigidas": 0, "incertas": 0}
    a = chamadas[0]
    for flag in ("--tools", "--strict-mcp-config", "--setting-sources", "--no-session-persistence", "--json-schema",
                 "--system-prompt-file"):
        assert flag in a
    assert a[a.index("--tools") + 1] == "" and a[a.index("--setting-sources") + 1] == ""
    assert a[a.index("--model") + 1] == "haiku" and a[a.index("--effort") + 1] == "medium"
    assert "--bare" not in a  # --bare exige chave de API; a rota é só pela assinatura
    d = json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))
    assert all(c["descricao"] and c["area"] == "AreaNucleo" for c in d["componentes"])
    assert d["pendentes"]["componentes_novos"] == [] and d["pendentes"]["descricoes_para_modelador"] == []
    assert rel["tokens"]["total"] > 0


def test_area_fora_das_decididas_e_recusada_no_schema(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    descrever.descrever(arq, projeto)
    a = _chamadas(log)[0]
    sch = json.loads(a[a.index("--json-schema") + 1])
    assert sch["properties"]["itens"]["items"]["properties"]["area"]["enum"] == ["AreaNucleo"]


def test_gate_reenvia_so_os_reprovados_uma_vez(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch, modo="generico")
    rel = descrever.descrever(arq, projeto)
    assert len(_so_descrever(_chamadas(log))) == 2 and rel["reenviados"] == 3 and rel["descritos"] == 3


def test_falha_do_cli_devolve_tudo_ao_modelador(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch, modo="erro")
    rel = descrever.descrever(arq, projeto)
    assert rel["descritos"] == 0 and len(rel["para_modelador"]) == 3
    assert len(_chamadas(log)) == 1  # sem reenvio quando o próprio CLI falhou
    d = json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))
    assert len(d["pendentes"]["descricoes_para_modelador"]) == 3
    assert all(not c["descricao"] for c in d["componentes"])
    assert descrever.main(["--arq", str(arq), "--repo", str(projeto)]) == 3


def test_sem_areas_recusa_antes_de_chamar(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    d = json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))
    d["areas"] = {}
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d), encoding="utf-8")
    assert descrever.main(["--arq", str(arq), "--repo", str(projeto)]) == 2
    assert _chamadas(log) == []


def test_so_os_marcados_ou_vazios_sao_alvo(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    descrever.descrever(arq, projeto)
    open(log, "w").close()
    rel = descrever.descrever(arq, projeto)  # nada pendente: nenhuma chamada
    assert rel["alvos"] == 0 and _chamadas(log) == []
    d = json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))
    d["pendentes"]["componentes_revisar"] = ["app/api.py"]
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    rel = descrever.descrever(arq, projeto)
    assert rel["alvos"] == 1 and len(_so_descrever(_chamadas(log))) == 1


def test_ficha_traz_superficie_e_relacoes_sem_o_corpo_inteiro(projeto):
    c = {"modulo": "app/regras.py", "linguagem": "python", "linhas": 5}
    f = descrever.ficha(projeto, c, [{"de": "app/api.py", "para": "app/regras.py"}])
    assert "Regras de negócio." in f and "- calcular" in f and "É usado por: app/api.py" in f
    assert len(f) <= descrever.TETO_FICHA + 400


def test_gate_pega_generico_tamanho_e_termo():
    f = "Módulo: app/regras.py\n- calcular"
    assert "genérica" in descrever.gate({"nome": "x", "descricao": "Este módulo calcula tudo garantindo coisas boas para todos."}, f, "app/regras.py")
    assert "tamanho" in descrever.gate({"nome": "x", "descricao": "Calcula."}, f, "app/regras.py")
    assert "termo" in descrever.gate({"nome": "x", "descricao": "Faz uma operação simples e rápida sobre os números do dia a dia."}, f, "app/regras.py")
    assert descrever.gate({"nome": "x", "descricao": "Calcula o valor final a partir das regras locais, sem estado global."}, f, "app/regras.py") == ""


def test_gate_com_codigo_recusa_nome_inventado_e_evidencia_que_nao_esta_na_ficha():
    f = "Módulo: app/regras.py\n- calcular\ndef calcular(x):"
    cod = "def calcular(x):\n    return x * TAXA_PADRAO\n"
    base = {"nome": "x", "evidencia": ["def calcular(x):"]}
    ok = "Calcula o valor final a partir das regras locais com TAXA_PADRAO, sem estado global."
    assert descrever.gate(dict(base, descricao=ok), f, "app/regras.py", cod) == ""
    inventado = "Calcula o valor final com `aplicarDesconto` e as regras locais, sem estado global nenhum."
    assert "aplicarDesconto" in descrever.gate(dict(base, descricao=inventado), f, "app/regras.py", cod)
    cab = "Calcula o valor final das regras locais e lê o cabeçalho X-Forwarded-For de cada pedido."
    assert "X-Forwarded-For" in descrever.gate(dict(base, descricao=cab), f, "app/regras.py", cod)
    sem = {"nome": "x", "descricao": ok, "evidencia": []}
    assert "sem evidência" in descrever.gate(sem, f, "app/regras.py", cod)
    falsa = {"nome": "x", "descricao": ok, "evidencia": ["def calcular_tudo(x, y):"]}
    assert "não aparece na ficha" in descrever.gate(falsa, f, "app/regras.py", cod)
    # sem código (chamada antiga), o gate continua só de forma
    assert descrever.gate({"nome": "x", "descricao": inventado}, f, "app/regras.py") == ""


def test_nomes_citados_ignora_palavras_comuns_e_abreviacoes():
    n = descrever.nomes_citados("Usa path.Clean e read_config em JavaScript, e.g. no GitHub, via onUploadProgress, "
                                "para URLs e IDs.")
    assert n == ["path.Clean", "read_config", "onUploadProgress"]


def test_evidencia_casa_comentario_quebrado_em_varias_linhas():
    """Medido no axios: a conferência citou numa linha um comentário que o código quebra em duas."""
    cod = ("  // class/template prototype are honored, but values injected onto a polluted\n"
           "  // Object.prototype are ignored.\n")
    o = {"evidencia": ["values injected onto a polluted Object.prototype are ignored"]}
    assert descrever._evidencia(o, "", cod) == ""


def test_evidencia_falsa_reenvia_e_depois_passa(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch, modo="sem_prova")
    rel = descrever.descrever(arq, projeto)
    assert rel["reenviados"] == 3 and rel["descritos"] == 3 and rel["para_modelador"] == []


def test_conferencia_troca_frase_falsa_pela_correcao(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch, conferir="falsa")
    rel = descrever.descrever(arq, projeto)
    assert rel["conferencia"]["falsas"] == 1 and rel["conferencia"]["corrigidas"] == 1
    d = json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))
    c = next(c for c in d["componentes"] if c["modulo"] == "app/regras.py")
    assert c["descricao"].startswith("Define calcular")


def test_correcao_reprovada_vai_para_o_modelador(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch, conferir="falsa_ruim")
    rel = descrever.descrever(arq, projeto)
    assert [p["modulo"] for p in rel["para_modelador"]] == ["app/regras.py"]
    assert "buscarNoBanco" in rel["para_modelador"][0]["motivo"]
    d = json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))
    assert d["pendentes"]["descricoes_para_modelador"][0]["modulo"] == "app/regras.py"
    c = next(c for c in d["componentes"] if c["modulo"] == "app/regras.py")
    assert not c.get("descricao"), "frase que a conferência reprovou não é gravada"


def test_sem_conferir_faz_uma_chamada_so(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    assert descrever.main(["--arq", str(arq), "--repo", str(projeto), "--sem-conferir"]) == 0
    assert len(_chamadas(log)) == 1


def test_auditar_lista_as_falsas_sem_mudar_nada(projeto, tmp_path, monkeypatch, capsys):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    descrever.descrever(arq, projeto, conferir_com=None)
    destino = esqueleto.caminho_decisoes(arq)
    antes = destino.read_text(encoding="utf-8")
    monkeypatch.setenv("LODEMAP_FALSO_CONFERIR", "falsa")
    capsys.readouterr()
    assert descrever.main(["--arq", str(arq), "--repo", str(projeto), "--auditar"]) == 3
    r = json.loads(capsys.readouterr().out)
    assert [f["modulo"] for f in r["falsas"]] == ["app/regras.py"] and r["conferidas"] == 3
    assert destino.read_text(encoding="utf-8") == antes


def _marcar_revisao(arq, modulo="app/regras.py"):
    """Deixa tudo descrito e marca um módulo como 'a revisar', com nome e área decididos antes."""
    destino = esqueleto.caminho_decisoes(arq)
    d = json.loads(destino.read_text(encoding="utf-8"))
    d["areas"] = {"AreaNucleo": "Núcleo", "AreaDados": "Dados"}
    for c in d["componentes"]:
        c.update(nome="Nome decidido", area="AreaDados",
                 descricao="Aplica as regras de negócio da amostra sobre os dados lidos do repositório local.")
    d["pendentes"] = {"componentes_novos": [], "componentes_revisar": [modulo], "relacoes_novas": []}
    destino.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return destino


def test_revisao_guarda_nome_e_area_e_so_troca_a_frase(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    destino = _marcar_revisao(arq)
    rel = descrever.descrever(arq, projeto)
    assert rel["alvos"] == 1 and rel["revisados"] == 1 and rel["mantidos"] == 0 and rel["descritos"] == 1
    c = next(c for c in json.loads(destino.read_text(encoding="utf-8"))["componentes"] if c["modulo"] == "app/regras.py")
    assert c["nome"] == "Nome decidido" and c["area"] == "AreaDados", "nome e área de uma revisão não mudam"
    assert c["descricao"].startswith("Calcula regras") and c["descrito_por"].startswith("claude -p")


def test_revisao_que_devolve_a_mesma_frase_conta_como_mantida(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch, modo="mantem")
    destino = _marcar_revisao(arq)
    antes = json.loads(destino.read_text(encoding="utf-8"))
    rel = descrever.descrever(arq, projeto)
    assert rel["revisados"] == 1 and rel["mantidos"] == 1 and rel["para_modelador"] == []
    depois = json.loads(destino.read_text(encoding="utf-8"))
    a = next(c for c in antes["componentes"] if c["modulo"] == "app/regras.py")
    b = next(c for c in depois["componentes"] if c["modulo"] == "app/regras.py")
    assert (b["nome"], b["descricao"], b["area"]) == (a["nome"], a["descricao"], a["area"])
    assert "descrito_por" not in b, "frase mantida não ganha autoria nova"
    assert depois["pendentes"]["componentes_revisar"] == []
    assert "kept as written" in descrever.resumo(rel, "en") and "mantidas como estavam" in descrever.resumo(rel, "pt")


def test_todos_refaz_do_zero_sem_modo_revisao(projeto, tmp_path, monkeypatch):
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    _marcar_revisao(arq)
    rel = descrever.descrever(arq, projeto, todos=True)
    assert rel["revisados"] == 0 and rel["descritos"] == 3


def test_modulo_novo_descrito_continua_listado_ate_ter_container_e_status(projeto, tmp_path, monkeypatch):
    """Descrever tira o módulo de `componentes_novos`; a lista do que o modelador ainda decide não pode sumir junto."""
    arq, log = _preparar(projeto, tmp_path, monkeypatch)
    destino = _marcar_revisao(arq)
    d = json.loads(destino.read_text(encoding="utf-8"))
    novo = next(c for c in d["componentes"] if c["modulo"] == "app/regras.py")
    for k in ("nome", "descricao", "area", "container", "status"):
        novo.pop(k, None)
    for c in d["componentes"]:
        if c is not novo:
            c.update(container="app", status="Pronto")
    d["pendentes"] = {"componentes_novos": ["app/regras.py"], "componentes_revisar": [], "relacoes_novas": []}
    destino.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    rel = descrever.descrever(arq, projeto)
    pend = json.loads(destino.read_text(encoding="utf-8"))["pendentes"]
    assert pend["componentes_novos"] == [] and pend["componentes_sem_container_ou_status"] == ["app/regras.py"]
    assert rel["revisados"] == 0 and "1 still need container and status" in descrever.resumo(rel, "en")
