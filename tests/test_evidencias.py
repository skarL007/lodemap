import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'evidencias.py'


def run(*args, cwd, env=None, check=True):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=check)


@pytest.fixture
def repo(tmp_path):
    run('git', 'init', '-q', cwd=tmp_path)
    run('git', 'config', 'user.email', 'test@example.org', cwd=tmp_path)
    run('git', 'config', 'user.name', 'Teste', cwd=tmp_path)
    (tmp_path / 'src').mkdir()
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'mapa' / 'explorador').mkdir(parents=True)
    (tmp_path / 'src' / 'alpha.py').write_text('def f(): return 1\n')
    (tmp_path / 'src' / 'beta.py').write_text('def g(): return 2\n')
    (tmp_path / 'tests' / 'test_alpha.py').write_text('from src.alpha import f\n')
    obj = {'elementos': [
        {'id': '1', 'ident': 'alpha', 'nome': 'Alpha', 'tipo': 'Componente', 'props': {'codigo': 'src/alpha.py', 'status': 'Pronto'}},
        {'id': '2', 'ident': 'beta', 'nome': 'Beta', 'tipo': 'Componente', 'props': {'codigo': 'src/beta.py'}},
        {'id': '3', 'ident': 'sem_codigo', 'nome': 'Outro', 'tipo': 'Componente', 'props': {}},
    ], 'relacoes': [], 'visoes': []}
    (tmp_path / 'mapa' / 'explorador' / 'dados.js').write_text('window.ARQ = ' + json.dumps(obj) + ';', encoding='utf8')
    env = os.environ.copy()
    env.update(GIT_AUTHOR_DATE='2026-10-15T12:00:00+00:00', GIT_COMMITTER_DATE='2026-10-15T12:00:00+00:00')
    run('git', 'add', '.', cwd=tmp_path)
    run('git', 'commit', '-qm', 'primeiro', cwd=tmp_path, env=env)
    return tmp_path


def gerar(repo, *extra):
    r = run(os.environ.get('PYTHON_TEST_EXE', __import__('sys').executable), str(SCRIPT), '--repositorio', str(repo), '--mapa', str(repo / 'mapa'), '--data-referencia', '2026-11-10', *extra, cwd=repo, check=False)
    assert r.returncode == 0, r.stderr
    texto = (repo / 'mapa' / 'explorador' / 'evidencias.js').read_text(encoding='utf8')
    assert texto.startswith('window.LODEMAP_EVIDENCIAS = ')
    return json.loads(texto.split(' = ', 1)[1].rstrip(';\n'))


def test_git_testes_e_ausencias(repo):
    d = gerar(repo)
    a, b, c = (d['componentes'][x] for x in ('alpha', 'beta', 'sem_codigo'))
    assert a['testes']['arquivos'] == ['tests/test_alpha.py']
    assert b['testes']['arquivos'] == []
    assert a['git']['commits_30_dias'] == 1
    assert a['git']['commits_90_dias'] == 1
    assert a['git']['ultima_mudanca'].startswith('2026-10-15')
    assert a['cobertura']['estado'] == 'ausente'
    assert a['junit']['estado'] == 'ausente'
    assert c['git']['commits_30_dias'] is None
    assert c['testes']['estado'] == 'desconhecido'
    assert d['referencia']['commit'] == run('git', 'rev-parse', 'HEAD', cwd=repo).stdout.strip()
    assert str(repo) not in json.dumps(d)
    antes = (repo / 'mapa' / 'explorador' / 'evidencias.js').read_bytes()
    gerar(repo)
    assert antes == (repo / 'mapa' / 'explorador' / 'evidencias.js').read_bytes()


def test_lcov_e_junit_correlacionado_por_arquivo(repo):
    (repo / 'lcov.info').write_text('TN:\nSF:src/alpha.py\nDA:1,1\nDA:2,0\nend_of_record\n')
    (repo / 'junit.xml').write_text('<testsuite><testcase file="tests/test_alpha.py" name="test_f"><failure message="erro"/></testcase><testcase name="sem_caminho"><failure/></testcase></testsuite>')
    d = gerar(repo, '--cobertura', str(repo / 'lcov.info'), '--junit', str(repo / 'junit.xml'))
    a, b = d['componentes']['alpha'], d['componentes']['beta']
    assert a['cobertura']['arquivos'][0]['linhas_cobertas'] == 1
    assert a['cobertura']['arquivos'][0]['linhas_total'] == 2
    assert a['cobertura']['arquivos'][0]['percentual'] == 50.0
    assert b['cobertura']['estado'] == 'sem_dados'
    assert [x['nome'] for x in a['junit']['falhas']] == ['test_f']
    assert b['junit']['falhas'] == []
    assert a['junit']['relatorio'] == 'junit.xml'


