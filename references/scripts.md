# Arquivos e scripts da skill

Referência completa. O `SKILL.md` cita só os comandos de cada passo.

Os comandos também podem partir de um checkout local do Lodemap. `~/.claude/skills/lodemap/` é o caminho da
integração empacotada com Claude Code, não um requisito dos coletores de observabilidade. No Codex, o agente nativo
pode preencher as decisões JSON; `descrever.py` continua sendo um helper opcional com Claude CLI.

## Na skill (`~/.claude/skills/lodemap/` ou checkout local)

| Arquivo | Para quê |
|---|---|
| `scripts/novo_mapa.py` | copia os templates para o repositório e preenche os marcadores; sem `--raiz-codigo` detecta a raiz do código (pasta convencional com código, senão a raiz do repositório) e escreve os globs de `modulos` e de `ignorar` da linguagem dominante |
| `scripts/inventario.py` | cada módulo dos globs, quem o cobre (ou FORA), resumo e importadores; `--json` grava a base do `inventario.json` |
| `scripts/verificar.py` | checagem final: `node --check`, explorador abrindo sem erro de JS e, com `--qualidade`, o gate do `qualidade.py` |
| `scripts/qualidade.py` | rubrica objetiva do modelo (nota 0 a 100 por critério e total) contra `references/baseline-qualidade.json`; `--listar-reprovados` |
| `scripts/codegraph_ponte.py` | arestas código → código (CodeGraph em leitura, ou `ast`): `--inventario`, `--relacoes`, `--impacto`; zero token |
| `scripts/linha_do_tempo.py` | linha do tempo da arquitetura, lida do git (zero token): por commit que tocou o mapa, o diff do `explorador/dados.js` por `ident` (componentes adicionados, removidos e alterados; relações novas e removidas; fluxos e seus passos), sha, data, assunto, tag mais próxima (`git describe --tags`) e as linhas novas do registro de atualizações; uma alteração ainda não commitada vira a última versão. Grava `explorador/linha-do-tempo.js` (`window.LODEMAP_LINHA_DO_TEMPO`) e `linha-do-tempo.json`; `--mapa`, `--saida`, `--max-versoes` (padrão 120; 0 = todas), `--rev`, `--omitir-sem-mudanca`, `--resumo`; sai com 3 fora de um repositório git. O `atualizar.py` o tenta após marcar o commit, antes das evidências; falhas só avisam |
| `scripts/evidencias.py` | evidências locais por componente via `props.codigo`: testes que referenciam o código, cobertura por arquivo de `lcov.info` ou `coverage.xml`, commits em 30/90 dias e última mudança, falhas JUnit só por atributo `file`; grava `explorador/evidencias.js` e opcionalmente `.json`. Referência inclui data UTC e commit da base Git; árvore de trabalho não verificada. Não executa testes nem infere prontidão; `--repositorio`, `--mapa`, `--cobertura`, `--junit`, `--data-referencia`, `--json` |
| `references/baseline-qualidade.json` | notas por critério do mapa público do axios; o gate compara com ela |
| `references/exemplos-estilo.md` | few-shot do estilo da casa (componentes, relações, fluxo), com projeto fictício |
| `templates/structurizr/` | a pasta da arquitetura: `workspace.dsl` esqueleto, `model/`, `views/` (estilos e tags de status), `scripts/`, `explorador/index.html` (+ `vendor/`), `leitor/index.html` (+ `vendor/`), `metricas/`, `docs/`, `adrs/` (ADR modelo no formato único), `lodemap.json`, `.gitignore` |
| `templates/tests/` | `test_arquitetura_cobertura.py`, `test_arquitetura_metricas.py`, `test_lodemap_diff.py`, `test_adrs_formato.py`, `test_leitor_gerador.py` e `test_barra_comum.py`, genéricos |
| `lodemap/` (`python -m lodemap`) | CLI única: `instalar`, `reverter`, `status`, `plano`, `consentir`, `revogar`, `verificar`, `doctor`; `--version` |
| `hooks/` | `aviso_lodemap.py`, o aviso único do perfil `padrao` do instalador (só biblioteca padrão) |
| `references/custo-equivalente.json` | modelo de custo medido (preços e rodadas) que o `plano` usa |
| `references/modelagem-c4.md` | níveis, como cortar componentes, relações, visões, fluxos, status, tags, formato das métricas |
| `scripts/esqueleto.py` | `rascunho` (decisões em JSON, com impressão digital semântica por módulo) , `pendencias` (o mesmo cálculo do rascunho, sem gravar nada: é o que o `lodemap_decidir.py` consulta) e `renderizar` (escreve o DSL e as visões estáticas) |
| `scripts/descrever.py` | rota enxuta: nome, descrição e área dos componentes pendentes numa chamada `claude -p` (Haiku medium); módulo a revisar mantém nome e área e só troca a frase se ela ficou falsa; cada frase traz evidência literal e passa por uma segunda chamada que lê o código e corrige ou rejeita a falsa (`--conferir <modelo>`, `--sem-conferir`); `--auditar` lista as falsas de um mapa existente sem mudar nada (saída 3 se achar); `--resumo` imprime uma linha, `--todos` refaz do zero |

## No projeto (`<arq>/scripts/`)

Scripts que vão para `<arq>/scripts/` (só biblioteca padrão do Python, 3.11 ou mais; os `.py` rodam em Windows, Linux e macOS; os `.ps1` são invólucros finos para o Windows):

