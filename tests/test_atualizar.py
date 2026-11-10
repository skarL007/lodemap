"""atualizar.py: o pipeline multiplataforma do Lodemap (argumentos, descoberta do CLI, extensões, ordem das etapas)."""
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

ESTRUTURIZR = RAIZ / "templates" / "structurizr"
ARQUIVO = ESTRUTURIZR / "scripts" / "atualizar.py"
CLI_REAL = [p for p in (Path.home() / ".structurizr" / "cli" / "structurizr.bat",
                        Path.home() / ".structurizr" / "cli" / "structurizr.sh") if p.is_file()]


def _carregar():
    spec = importlib.util.spec_from_file_location("lodemap_atualizar", ARQUIVO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


at = _carregar()


# ------------------------------------------------------------------------------------------------ argumentos

def test_argumentos_padrao_vem_do_ambiente_e_da_pasta_pessoal(tmp_path):
    a = at.parse_args([], env={})
    assert a.ferramentas == str(Path.home() / ".structurizr")
    assert a.python == sys.executable
    assert a.template.endswith(str(Path("templates") / "structurizr"))
    assert not (a.com_site or a.sem_site or a.sem_extensoes or a.incremental)
    assert a.checkpoint == "" and a.cli == ""
    env = {"STRUCTURIZR_FERRAMENTAS": str(tmp_path / "f"), "LODEMAP_PYTHON": "py3", "LODEMAP_TEMPLATE": str(tmp_path / "t")}
    a = at.parse_args([], env=env)
    assert (a.ferramentas, a.python, a.template) == (str(tmp_path / "f"), "py3", str(tmp_path / "t"))
    # sem LODEMAP_TEMPLATE, a pasta da skill (a mesma variável do lodemap_decidir.py) dá o template
    a = at.parse_args([], env={"LODEMAP_SKILL": str(tmp_path / "skill")})
    assert a.template == str(tmp_path / "skill" / "templates" / "structurizr")
    a = at.parse_args([], env={"LODEMAP_SKILL": str(tmp_path / "skill"), "LODEMAP_TEMPLATE": str(tmp_path / "t")})
    assert a.template == str(tmp_path / "t")


def test_argumentos_em_kebab_case_espelham_os_parametros_do_ps1():
    a = at.parse_args(["--com-site", "--sem-extensoes", "--sem-site", "--incremental", "--checkpoint", "merge feat/ç",
                       "--ferramentas", "F", "--python", "P", "--template", "T", "--cli", "C"], env={})
    assert a.com_site and a.sem_extensoes and a.sem_site and a.incremental
    assert (a.checkpoint, a.ferramentas, a.python, a.template, a.cli) == ("merge feat/ç", "F", "P", "T", "C")


def test_checkpoint_env_le_o_rotulo_do_ambiente_com_acentos():
    a = at.parse_args(["--checkpoint-env"], env={"LODEMAP_CHECKPOINT": "pós-merge ação"})
    assert a.checkpoint == "pós-merge ação"
    # o rótulo explícito vence a variável
    assert at.parse_args(["--checkpoint-env", "--checkpoint", "x"], env={"LODEMAP_CHECKPOINT": "y"}).checkpoint == "x"


def test_argumento_desconhecido_sai_com_codigo_2(capsys):
    with pytest.raises(SystemExit) as e:
        at.parse_args(["--nao-existe"], env={})
    assert e.value.code == 2


# ------------------------------------------------------------------------------------------------ Structurizr CLI

def _fake_cli(pasta: Path, nome: str) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    p = pasta / nome
    p.write_text("fake", encoding="utf-8")
    return p


def _sem_path(_nome, path=None):
    return None


@pytest.mark.parametrize("windows,nome", [(True, "structurizr.bat"), (False, "structurizr.sh")])
def test_cli_por_env_arquivo_ou_pasta(tmp_path, windows, nome):
    cli = _fake_cli(tmp_path / "x", nome)
    achado = at.localizar_cli(tmp_path / "vazio", env={"STRUCTURIZR_CLI": str(cli)}, which=_sem_path, windows=windows)
    assert achado == cli
    achado = at.localizar_cli(tmp_path / "vazio", env={"STRUCTURIZR_CLI": str(cli.parent)}, which=_sem_path, windows=windows)
    assert achado == cli


def test_cli_env_vence_a_pasta_de_ferramentas(tmp_path):
    da_env = _fake_cli(tmp_path / "env", "structurizr.bat")
    _fake_cli(tmp_path / "ferr" / "cli", "structurizr.bat")
    achado = at.localizar_cli(tmp_path / "ferr", env={"STRUCTURIZR_CLI": str(da_env)}, which=_sem_path, windows=True)
    assert achado == da_env


def test_cli_na_pasta_de_ferramentas_vence_o_path(tmp_path):
    cli = _fake_cli(tmp_path / "ferr" / "cli", "structurizr.sh")
    outro = _fake_cli(tmp_path / "bin", "structurizr.sh")
    achado = at.localizar_cli(tmp_path / "ferr", env={}, which=lambda n, path=None: str(outro), windows=False)
    assert achado == cli


def test_cli_pelo_path_falso(tmp_path):
    """PATH falso: sem trocar o which, só uma pasta temporária no PATH (o nome vale para o sistema em que roda)."""
    windows = os.name == "nt"
    nome = "structurizr.bat" if windows else "structurizr.sh"
    cli = _fake_cli(tmp_path / "bin", nome)
    os.chmod(cli, 0o755)
    env = {"PATH": str(tmp_path / "bin")}
    achado = at.localizar_cli(tmp_path / "vazio", env=env, windows=windows)
    assert Path(achado).resolve() == cli.resolve()


def test_cli_ausente_para_com_mensagem_de_instalacao(tmp_path):
    with pytest.raises(at.Falha) as e:
        at.localizar_cli(tmp_path / "vazio", env={"PATH": str(tmp_path / "nada")}, which=_sem_path, windows=False)
    msg = str(e.value)
    assert "structurizr.sh" in msg and "STRUCTURIZR_CLI" in msg and "github.com/structurizr/cli" in msg
    assert e.value.codigo == 1


def test_cli_env_invalido_vira_aviso_e_a_busca_continua(tmp_path, capsys):
    cli = _fake_cli(tmp_path / "ferr" / "cli", "structurizr.bat")
    achado = at.localizar_cli(tmp_path / "ferr", env={"STRUCTURIZR_CLI": str(tmp_path / "nao-existe")},
                              which=_sem_path, windows=True)
    assert achado == cli
    assert "STRUCTURIZR_CLI" in capsys.readouterr().err


def test_dot_vem_do_graphviz_empacotado_ou_do_path(tmp_path):
    assert at.achar_dot(tmp_path / "f", which=lambda n: "/usr/bin/dot", windows=False) == "/usr/bin/dot"
    assert at.achar_dot(tmp_path / "f", which=lambda n: None, windows=False) is None
    emp = tmp_path / "f" / "graphviz" / "bin" / "dot.exe"
    emp.parent.mkdir(parents=True)
    emp.write_text("x", encoding="utf-8")
    assert at.achar_dot(tmp_path / "f", which=lambda n: "/usr/bin/dot", windows=True) == str(emp)


# ------------------------------------------------------------------------------------------------ extensões

def test_reunir_extensoes_do_json_com_bom_e_da_env(tmp_path):
    (tmp_path / "lodemap.json").write_text(json.dumps({"extensoes": ["a.py", "b.py"]}), encoding="utf-8-sig")
    env = {"LODEMAP_EXTENSOES": "c.py;;d.py:e.py"}
    assert at.reunir_extensoes(tmp_path, env=env, windows=True) == ["a.py", "b.py", "c.py", "d.py:e.py"]
    assert at.reunir_extensoes(tmp_path, env=env, windows=False) == ["a.py", "b.py", "c.py", "d.py", "e.py"]
    assert at.reunir_extensoes(tmp_path, env={}, windows=False) == ["a.py", "b.py"]


def test_extensoes_sem_arquivo_de_configuracao_nem_env(tmp_path):
    assert at.reunir_extensoes(tmp_path, env={}) == []


def test_extensao_que_passa_e_extensao_que_falha_vira_aviso(tmp_path, capsys):
    bom = tmp_path / "bom.py"
    bom.write_text(
        "import os, sys, pathlib\n"
        "pathlib.Path(sys.argv[0]).with_suffix('.out').write_text("
        "'|'.join(sys.argv[1:]) + '|' + os.environ.get('LODEMAP_CHECKPOINT', 'SEM'), encoding='utf-8')\n",
        encoding="utf-8")
    ruim = tmp_path / "ruim.py"
    ruim.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
    ws, raiz, repo = tmp_path / "ws.json", tmp_path / "arq", tmp_path / "repo"
    falhas = at.rodar_extensoes([str(ruim), str(tmp_path / "ausente.py"), str(bom)], sys.executable, ws, raiz, repo,
                                "pós ação")
    assert falhas == 2
    err = capsys.readouterr().err
    assert "AVISO" in err and "ruim.py" in err and "código 3" in err and "ausente.py" in err
    assert (tmp_path / "bom.out").read_text(encoding="utf-8") == f"{ws}|--arq|{raiz}|--repo|{repo}|pós ação"


def test_extensao_expande_variavel_de_ambiente(tmp_path, monkeypatch):
    ext = tmp_path / "ext.py"
    ext.write_text("pass\n", encoding="utf-8")
    monkeypatch.setenv("PASTA_EXT", str(tmp_path))
    ref = "%PASTA_EXT%/ext.py" if os.name == "nt" else "$PASTA_EXT/ext.py"
    assert at.rodar_extensoes([ref], sys.executable, tmp_path / "w.json", tmp_path, tmp_path, "") == 0


# ------------------------------------------------------------------------------------------------ ordem das etapas

def _nomes(cmd) -> str:
    """Comando só com o nome final de cada argumento (o caminho do tmp_path traz o nome do teste)."""
    return " ".join(Path(str(c)).name for c in cmd)


class Simulador:
    """Troca subprocess.run: guarda cada chamada e responde com o código programado por trecho do comando."""

    def __init__(self, falhar: dict[str, int] | None = None, relevante: int = 0, topo: str = ""):
        self.chamadas: list[tuple[list[str], dict]] = []
        self.falhar = falhar or {}
        self.relevante = relevante
        self.topo = topo

    def __call__(self, cmd, **kw):
        self.chamadas.append((list(cmd), kw))
        junto = _nomes(cmd)
        if cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, 0, stdout=self.topo + "\n", stderr="")
        if "--relevante" in cmd:
            return subprocess.CompletedProcess(cmd, self.relevante, stdout="", stderr="")
        if "--trabalho" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"semComponente": ["m/novo.py"]}), stderr="")
        for trecho, rc in self.falhar.items():
            if trecho in junto:
                return subprocess.CompletedProcess(cmd, rc, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def etapas(self) -> list[str]:
        """Nome curto de cada chamada, na ordem em que aconteceu."""
        nomes = []
        for cmd, _ in self.chamadas:
            junto = _nomes(cmd)
            for chave in ("validate", "-format json", "gerar_docs", "gerar_leitor", "codegraph_ponte", "gerar_explorador",
                          "-format static", "--marcar", "--relevante", "--trabalho", "rev-parse", "ext_"):
                if chave in junto:
                    nomes.append(chave)
                    break
            else:
                nomes.append(junto)
        return nomes


@pytest.fixture
def projeto(tmp_path, monkeypatch):
    """Pasta de arquitetura mínima, template com as páginas fixas e um CLI de mentira."""
    raiz = tmp_path / "repo" / "docs" / "architecture" / "structurizr"
    scripts = raiz / "scripts"
    scripts.mkdir(parents=True)
    (raiz / "workspace.dsl").write_text("workspace {}\n", encoding="utf-8")
    tpl = tmp_path / "skill" / "templates" / "structurizr"
    for rel in ("explorador/index.html", "leitor/index.html", "explorador/vendor/lib.js", "leitor/vendor/lib.js"):
        (tpl / rel).parent.mkdir(parents=True, exist_ok=True)
        (tpl / rel).write_text("x", encoding="utf-8")
    (tmp_path / "skill" / "scripts").mkdir(parents=True)
    (tmp_path / "skill" / "scripts" / "codegraph_ponte.py").write_text("pass\n", encoding="utf-8")
    cli = _fake_cli(tmp_path / "ferr" / "cli", "structurizr.bat" if os.name == "nt" else "structurizr.sh")
    os.chmod(cli, 0o755)  # sem o bit de execução o atualizar.py antepõe "bash" no Linux e no macOS
    monkeypatch.delenv("LODEMAP_EXTENSOES", raising=False)
    monkeypatch.delenv("STRUCTURIZR_CLI", raising=False)
    return type("P", (), {"raiz": raiz, "scripts": scripts, "tpl": tpl, "cli": cli, "tmp": tmp_path})


def _rodar(projeto, monkeypatch, sim, *args):
    monkeypatch.setattr(at.subprocess, "run", sim)
    base = ["--template", str(projeto.tpl), "--cli", str(projeto.cli), "--ferramentas", str(projeto.tmp / "ferr"),
            "--python", "PY"]
    return at.main([*base, *args], scripts=projeto.scripts)


def test_ordem_das_etapas_no_caminho_padrao(projeto, monkeypatch, capsys):
    sim = Simulador(topo=str(projeto.tmp / "repo"))
    rc = _rodar(projeto, monkeypatch, sim, "--checkpoint", "merge x")
    assert rc == 0
    assert sim.etapas() == ["validate", "-format json", "gerar_docs", "gerar_leitor", "codegraph_ponte", "rev-parse",
                            "gerar_explorador", "--marcar"]
    out = capsys.readouterr().out
    ordem = [out.index(m) for m in ("1/7", "2/7", "3/7", "4/7", "5/7", "6/7 sem extensões", "7/7 site estático fora")]
    assert ordem == sorted(ordem)
    assert "Pronto." in out


def test_argumentos_de_cada_etapa_e_regras_de_subprocesso(projeto, monkeypatch):
    sim = Simulador(topo=str(projeto.tmp / "repo"))
    _rodar(projeto, monkeypatch, sim)
    por_nome = dict(zip(sim.etapas(), sim.chamadas))
    ws = projeto.raiz / ".structurizr" / "export" / "workspace.json"
    cli = str(projeto.cli)
    assert por_nome["validate"][0] == [cli, "validate", "-workspace", str(projeto.raiz / "workspace.dsl")]
    assert por_nome["-format json"][0] == [cli, "export", "-workspace", str(projeto.raiz / "workspace.dsl"), "-format",
                                           "json", "-output", str(projeto.raiz / ".structurizr" / "export")]
    assert por_nome["gerar_docs"][0] == ["PY", str(projeto.scripts / "gerar_docs.py"), str(ws), str(projeto.raiz / "docs")]
    assert por_nome["gerar_leitor"][0][-2:] == [str(ws), str(projeto.raiz / "leitor")]
    assert por_nome["codegraph_ponte"][0][2:] == ["--relacoes", "--arq", str(projeto.raiz)]
    assert por_nome["gerar_explorador"][0][-1] == str(projeto.tmp / "repo")
    assert por_nome["--marcar"][0][2:] == ["--arq", str(projeto.raiz), "--marcar", "--checkpoint-env"]
    for cmd, kw in sim.chamadas:
        assert isinstance(cmd, list) and not kw.get("shell"), cmd
        assert kw.get("encoding") == "utf-8", cmd
    assert (projeto.raiz / ".structurizr" / "export").is_dir()


def test_checkpoint_chega_ao_marcar_pelo_ambiente(projeto, monkeypatch):
    sim = Simulador(topo=str(projeto.tmp / "repo"))
    _rodar(projeto, monkeypatch, sim, "--checkpoint", "pós-merge ação")
    marcar = [kw for cmd, kw in sim.chamadas if "--marcar" in cmd][0]
    assert marcar["env"]["LODEMAP_CHECKPOINT"] == "pós-merge ação"
    assert "pós-merge ação" not in [c for cmd, _ in sim.chamadas for c in cmd]


def test_paginas_fixas_faltantes_vem_do_template(projeto, monkeypatch, capsys):
    (projeto.raiz / "leitor").mkdir()
    (projeto.raiz / "leitor" / "index.html").write_text("do projeto", encoding="utf-8")
    _rodar(projeto, monkeypatch, Simulador(topo=str(projeto.tmp / "repo")))
    assert (projeto.raiz / "leitor" / "index.html").read_text(encoding="utf-8") == "do projeto"
    assert (projeto.raiz / "explorador" / "index.html").is_file()
    assert (projeto.raiz / "explorador" / "vendor" / "lib.js").is_file()
    assert (projeto.raiz / "leitor" / "vendor" / "lib.js").is_file()
    out = capsys.readouterr().out
    assert "copiado do template: explorador/index.html" in out and "copiado do template: leitor/index.html" not in out


def test_extensao_e_site_entram_na_ordem(projeto, monkeypatch, capsys):
    ext = projeto.tmp / "ext_um.py"
    ext.write_text("pass\n", encoding="utf-8")
    (projeto.raiz / "lodemap.json").write_text(json.dumps({"extensoes": [str(ext)]}), encoding="utf-8")
    sim = Simulador(topo=str(projeto.tmp / "repo"))
    assert _rodar(projeto, monkeypatch, sim, "--com-site") == 0
    assert sim.etapas() == ["validate", "-format json", "gerar_docs", "gerar_leitor", "codegraph_ponte", "rev-parse",
                            "gerar_explorador", "ext_", "-format static", "--marcar"]
    chamada_ext = [c for c, _ in sim.chamadas if "ext_um.py" in _nomes(c)][0]
    assert chamada_ext[0] == "PY" and chamada_ext[-4:-2] == ["--arq", str(projeto.raiz)]
    assert "6/7 rodando 1 extensão" in capsys.readouterr().out


def test_sem_extensoes_ignora_json_e_env(projeto, monkeypatch):
    ext = projeto.tmp / "ext_um.py"
    ext.write_text("pass\n", encoding="utf-8")
    (projeto.raiz / "lodemap.json").write_text(json.dumps({"extensoes": [str(ext)]}), encoding="utf-8")
    monkeypatch.setenv("LODEMAP_EXTENSOES", str(ext))
    sim = Simulador(topo=str(projeto.tmp / "repo"))
    assert _rodar(projeto, monkeypatch, sim, "--sem-extensoes") == 0
    assert "ext_" not in sim.etapas()


def test_sem_site_vence_com_site(projeto, monkeypatch):
    sim = Simulador(topo=str(projeto.tmp / "repo"))
    _rodar(projeto, monkeypatch, sim, "--com-site", "--sem-site")
    assert "-format static" not in sim.etapas()


@pytest.mark.parametrize("quebra,ultima,codigo", [
    ("validate", "validate", 1),
    ("-format json", "-format json", 1),
    ("gerar_docs", "gerar_docs", 1),
    ("gerar_leitor", "gerar_leitor", 1),
    ("gerar_explorador", "gerar_explorador", 1),
])
def test_falha_de_etapa_obrigatoria_para_o_pipeline_com_codigo_diferente_de_zero(projeto, monkeypatch, capsys,
                                                                                  quebra, ultima, codigo):
    sim = Simulador(falhar={quebra: 7}, topo=str(projeto.tmp / "repo"))
    rc = _rodar(projeto, monkeypatch, sim)
    assert rc == codigo != 0
    assert sim.etapas()[-1] == ultima
    assert "--marcar" not in sim.etapas()
    assert "ERRO:" in capsys.readouterr().err


def test_falha_de_ponte_site_e_marcar_so_avisa(projeto, monkeypatch, capsys):
    sim = Simulador(falhar={"codegraph_ponte": 1, "-format static": 1, "--marcar": 1}, topo=str(projeto.tmp / "repo"))
    assert _rodar(projeto, monkeypatch, sim, "--com-site") == 0
    err = capsys.readouterr().err
    assert err.count("AVISO") >= 3 and "relacoes" in err and "estático" in err and "estado.json" in err
    assert sim.etapas()[-1] == "--marcar"


def test_incremental_sem_mudanca_sai_com_zero_sem_regenerar(projeto, monkeypatch, capsys):
    sim = Simulador(relevante=1)
    assert _rodar(projeto, monkeypatch, sim, "--incremental") == 0
    assert sim.etapas() == ["--relevante"]
    assert "Nada mudou" in capsys.readouterr().out


def test_incremental_com_mudanca_avisa_modulo_sem_componente_e_segue(projeto, monkeypatch, capsys):
    sim = Simulador(topo=str(projeto.tmp / "repo"))
    assert _rodar(projeto, monkeypatch, sim, "--incremental") == 0
    # o aviso de módulo sem componente sai depois de exportar: antes, o workspace.json ainda é o do modelo anterior
    assert sim.etapas()[:4] == ["--relevante", "validate", "-format json", "--trabalho"]
    assert "m/novo.py" in capsys.readouterr().err


def test_sem_cli_para_antes_de_qualquer_etapa(projeto, monkeypatch, capsys):
    sim = Simulador()
    monkeypatch.setattr(at.subprocess, "run", sim)
    monkeypatch.setattr(at.shutil, "which", lambda *a, **k: None)
    rc = at.main(["--template", str(projeto.tpl), "--ferramentas", str(projeto.tmp / "vazio")], scripts=projeto.scripts)
    assert rc == 1 and sim.chamadas == []
    assert "STRUCTURIZR_CLI" in capsys.readouterr().err


def test_programa_inexistente_vira_erro_e_nao_traceback(projeto, monkeypatch, capsys):
    def explode(cmd, **kw):
        raise FileNotFoundError(2, "No such file", cmd[0])
    monkeypatch.setattr(at.subprocess, "run", explode)
    base = ["--template", str(projeto.tpl), "--cli", str(projeto.cli)]
    assert at.main(base, scripts=projeto.scripts) == 1
    assert "ERRO:" in capsys.readouterr().err


# ------------------------------------------------------------------------------------------------ ponta a ponta

@pytest.mark.skipif(not CLI_REAL or shutil.which("java") is None,
                    reason="Structurizr CLI (~/.structurizr/cli) ou java ausente")
def test_ponta_a_ponta_com_o_structurizr_cli_real(tmp_path):
    repo = tmp_path / "amostra"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "api.py").write_text("from app import store\n\n\ndef rota():\n    return store.ler()\n", encoding="utf-8")
    (repo / "app" / "store.py").write_text("def ler():\n    return 1\n", encoding="utf-8")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)]
    subprocess.run([*git, "init", "-q"], check=True, capture_output=True)
    subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-q", "-m", "inicio"], check=True, capture_output=True)
    novo = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(repo),
                           "--projeto", "Amostra"], capture_output=True, text=True, encoding="utf-8")
    assert novo.returncode == 0, novo.stdout + novo.stderr
    arq = repo / "docs" / "architecture" / "structurizr"
    env = {k: v for k, v in os.environ.items() if k not in ("STRUCTURIZR_CLI", "LODEMAP_EXTENSOES")}
    r = subprocess.run([sys.executable, str(arq / "scripts" / "atualizar.py"), "--template", str(ESTRUTURIZR),
                        "--checkpoint", "teste e2e"], cwd=tmp_path, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert (arq / ".structurizr" / "export" / "workspace.json").is_file()
    assert (arq / "leitor" / "dados.js").is_file() and (arq / "explorador" / "dados.js").is_file()
    evidencias_js = (arq / "explorador" / "evidencias.js").read_text(encoding="utf-8")
    assert evidencias_js.startswith("window.LODEMAP_EVIDENCIAS = ")
    evidencias = json.loads(evidencias_js.split(" = ", 1)[1].rstrip(";\n"))
    assert evidencias["componentes"]
    assert evidencias["referencia"]["commit"]
    assert all(x["cobertura"]["estado"] == "ausente" for x in evidencias["componentes"].values())
    assert all((arq / "explorador" / nome).is_file() for nome in ("saude.js", "linha-do-tempo-ui.js"))
    estado = json.loads((arq / ".lodemap" / "estado.json").read_text(encoding="utf-8"))
    assert estado.get("ultimoCommit") and estado.get("checkpoint") == "teste e2e"
    assert "Pronto." in r.stdout


def test_arquivos_fixos_novos_sem_mudar_interface_customizada(projeto, monkeypatch):
    for nome in ('linha-do-tempo-ui.js', 'saude.js'):
        (projeto.tpl / 'explorador' / nome).write_text('novo ' + nome, encoding='utf8')
    (projeto.raiz / 'explorador').mkdir()
    (projeto.raiz / 'explorador' / 'index.html').write_text('personalizado', encoding='utf8')
    _rodar(projeto, monkeypatch, Simulador(topo=str(projeto.tmp / 'repo')))
    assert (projeto.raiz / 'explorador' / 'index.html').read_text(encoding='utf8') == 'personalizado'
    for nome in ('linha-do-tempo-ui.js', 'saude.js'):
        assert (projeto.raiz / 'explorador' / nome).read_text(encoding='utf8') == 'novo ' + nome


def test_atualizar_interface_cria_backups_unicos(projeto, monkeypatch):
    for rel in ('explorador/index.html', 'leitor/index.html', 'explorador/saude.js', 'explorador/linha-do-tempo-ui.js'):
        destino = projeto.raiz / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text('personalizado ' + rel, encoding='utf8')
        origem = projeto.tpl / rel
        origem.parent.mkdir(parents=True, exist_ok=True)
        origem.write_text('template ' + rel, encoding='utf8')
        (destino.parent / (destino.name + '.lodemap-bak')).write_text('backup antigo', encoding='utf8')
    assert _rodar(projeto, monkeypatch, Simulador(topo=str(projeto.tmp / 'repo')), '--atualizar-interface') == 0
    for rel in ('explorador/index.html', 'leitor/index.html', 'explorador/saude.js', 'explorador/linha-do-tempo-ui.js'):
        destino = projeto.raiz / rel
        assert destino.read_text(encoding='utf8') == 'template ' + rel
        assert (destino.parent / (destino.name + '.lodemap-bak')).read_text(encoding='utf8') == 'backup antigo'
        assert (destino.parent / (destino.name + '.lodemap-bak.1')).read_text(encoding='utf8') == 'personalizado ' + rel


def test_incremental_atualiza_interface_e_copia_arquivos_faltantes(projeto, monkeypatch):
    (projeto.tpl / 'explorador' / 'saude.js').write_text('saude', encoding='utf8')
    sim = Simulador(relevante=1, topo=str(projeto.tmp / 'repo'))
    assert _rodar(projeto, monkeypatch, sim, '--incremental') == 0
    assert (projeto.raiz / 'explorador' / 'saude.js').read_text(encoding='utf8') == 'saude'
    assert sim.etapas() == ['--relevante']


def test_atualizar_interface_vence_incremental_sem_mudanca(projeto, monkeypatch):
    sim = Simulador(relevante=1, topo=str(projeto.tmp / 'repo'))
    assert _rodar(projeto, monkeypatch, sim, '--incremental', '--atualizar-interface') == 0
    assert 'validate' in sim.etapas() and '--relevante' not in sim.etapas()


def test_evidencias_opcional_apos_gerar_explorador(projeto, monkeypatch):
    evidencia = projeto.tmp / 'skill' / 'scripts' / 'evidencias.py'
    evidencia.write_text('pass\n', encoding='utf8')
    sim = Simulador(topo=str(projeto.tmp / 'repo'))
    assert _rodar(projeto, monkeypatch, sim) == 0
    indice = next(i for i, (cmd, _) in enumerate(sim.chamadas) if str(evidencia) in cmd)
    assert sim.etapas().index('gerar_explorador') < indice
    cmd = sim.chamadas[indice][0]
    assert cmd[2:] == ['--repositorio', str(projeto.tmp / 'repo'), '--mapa', str(projeto.raiz)]


def test_falha_evidencias_so_avisa(projeto, monkeypatch, capsys):
    (projeto.tmp / 'skill' / 'scripts' / 'evidencias.py').write_text('pass\n', encoding='utf8')
    sim = Simulador(falhar={'evidencias.py': 2}, topo=str(projeto.tmp / 'repo'))
    assert _rodar(projeto, monkeypatch, sim) == 0
    assert 'evidência' in capsys.readouterr().err.lower()
