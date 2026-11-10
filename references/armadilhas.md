# Armadilhas conhecidas

Leia quando um passo falhar de um jeito estranho. A maioria é de ambiente (Windows, PowerShell, Structurizr Lite).

- **PowerShell 5.1:** `.ps1` com acento precisa de UTF-8 com BOM. Com `$ErrorActionPreference = "Stop"` e saída
  redirecionada, o aviso do Graphviz no stderr ("size too small for label") vira erro fatal; por isso a lógica saiu
  do `.ps1`: o `atualizar.py` não usa essa variável e decide pelo código de saída do processo.
- **Git Bash:** heredoc colapsa `\\` em `\`. Patches com barras invertidas vão num arquivo e rodam de lá.
- **Structurizr Lite:** com caminho absoluto com letra de unidade em `STRUCTURIZR_WORKSPACE_PATH` ele quebra; o
  `ver_arquitetura.py` passa o caminho relativo à pasta padrão dele no Windows (em Linux e macOS, o absoluto). O Lite devolve 200 até na página de erro
  (conferir o conteúdo) e grava `workspace.json` e `.structurizr/` ao lado do DSL.
- **Export por projeto:** o `atualizar.py` exporta em `<arq>/.structurizr/export`, para dois projetos não dividirem
  o mesmo `workspace.json` na pasta de ferramentas.
- **Venv no Windows:** o `python.exe` de um venv é um lançador que abre o Python base; um servidor sobe como dois
  processos (encerre os dois).
- **Ganchos:** rodam sem as variáveis da sessão (por isso `--ferramentas` fica gravado no gancho) e com o `sh` do Git
  para Windows; o `lodemap_gancho.py` nunca devolve erro ao git.
- **Graphviz:** sem `dot` (`dot.exe` no Windows) no PATH do processo, o `autoLayout` não roda no export estático nem no Lite.
- **Visões dinâmicas:** cada passo precisa de uma relação que exista no modelo; numa visão de container só entram
  componentes desse container (de outro container, use o container todo e declare a relação container → componente).
- **Bibliotecas embutidas:** Cytoscape, dagre e Mermaid ficam em `explorador/vendor/` e `leitor/vendor/`; nenhuma página carrega nada de CDN.
- **BOM no `lodemap.json`:** o PowerShell 5.1 (`Set-Content -Encoding UTF8`) grava BOM; todos os scripts e
  testes leem o JSON com `utf-8-sig`, então edite à vontade, mas prefira o Edit/Write a `Set-Content`.
- **Contexto e Containers sem seta:** com `!impliedRelationships false`, as visões de panorama só têm setas se você
  declarar relações de `sistema` e de container (além das de componente). Sem elas, a visão "Containers" sai como uma
  coluna de nós soltos; declare-as no fim do `relacoes.dsl`.
- **`lodemap_diff.py` só olha commits:** mudança não commitada não aparece; commite (ou use `git stash`) antes de medir.
- **Fim de linha:** com `core.autocrlf=true` o checkout vem em CRLF; os geradores gravam LF e o git normaliza.
- **Explorador:** ao fim de todo layout sem nó em foco o grafo faz `resize` e `fit` no canvas inteiro; sem foco, os
  "Círculos em volta do foco" põem os nós mais ligados no centro.
- **Métricas:** o teste pula a conferência dos números quando os commits de evidência não estão no clone (CI raso),
  mas nunca aceita fonte incompleta.
- **Projeto com o nome antigo** (`structurize-map.json`, `.smap/`, `smap_diff.py`): rode `python ~/.claude/skills/lodemap/scripts/migrar_para_lodemap.py <pasta da arquitetura>` (plano) e depois com `--aplicar`, e copie de novo os scripts do template. As variáveis de ambiente passaram de `STRUCTURIZE_*` para `LODEMAP_*`.