| Script | Faz |
|---|---|
| `atualizar.py` | o caminho em qualquer sistema (Windows, Linux e macOS). Copia do template as páginas fixas que faltarem (explorador e `vendor/`, leitor e `vendor/`); valida, exporta, gera documentos, o leitor, atualiza o `relacoes-codigo.json` (a prova no código, sem modelo) e gera o `dados.js` do explorador; extensões locais (scripts do dono fora do repositório, em `"extensoes"` do `lodemap.json` ou `LODEMAP_EXTENSOES`; `--sem-extensoes` pula) e site estático só com `--com-site`; depois de marcar o commit, tenta a linha do tempo e as evidências locais pelos scripts da skill acessíveis a partir do template; essas falhas só avisam. Relatórios de cobertura/JUnit não são passados automaticamente. `--atualizar-interface` atualiza HTML e JS fixos existentes com backups exclusivos (não atualiza as pastas `vendor/` existentes); sem a opção, só copia fixos ausentes. `--incremental`, `--checkpoint`, `--python`, `--ferramentas`, `--template`, `--cli` (`--sem-site` fica por compatibilidade). Acha o Structurizr CLI em `--cli`, `STRUCTURIZR_CLI`, `<ferramentas>/cli` e no PATH (`structurizr.bat` no Windows, `structurizr.sh` nos outros); o `dot` vem do Graphviz empacotado ou do PATH |
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

## Comandos de observabilidade

A partir da raiz do checkout do Lodemap, substitua os caminhos abaixo pelos do projeto:

```bash
python scripts/linha_do_tempo.py --mapa /caminho/projeto/docs/architecture/structurizr --resumo
python scripts/linha_do_tempo.py --mapa /caminho/projeto/docs/architecture/structurizr --rev main --max-versoes 0 --omitir-sem-mudanca --saida /caminho/saida
python scripts/evidencias.py --repositorio /caminho/projeto --mapa /caminho/projeto/docs/architecture/structurizr --cobertura coverage.xml --junit junit.xml --data-referencia 2026-11-10 --json
```

`--rev` consulta o ramo, tag ou SHA sem checkout; sem ele, uma alteração local no mapa também pode aparecer como a
última versão. A tag exibida vem de `git describe --tags`, não certifica a correspondência exata a uma release.
A comparação representa o mapa registrado, não todas as mudanças do código. A data de referência das evidências
inclui o dia inteiro em UTC. Os relatórios devem estar dentro da raiz do código; caminhos relativos partem dela.
Relatório ausente ou sem correspondência não implica aprovação. Testes são referências estáticas; o coletor não os
executa. JUnit só associa casos cujo `file` identifica um teste referenciado. Data e commit não certificam a origem
dos relatórios nem a limpeza da árvore.

## Migrar a interface de mapas existentes

Mapas gerados por versões anteriores podem ter um `scripts/atualizar.py` que não reconhece
`--atualizar-interface`. `--template` não atualiza esse script, e `novo_mapa.py` preserva scripts existentes por padrão.
Prepare o script do mapa antes de usar a opção:

1. Atualize a instalação da skill ou o checkout do Lodemap e localize seu
   `templates/structurizr/scripts/atualizar.py` atual, de fonte confiável.
2. Preserve `<arq>/scripts/atualizar.py` antes de alterá-lo: crie o backup exclusivo
   `<arq>/scripts/atualizar.py.lodemap-bak`. Se já existir, use `.lodemap-bak.1`, `.lodemap-bak.2`, etc.; nunca
   sobrescreva um backup anterior. Compare o script local com o atual do template e confira as personalizações.
3. Se o script local não tiver personalizações, copie o arquivo atual do template para
   `<arq>/scripts/atualizar.py`. Se tiver, incorpore a atualização manualmente, preservando as personalizações e o
   backup anterior; não basta acrescentar a flag ao parser. Confira a atualização antes de executá-la.
4. Na pasta da arquitetura (`<arq>`), execute `python scripts/atualizar.py --help` e confirme que a ajuda contém
   `--atualizar-interface`. Execute sempre o script dentro do mapa: a raiz é determinada pela localização do
   próprio script, não pela pasta de trabalho. Não execute o script diretamente no template para atualizar o mapa.
5. Com o script do mapa atualizado, migre a interface e regenere as saídas na pasta da arquitetura:

```bash
python scripts/atualizar.py --atualizar-interface --template /caminho/lodemap/templates/structurizr
```

A opção atualiza `explorador/index.html`, `leitor/index.html`, `explorador/linha-do-tempo-ui.js` e
`explorador/saude.js` quando diferem do template. Cada arquivo anterior fica em `<nome>.lodemap-bak`; backups
existentes são preservados com `.1`, `.2`, etc. Revise as personalizações antes de executar. Sem a opção, os arquivos
fixos existentes são preservados. Mesmo com `--incremental`, a opção força o pipeline em vez de sair pelo atalho.
Para desfazer uma migração, confira o backup escolhido e restaure-o sobre o arquivo correspondente; não há comando
de reversão automática dessa opção. Os coletores exigem acesso aos scripts da skill pelo template e suas falhas são
avisos. Confira as saídas; uma geração concluída não certifica que as evidências foram atualizadas.

A visão Linha do tempo usa snapshots históricos e suas comparações; a visão Saúde usa a coleta atual. Evidências
atuais não são atribuídas a versões antigas. As cores de Saúde indicam referência de teste encontrada, nenhuma
referência encontrada ou dado desconhecido. O alerta de `Pronto` sem referência de teste pede revisão humana.
