# Arquivos e scripts da skill

Referência completa. O `SKILL.md` cita só os comandos de cada passo.

## Na skill (`~/.claude/skills/lodemap/`)

| Arquivo | Para quê |
|---|---|
| `scripts/novo_mapa.py` | copia os templates para o repositório e preenche os marcadores; sem `--raiz-codigo` detecta a raiz do código (pasta convencional com código, senão a raiz do repositório) e escreve os globs de `modulos` e de `ignorar` da linguagem dominante |
| `scripts/inventario.py` | cada módulo dos globs, quem o cobre (ou FORA), resumo e importadores; `--json` grava a base do `inventario.json` |
| `scripts/verificar.py` | checagem final: `node --check`, explorador abrindo sem erro de JS e, com `--qualidade`, o gate do `qualidade.py` |
| `scripts/qualidade.py` | rubrica objetiva do modelo (nota 0 a 100 por critério e total) contra `references/baseline-qualidade.json`; `--listar-reprovados` |
| `scripts/codegraph_ponte.py` | arestas código → código (CodeGraph em leitura, ou `ast`): `--inventario`, `--relacoes`, `--impacto`; zero token |
| `references/baseline-qualidade.json` | notas por critério da linha de base (o primeiro mapa que a skill gerou); o gate compara com ela |
| `references/exemplos-estilo.md` | few-shot do estilo da casa (componentes, relações, fluxo), com projeto fictício |
| `templates/structurizr/` | a pasta da arquitetura: `workspace.dsl` esqueleto, `model/`, `views/` (estilos e tags de status), `scripts/`, `explorador/index.html` (+ `vendor/`), `leitor/index.html` (+ `vendor/`), `metricas/`, `docs/`, `adrs/` (ADR modelo no formato único), `lodemap.json`, `.gitignore` |
| `templates/tests/` | `test_arquitetura_cobertura.py`, `test_arquitetura_metricas.py`, `test_lodemap_diff.py`, `test_adrs_formato.py`, `test_leitor_gerador.py` e `test_barra_comum.py`, genéricos |
| `lodemap/` (`python -m lodemap`) | CLI única: `instalar`, `reverter`, `status`, `plano`, `consentir`, `revogar`, `verificar`, `doctor`; `--version` |
| `hooks/` | `aviso_lodemap.py`, o aviso único do perfil `padrao` do instalador (só biblioteca padrão) |
| `references/custo-equivalente.json` | modelo de custo medido (preços e rodadas) que o `plano` usa |
| `references/modelagem-c4.md` | níveis, como cortar componentes, relações, visões, fluxos, status, tags, formato das métricas |
| `scripts/esqueleto.py` | `rascunho` (decisões em JSON, com impressão digital semântica por módulo) , `pendencias` (o mesmo cálculo do rascunho, sem gravar nada: é o que o `lodemap_decidir.py` consulta) e `renderizar` (escreve o DSL e as visões estáticas) |
| `scripts/descrever.py` | rota enxuta: nome, descrição e área dos componentes pendentes numa chamada `claude -p` (Haiku medium); módulo a revisar mantém nome e área e só troca a frase se ela ficou falsa; `--resumo` imprime uma linha, `--todos` refaz do zero |

## No projeto (`<arq>/scripts/`)

Scripts que vão para `<arq>/scripts/` (só biblioteca padrão do Python, 3.11 ou mais; os `.py` rodam em Windows, Linux e macOS; os `.ps1` são invólucros finos para o Windows):

| Script | Faz |
|---|---|
| `atualizar.py` | o caminho em qualquer sistema (Windows, Linux e macOS). Copia do template as páginas fixas que faltarem (explorador e `vendor/`, leitor e `vendor/`); valida, exporta, gera documentos, o leitor, atualiza o `relacoes-codigo.json` (a prova no código, sem modelo) e gera o `dados.js` do explorador; extensões locais (scripts do dono fora do repositório, em `"extensoes"` do `lodemap.json` ou `LODEMAP_EXTENSOES`; `-SemExtensoes` pula) e site estático só com `--com-site`; `--incremental`, `--checkpoint`, `--python`, `--ferramentas`, `--template`, `--cli` (`--sem-site` fica por compatibilidade). Acha o Structurizr CLI em `--cli`, `STRUCTURIZR_CLI`, `<ferramentas>/cli` e no PATH (`structurizr.bat` no Windows, `structurizr.sh` nos outros); o `dot` vem do Graphviz empacotado ou do PATH |
| `atualizar.ps1` | invólucro fino para o Windows: chama o `atualizar.py` com os mesmos parâmetros em PowerShell (`-Incremental`, `-Checkpoint`, `-ComSite`, `-SemExtensoes`, `-SemSite`, `-Python`, `-Ferramentas`, `-Template`) |
| `ver_arquitetura.py` | o caminho em qualquer sistema: atualiza os dados se os arquivos-fonte estão mais novos que o `dados.js`, sobe o explorador e o leitor em http e abre o explorador; `--abrir explorador\|leitor\|lite\|ambos`, `--com-lite` (o Lite só sobe com ele), `--porta`, `--porta-explorador`, `--sem-navegador`, `--ferramentas`, `--python` |
| `ver-arquitetura.ps1` | invólucro fino para o Windows: chama o `ver_arquitetura.py` com os mesmos parâmetros em PowerShell (`-Abrir`, `-ComLite`, `-Porta`, `-PortaExplorador`, `-SemNavegador`, `-Ferramentas`, `-Python`) |
| `arq_comum.py` | leitura do workspace, da configuração e das métricas; nomes e caminhos das notas |
| `gerar_docs.py` | `docs/02-mapa-de-status.md`, `90-catalogo-de-observabilidade.md`, `91-metricas-e-benchmarks.md` e o índice `92-indice-de-decisoes.md` (resumo no topo, nomes com link para o mapa) |
| `gerar_leitor.py` | `leitor/dados.js` a partir de `docs/*.md` e `adrs/*.md` (Markdown renderizado em Python, sem dependência); também o leitor e o validador do formato único de ADR |
| `gerar_explorador.py` | `explorador/dados.js` |
| `lodemap_diff.py` | diff desde `ultimoCommit`: `modulosNovos`, `modulosMudados`, `modulosRemovidos`, `componentesAfetados`, `semComponente`; `--relevante`; `--marcar` |
| `lodemap_decidir.py` | quando atualizar, sem token: mede a dívida do mapa e responde `nada`, `scripts`, `adiar`, `descrever`, `modelar` ou `gerar`, com motivos e o próximo comando; `--resumo`; `--adiar` (grava `pendentes.json`); `--gancho` (o que o gancho pergunta) |
| `lodemap_gancho.py` | o que os ganchos do git chamam (decide rápido e dispara o `atualizar.py` com o mesmo Python, em segundo plano; sem PowerShell) |
| `instalar_gancho.py` | o caminho em qualquer sistema: instala ou remove (opt-in) o `post-commit` e o `post-merge`; `--python`, `--ferramentas`, `--remover`, `--forcar` |
| `instalar-gancho.ps1` | invólucro fino para o Windows: chama o `instalar_gancho.py` (`-Python`, `-Ferramentas`, `-Remover`, `-Forcar`) |
| `enriquecer.groovy` | perspectivas, link do GitHub e passos de animação no Lite |