def test_cobertura_xml_e_repositorio_sem_testes(repo):
    (repo / 'tests' / 'test_alpha.py').unlink()
    (repo / 'coverage.xml').write_text('<coverage><sources><source>.</source></sources><packages><package><classes><class filename="src/alpha.py"><lines><line number="1" hits="2"/><line number="2" hits="0"/></lines></class></classes></package></packages></coverage>')
    d = gerar(repo, '--cobertura', str(repo / 'coverage.xml'))
    a = d['componentes']['alpha']
    assert a['testes']['arquivos'] == []
    assert a['cobertura']['arquivos'][0]['percentual'] == 50.0
    assert a['cobertura']['relatorio'] == 'coverage.xml'


def test_caminho_ausente_nao_gera_zero(repo):
    (repo / 'src' / 'beta.py').unlink()
    b = gerar(repo)['componentes']['beta']
    assert b['testes']['estado'] == 'desconhecido'
    assert b['git']['commits_30_dias'] is None


def test_junit_sem_correlacao_nao_declara_sucesso(repo):
    (repo / 'junit.xml').write_text('<testsuite><testcase name="sem_caminho"><failure/></testcase></testsuite>')
    d = gerar(repo, '--junit', str(repo / 'junit.xml'))
    assert d['componentes']['alpha']['junit']['estado'] == 'sem_dados'
    assert d['componentes']['alpha']['junit']['falhas'] == []


def test_sem_git_e_caminho_literal(repo):
    sem_git = repo / 'solto'
    (sem_git / 'mapa' / 'explorador').mkdir(parents=True)
    (sem_git / 'src').mkdir()
    (sem_git / 'src' / 'a.py').write_text('pass')
    obj = {'elementos': [{'id': '1', 'ident': 'a', 'nome': 'A', 'tipo': 'Componente', 'props': {'codigo': 'src/a.py'}}]}
    (sem_git / 'mapa' / 'explorador' / 'dados.js').write_text('window.ARQ = ' + json.dumps(obj) + ';')
    dados = gerar(sem_git)
    assert dados['referencia']['commit'] is None
    assert dados['componentes']['a']['git']['commits_30_dias'] is None


def test_datas_futuras_excluidas(repo):
    env = os.environ.copy()
    env.update(GIT_AUTHOR_DATE='2026-11-11T12:00:00+00:00', GIT_COMMITTER_DATE='2026-11-11T12:00:00+00:00')
    (repo / 'src' / 'alpha.py').write_text('def f(): return 2\n')
    run('git', 'add', 'src/alpha.py', cwd=repo)
    run('git', 'commit', '-qm', 'futuro', cwd=repo, env=env)
    a = gerar(repo)['componentes']['alpha']
    assert a['git']['commits_30_dias'] == 1
    assert a['git']['ultima_mudanca'].startswith('2026-10-15')


def alterar_codigo(repo, codigo, tipo=None):
    arquivo = repo / 'mapa' / 'explorador' / 'dados.js'
    obj = json.loads(arquivo.read_text(encoding='utf8').split(' = ', 1)[1].rstrip(';'))
    obj['elementos'][0]['props']['codigo'] = codigo
    if tipo:
        obj['elementos'][0]['tipo'] = tipo
    arquivo.write_text('window.ARQ = ' + json.dumps(obj) + ';', encoding='utf8')


def test_formato_real_componente_portugues(repo):
    alterar_codigo(repo, 'src/alpha.py', 'Componente')
    assert gerar(repo)['componentes']['alpha']['arquivos'] == ['src/alpha.py']


