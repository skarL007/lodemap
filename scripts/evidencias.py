"""Coleta evidências locais para o explorador, sem inferir estado de prontidão.

Uso: python evidencias.py --repositorio DIR --mapa DIR [--cobertura RELATORIO]
                         [--junit RELATORIO] [--data-referencia AAAA-MM-DD] [--json]

Os caminhos em dados.js e nos relatórios são relativos à raiz do código. Testes são
referências estáticas, não prova de execução. JUnit só é associado por atributo file.
A data de referência inclui o dia inteiro em UTC. A árvore de trabalho pode ter
alterações não commitadas; o commit identifica apenas a base Git, não os relatórios.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'templates' / 'structurizr' / 'scripts'))
from arq_comum import caminhos_do_codigo  # noqa: E402


def relativo(path, raiz):
    try:
        return path.resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return None


def seguro(valor, raiz):
    valor = str(valor).replace('\\', '/')
    p = Path(valor)
    if PureWindowsPath(valor).is_absolute() and not p.is_absolute():
        return None
    if not p.is_absolute():
        p = raiz / p
    rel = relativo(p, raiz)
    return rel if rel and rel != '.' else None


def git(raiz, *args):
    env = dict(os.environ)
    for chave in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(chave, None)
    try:
        r = subprocess.run(['git', '--literal-pathspecs', *args], cwd=raiz, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return r.stdout.strip() if r.returncode == 0 else None
    except OSError:
        return None


def carregar_mapa(caminho):
    texto = caminho.read_text(encoding='utf-8-sig')
    m = re.search(r'window\.ARQ\s*=\s*', texto)
    if not m:
        raise ValueError('dados.js não contém window.ARQ')
    obj, _ = json.JSONDecoder().raw_decode(texto, m.end())
    if not isinstance(obj, dict) or not isinstance(obj.get('elementos'), list):
        raise ValueError('dados.js não contém lista de elementos')
    return obj


def normalizar_codigo(codigo, raiz):
    if not isinstance(codigo, str) or not codigo.strip():
        return []
    normalizados = []
    for parte in caminhos_do_codigo(codigo.replace('\\', '/')):
        if '..' in PurePosixPath(parte).parts:
            continue
        rel = seguro(parte, raiz)
        if rel:
            normalizados.append(rel)
    return normalizados


def arquivos_codigo(caminhos, raiz):
    achados = set()
    for parte in caminhos:
        try:
            candidatos = raiz.glob(parte) if any(c in parte for c in '*?[') else [raiz / parte]
            for p in candidatos:
                if p.is_dir():
                    candidatos_filhos = p.rglob('*')
                else:
                    candidatos_filhos = [p]
                for filho in candidatos_filhos:
                    rel = relativo(filho, raiz)
                    if rel and filho.is_file() and '.git' not in PurePosixPath(rel).parts:
                        achados.add(rel)
        except (OSError, ValueError):
            continue
    return sorted(achados)


def arquivos_teste(raiz):
    saida = []
    for atual, dirs, files in os.walk(raiz, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build', 'coverage'})
        for nome in sorted(files):
            p = Path(atual) / nome
            rel = relativo(p, raiz)
            if not rel:
                continue
            partes = PurePosixPath(rel).parts
            if (any(x.lower() in {'test', 'tests', '__tests__', 'spec', 'specs'} for x in partes[:-1]) or
                    re.search(r'(^test_|_test\.|\.test\.|\.spec\.|_spec\.)', nome, re.I)):
                try:
                    saida.append((rel, p.read_text(encoding='utf-8', errors='replace')))
                except OSError:
                    pass
    return saida


def referencia_teste(rel_teste, texto, arquivos):
    # Importações Python são nomes de módulos; citações de caminhos exigem limites.
    modulos = set()
    if rel_teste.endswith('.py'):
        try:
            for no in ast.walk(ast.parse(texto)):
                if isinstance(no, ast.Import):
                    modulos.update(x.name for x in no.names)
                elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
                    modulos.add(no.module)
                    modulos.update(no.module + '.' + x.name for x in no.names if x.name != '*')
        except SyntaxError:
            pass
    for caminho in arquivos:
        modulo = str(PurePosixPath(caminho).with_suffix('')).replace('/', '.')
        if modulo in modulos:
            return True
        base = PurePosixPath(rel_teste).parent
        try:
            relativo_teste = os.path.relpath(caminho, str(base)).replace('\\', '/')
        except ValueError:
            relativo_teste = caminho
        candidatos = {caminho, relativo_teste, './' + relativo_teste}
        candidatos |= {str(PurePosixPath(x).with_suffix('')) for x in list(candidatos)}
        for candidato in candidatos:
            if '/' not in candidato and not candidato.startswith('.'):
                continue
            if re.search(r'(?<![\w./-])' + re.escape(candidato) + r'(?![\w./-])', texto):
                return True
    return False


def cobertura_lcov(path, raiz):
    registros, atual = {}, None
    for linha in path.read_text(encoding='utf-8-sig').splitlines():
        if linha.startswith('SF:'):
            atual = seguro(linha[3:], raiz)
            if atual:
                registros.setdefault(atual, {})
        elif linha.startswith('DA:') and atual:
            partes = linha[3:].split(',')
            numero, hits = int(partes[0]), int(partes[1])
            registros[atual][numero] = max(hits, registros[atual].get(numero, 0))
        elif linha == 'end_of_record':
            atual = None
    return registros


def cobertura_xml(path, raiz):
    tree = ET.parse(path)
    fontes = [x.text for x in tree.findall('.//sources/source') if x.text] or ['.']
    registros = {}
    for classe in tree.findall('.//class'):
        nome = classe.get('filename')
        if not nome:
            continue
        candidatos = [seguro(str(Path(fonte) / nome), raiz) for fonte in fontes] + [seguro(nome, raiz)]
        rel = next((x for x in candidatos if x and (raiz / x).is_file()), None)
        if not rel:
            continue
        linhas = registros.setdefault(rel, {})
        for linha in classe.findall('./lines/line'):
            numero, hits = int(linha.attrib['number']), int(linha.attrib['hits'])
            linhas[numero] = max(hits, linhas.get(numero, 0))
    return registros


def carregar_junit(path, raiz):
    falhas, arquivos = {}, set()
    for caso in ET.parse(path).iter('testcase'):
        arquivo = caso.get('file')
        falha = caso.find('failure')
        if falha is None:
            falha = caso.find('error')
        rel = seguro(arquivo, raiz) if arquivo else None
        if rel:
            arquivos.add(rel)
        if rel and falha is not None:
            falhas.setdefault(rel, []).append({'arquivo': rel, 'nome': caso.get('name', ''), 'tipo': falha.tag})
    return falhas, arquivos


def historico(raiz, arquivos, referencia, tem_git):
    vazio = {'commits_30_dias': None, 'commits_90_dias': None, 'ultima_mudanca': None}
    if not arquivos or not tem_git:
        return vazio
    saida = git(raiz, 'log', '--format=%cI', '--', *arquivos)
    if saida is None:
        return vazio
    fim = datetime.combine(referencia + timedelta(days=1), time.min, tzinfo=timezone.utc)
    datas = []
    for linha in saida.splitlines():
        d = datetime.fromisoformat(linha)
        if d < fim:
            datas.append(d)
    return {'commits_30_dias': sum(fim - timedelta(days=30) <= d < fim for d in datas),
            'commits_90_dias': sum(fim - timedelta(days=90) <= d < fim for d in datas),
            'ultima_mudanca': max(datas).isoformat() if datas else None}


def gerar(raiz, mapa, cobertura, junit, referencia):
    arq = carregar_mapa(mapa / 'explorador' / 'dados.js')
    topo = git(raiz, 'rev-parse', '--show-toplevel')
    tem_git = bool(topo and Path(topo).resolve() == raiz.resolve())
    commit = git(raiz, 'rev-parse', 'HEAD') if tem_git else None
    testes = arquivos_teste(raiz)
    cob = (cobertura_xml(cobertura, raiz) if cobertura.suffix.lower() == '.xml' else cobertura_lcov(cobertura, raiz)) if cobertura else {}
    falhas, arquivos_junit = carregar_junit(junit, raiz) if junit else ({}, set())
    resultado = {}
    for elemento in arq['elementos']:
        if not isinstance(elemento, dict) or elemento.get('tipo') not in ('Component', 'Componente'):
            continue
        props = elemento.get('props') or {}
        ident = elemento.get('ident') or props.get('structurizr.dsl.identifier')
        chave = str(ident or elemento.get('id'))
        if chave in resultado:
            raise ValueError(f'identificador duplicado: {chave}')
        caminhos = normalizar_codigo(props.get('codigo'), raiz)
        codigo = ', '.join(caminhos) or None
        arquivos = arquivos_codigo(caminhos, raiz)
        associados = [rel for rel, texto in testes if referencia_teste(rel, texto, arquivos)]
        medidas = []
        for nome in arquivos:
            if nome in cob:
                linhas = cob[nome]
                total = len(linhas)
                cobertas = sum(x > 0 for x in linhas.values())
                medidas.append({'arquivo': nome, 'linhas_cobertas': cobertas, 'linhas_total': total,
                                'percentual': round(100 * cobertas / total, 2) if total else None})
        estado = 'medido' if arquivos else 'desconhecido'
        resultado[chave] = {'id': str(elemento.get('id')), 'ident': ident, 'codigo': codigo, 'arquivos': arquivos,
            'testes': {'estado': estado, 'arquivos': associados},
            'cobertura': {'estado': ('ausente' if not cobertura else 'desconhecido' if not arquivos else 'medido' if medidas else 'sem_dados'),
                          'relatorio': seguro(cobertura, raiz) if cobertura else None, 'arquivos': medidas},
            'git': historico(raiz, arquivos, referencia, tem_git),
            'junit': {'estado': ('ausente' if not junit else 'desconhecido' if not arquivos else
                                 'medido' if arquivos_junit.intersection(associados) else 'sem_dados'),
                      'relatorio': seguro(junit, raiz) if junit else None,
                      'falhas': [f for teste in associados for f in falhas.get(teste, [])]}}
    return {'versao': 1, 'referencia': {'data': referencia.isoformat(), 'commit': commit,
            'repositorio': raiz.name, 'mapa': relativo(mapa, raiz), 'arvore_de_trabalho': 'nao_verificada'},
            'componentes': resultado}


def main():
    parser = argparse.ArgumentParser(description='Coleta evidências locais por componente, sem modelo.')
    parser.add_argument('--repositorio', type=Path, required=True, help='Raiz do código')
    parser.add_argument('--mapa', type=Path, required=True, help='Pasta do mapa')
    parser.add_argument('--cobertura', type=Path, help='Relatório lcov.info ou coverage.xml')
    parser.add_argument('--junit', type=Path, help='Relatório JUnit XML')
    parser.add_argument('--data-referencia', type=date.fromisoformat, default=datetime.now(timezone.utc).date(), help='Data UTC AAAA-MM-DD')
    parser.add_argument('--json', action='store_true', help='Grava também evidencias.json')
    args = parser.parse_args()
    try:
        raiz, mapa = args.repositorio.resolve(), args.mapa.resolve()
        if not raiz.is_dir() or not mapa.is_dir():
            raise ValueError('repositório ou mapa inexistente')
        for nome in ('cobertura', 'junit'):
            path = getattr(args, nome)
            if path:
                resolvido = (path if path.is_absolute() else raiz / path).resolve()
                if seguro(resolvido, raiz) is None or not resolvido.is_file():
                    setattr(args, nome, None)
                else:
                    setattr(args, nome, resolvido)
        dados = gerar(raiz, mapa, args.cobertura, args.junit, args.data_referencia)
        conteudo = json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
        destino = mapa / 'explorador' / 'evidencias.js'
        destino.write_text('window.LODEMAP_EVIDENCIAS = ' + conteudo.rstrip() + ';\n', encoding='utf-8')
        if args.json:
            destino.with_suffix('.json').write_text(conteudo, encoding='utf-8')
        print(f'Evidências geradas: {destino} ({len(dados["componentes"])} componentes)')
        return 0
    except (OSError, ValueError, ET.ParseError, json.JSONDecodeError) as erro:
        print(f'Erro: {erro}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
