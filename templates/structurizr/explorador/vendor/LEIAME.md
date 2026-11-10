# Bibliotecas embutidas do explorador

Cópias fiéis, sem alteração, carregadas por `../index.html` para o explorador abrir por `file://` e por http sem
nenhuma requisição externa. Todas são MIT; a licença de cada uma está ao lado.

| Arquivo | Versão | Origem | Licença |
|---|---|---|---|
| `cytoscape.min.js` | 3.30.2 | https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.2/cytoscape.min.js | `LICENSE-cytoscape.txt` |
| `dagre.min.js` | 0.8.5 | https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js | `LICENSE-dagre.txt` |
| `cytoscape-dagre.js` | 2.5.0 | https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.js | `LICENSE-cytoscape-dagre.txt` |

Para atualizar, baixe a nova versão da mesma origem, troque o arquivo e a linha desta tabela e rode o teste
`templates/tests/test_explorador_vendor.py`.
