# Biblioteca embutida do leitor

Cópia fiel, sem alteração, carregada por `../index.html` só quando uma página tem um diagrama Mermaid. Assim o leitor
abre por `file://` e por http sem nenhuma requisição externa, e uma documentação sem diagramas não paga o custo do arquivo.

| Arquivo | Versão | Origem | Licença |
|---|---|---|---|
| `mermaid.tiny.js` | 12.3.0 | https://cdn.jsdelivr.net/npm/@mermaid-js/tiny@12.3.0/dist/mermaid.tiny.js | `LICENSE-mermaid.txt` (MIT) |
| `mermaid.min.js` | 12.3.0 | https://cdn.jsdelivr.net/npm/mermaid@12.3.0/dist/mermaid.min.js | `LICENSE-mermaid.txt` (MIT) |

SHA-256 do `mermaid.tiny.js`: `C41F5236091B83F524C4940F97A16B2B14A76F21FF84AEA4FD6B66421D8A2A9A`.

SHA-256 do `mermaid.min.js`: `336DF803D87A38B70A01E736E666C8F7601D2CE42F5E47C8FAFE5D721074B9A3`.

**Duas versões, carregadas sob demanda.** A `tiny` (2,8 MB) desenha fluxogramas, diagramas de sequência, de
classes, de estados, entidade-relacionamento, Gantt, pizza e outros, e é a que o leitor carrega por padrão. Ela não
desenha `mindmap`, `architecture` nem fórmulas KaTeX (`$$...$$`). Quando a página tem um bloco desses, o leitor
carrega a versão completa (`mermaid.min.js`, 5,3 MB) no lugar. Uma página sem diagramas não carrega nenhuma das
duas. Para economizar espaço num mapa que não usa esses tipos, apague `mermaid.min.js`: o bloco mostra um aviso e o
texto continua visível.

**Licenças do que vem dentro.** O pacote embute dependências do Mermaid, todas permissivas: MIT (mermaid, dayjs, marked,
stylis, roughjs, dagre-d3-es, lodash e outras), ISC (d3), BSD-3-Clause (d3-sankey) e Apache-2.0 (chevrotain). O DOMPurify
vem sob "MPL-2.0 OU Apache-2.0"; este projeto o usa sob a Apache-2.0. O texto da Apache-2.0 está em
`LICENSE-apache-2.0.txt`. Os avisos de direitos autorais que o próprio pacote carrega permanecem dentro do arquivo.

Para atualizar, baixe a nova versão da mesma origem, troque o arquivo, a versão e o SHA-256 desta tabela, e rode
`templates/tests/test_leitor_gerador.py`.