def test_cobertura_xml_respeita_source_antes_da_raiz(repo):
    (repo / 'alpha.py').write_text('pass')
    (repo / 'coverage.xml').write_text('<coverage><sources><source>src</source></sources><packages><package><classes><class filename="alpha.py"><lines><line number="1" hits="1"/></lines></class></classes></package></packages></coverage>')
    alpha = gerar(repo, '--cobertura', str(repo / 'coverage.xml'))['componentes']['alpha']
    assert alpha['cobertura']['arquivos'][0]['arquivo'] == 'src/alpha.py'


def test_codigo_compacto_herda_pasta(repo):
    alterar_codigo(repo, 'src/alpha.py, beta.py')
    assert gerar(repo)['componentes']['alpha']['arquivos'] == ['src/alpha.py', 'src/beta.py']


def test_importacao_python_por_pacote(repo):
    (repo / 'tests' / 'test_alpha.py').write_text('from src import alpha\n')
    assert gerar(repo)['componentes']['alpha']['testes']['arquivos'] == ['tests/test_alpha.py']


def test_codigo_externo_omitido_e_caminho_interno_normalizado(repo):
    alterar_codigo(repo, f'{repo.as_posix()}/src/alpha.py, C:/Users/private/project/secret.py')
    dados = gerar(repo)
    registro = dados['componentes']['alpha']
    assert registro['codigo'] == 'src/alpha.py'
    assert registro['arquivos'] == ['src/alpha.py']
    assert 'private' not in json.dumps(dados)
    assert repo.as_posix() not in json.dumps(dados)


def test_relatorio_externo_e_descartado(repo, tmp_path_factory):
    externo = tmp_path_factory.mktemp('externo') / 'coverage.xml'
    externo.write_text('não deve ser lido')
    assert gerar(repo, '--cobertura', str(externo))['componentes']['alpha']['cobertura']['estado'] == 'ausente'

@pytest.mark.parametrize('nome,opcao,chave', [
    ('coverage.xml', '--cobertura', 'cobertura'), ('junit.xml', '--junit', 'junit')])
def test_relatorio_relativo_nao_le_arquivo_do_diretorio_corrente(repo, tmp_path_factory, nome, opcao, chave):
    fora = tmp_path_factory.mktemp('cwd-externo')
    if chave == 'cobertura':
        conteudo = '<coverage><packages><package><classes><class filename="src/alpha.py"><lines><line number="1" hits="1"/></lines></class></classes></package></packages></coverage>'
    else:
        conteudo = '<testsuite><testcase file="tests/test_alpha.py" name="exterior"><failure/></testcase></testsuite>'
    (fora / nome).write_text(conteudo, encoding='utf-8')
    r = run(__import__('sys').executable, str(SCRIPT), '--repositorio', str(repo), '--mapa', str(repo / 'mapa'),
            '--data-referencia', '2026-11-10', opcao, nome, cwd=fora, check=False)
    assert r.returncode == 0, r.stderr
    texto = (repo / 'mapa' / 'explorador' / 'evidencias.js').read_text(encoding='utf-8')
    registro = json.loads(texto.split(' = ', 1)[1].rstrip(';\n'))['componentes']['alpha'][chave]
    assert registro['estado'] == 'ausente'
    assert registro['relatorio'] is None


def test_relatorio_relativo_usa_raiz_do_repositorio(repo, tmp_path_factory):
    fora = tmp_path_factory.mktemp('cwd-externo-interno')
    (fora / 'coverage.xml').write_text('não deve ser lido', encoding='utf-8')
    (repo / 'coverage.xml').write_text('<coverage><packages><package><classes><class filename="src/alpha.py"><lines><line number="1" hits="0"/></lines></class></classes></package></packages></coverage>', encoding='utf-8')
    r = run(__import__('sys').executable, str(SCRIPT), '--repositorio', str(repo), '--mapa', str(repo / 'mapa'),
            '--data-referencia', '2026-11-10', '--cobertura', 'coverage.xml', cwd=fora, check=False)
    assert r.returncode == 0, r.stderr
    texto = (repo / 'mapa' / 'explorador' / 'evidencias.js').read_text(encoding='utf-8')
    cob = json.loads(texto.split(' = ', 1)[1].rstrip(';\n'))['componentes']['alpha']['cobertura']
    assert cob['relatorio'] == 'coverage.xml' and cob['arquivos'][0]['percentual'] == 0
