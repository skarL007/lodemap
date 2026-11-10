"""Contrato das evidências apresentado pela interface, sem exigir navegador instalado."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAUDE = ROOT / 'templates/structurizr/explorador/saude.js'


def test_saude_distingue_ausencia_zero_e_referencia_sem_inventar_execucao():
    node = shutil.which('node')
    if not node:
        pytest.skip('node não instalado')
    js = r'''
const fs = require('fs');
global.window = {LODEMAP_EVIDENCIAS:{referencia:{data:'2026-01-01',commit:'abc',arvore_de_trabalho:'nao_verificada'},componentes:{
  zero:{testes:{estado:'medido',arquivos:[]},cobertura:{estado:'ausente'},junit:{estado:'ausente'},git:{commits_30_dias:0,commits_90_dias:0}},
  refs:{testes:{estado:'medido',arquivos:['tests/t.py']},cobertura:{estado:'sem_dados'},junit:{estado:'sem_dados'},git:{}}}}};
eval(fs.readFileSync(process.argv[1], 'utf8'));
(async()=>{const s=window.LodemapSaude;await s.carregar();s.referencia('def');
 const e={ident:'zero',props:{status:'Pronto'}};
 console.log(JSON.stringify({zero:s.estado(e),refs:s.estado({ident:'refs'}),ausente:s.estado({ident:'sem'}),texto:s.texto(e)}));})();
'''
    r = subprocess.run([node, '-e', js, str(SAUDE)], capture_output=True, text=True, encoding='utf-8', check=True)
    dados = json.loads(r.stdout)
    assert (dados['zero'], dados['refs'], dados['ausente']) == ('sem_referencia', 'referenciado', 'desconhecido')
    assert '0 arquivo(s)' in dados['texto'] and 'Divergência' in dados['texto']
    assert 'não comprovam execução' in dados['texto'] and 'árvore de trabalho não verificada' in dados['texto']
    assert 'difere' in dados['texto'] and 'Cobertura: ausente' in dados['texto']
