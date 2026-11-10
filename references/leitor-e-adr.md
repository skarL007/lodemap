# Leitor de documentação, ADR no formato único e barra comum

Leia antes de criar ou migrar ADRs, de mexer na organização dos documentos ou na barra de topo.

## Leitor

O leitor (`leitor/index.html`, fixo, + `leitor/dados.js`, gerado por `gerar_leitor.py`) é a documentação do mapa, no
mesmo design do explorador (tokens `sds:tokens`). Organização no espírito do Diátaxis:

| Seção | O que entra | Como o gerador decide |
|---|---|---|
| Explicação | por que o sistema é assim (propostas, conceitos) | o padrão para `docs/*.md` |
| Guias | como fazer (abrir, atualizar, mudar) | nome com `como-`, `guia`, `tutorial` ou `<!-- leitor: guia -->` no arquivo |
| Referência | gerados do modelo (02, 90, 91) e o registro 99 | marca "Gerado por scripts/gerar_docs.py", prefixo `99-` ou `<!-- leitor: referencia -->` |
| Decisões | os ADRs numa linha do tempo, com filtro por status | `adrs/*.md`; o índice `92-indice-de-decisoes.md` vira esta seção |

- **Âncoras estáveis** (o explorador e as notas linkam para elas): `leitor/index.html#doc-<arquivo sem .md>`,
  `#adr-<id de 4 dígitos>`, `#decisoes`; títulos internos como `#doc-<arquivo>--<titulo>`.
- **Links cruzados:** link para outro `.md` vira âncora do leitor; `` `identificador` `` do modelo vira link "ver no
  mapa" (`../explorador/index.html#<identificador>`); cada elemento citado num ADR tem "Ver no mapa".
- Sumário lateral, "Nesta página", busca no texto (`/` ou Ctrl+K), tema por `?tema=claro|escuro`, quatro estados
  (carregando, vazio, erro sem `dados.js` ou âncora inexistente, conteúdo). Abre por `file://` e por http, sem
  nenhuma requisição externa (Markdown renderizado no gerador, só biblioteca padrão).
- **Diagramas Mermaid:** um bloco ```` ```mermaid ```` vira `<figure data-diagrama>` com o texto dentro; o leitor o desenha
  no navegador com `leitor/vendor/mermaid.tiny.js` (MIT, 12.3.0, carregado só em página que tem diagrama), nas cores do
  tema, com "Tamanho real", "Ver código" e "Tela cheia". A versão `tiny` não desenha `mindmap`, `architecture` nem
  fórmulas: nesses casos, ou se a biblioteca faltar, o texto fica visível com um aviso. Projeto gerado antes disso:
  apague o `leitor/index.html` antigo e rode `atualizar.py` para copiar a página nova e o `leitor/vendor/`.

**ADR no formato único** (`adrs/NNNN-<titulo>.md`; o `workspace.dsl` usa `!adrs adrs madr`, que lê `status` e `date` do
cabeçalho):

```markdown
---
id: "0007"
titulo: Fila única de eventos
status: proposta
data: 2026-11-05
date: 2026-11-05
decisores: [dono]
elementos: [nucFila, nucRotas]
substitui: []
substituida_por: []
evidencia:
  - docs/40-fluxo.md
---

# Fila única de eventos

## Contexto
## Decisão
## Alternativas
## Consequências
```

`status` é `proposta`, `aceita`, `substituida` ou `rejeitada`; `date` repete `data` (é o campo que o Structurizr lê);
`elementos` são identificadores do DSL; `substitui` e `substituida_por` levam ids de 4 dígitos e são recíprocos. Sem
comentários no cabeçalho. O `test_adrs_formato.py` falha com campo faltando, status inválido, id diferente do número do arquivo, seção
faltando, elemento que não existe no `workspace.json` exportado (ou nos `.dsl`) e `substitui`/`substituida_por` sem
par. Listas manuais de decisões dão lugar ao índice gerado (`92-indice-de-decisoes.md` e `leitor/#decisoes`).
Decisão que já tinha outro número (por exemplo `H-012` num registro antigo) leva `aliases: [H-012]` no cabeçalho: o
leitor mostra "Também registrada como" e a busca acha pelo número antigo. Ao migrar um registro, não duplique o que
já virou ADR: acrescente o alias ao ADR existente.

## Barra comum

Explorador e leitor usam a mesma barra (blocos `lodemap:barra` e `lodemap:barra-fim` no HTML, com a busca da página
entre eles, e `lodemap:barra:css` no CSS, idênticos nas duas páginas; `test_barra_comum.py` compara): marca do
projeto, navegação **Mapa | Documentação | Decisões** (links relativos `../explorador/`, `../leitor/`,
`../leitor/index.html#decisoes`), estado ativo por `aria-current`, a busca da própria página, tema (propaga
`?tema=` nos links) e, até 900 px, um menu compacto com as três seções. A página chama
`LodemapBarra.ativar("docs"|"decisoes"|...)` e `LodemapBarra.projeto(nome)`; a troca de tema dispara o evento
`lm:tema`. Mudou a barra? Mude nas duas páginas.
