# Como abrir o explorador, o leitor e o Lite

Portas, opções e o que o `ver_arquitetura.py` faz antes de servir.

`python scripts/ver_arquitetura.py` (em qualquer sistema; no Windows também `.\scripts\ver-arquitetura.ps1`, que só repassa os
parâmetros) serve a pasta da arquitetura em localhost e abre o explorador (`--abrir leitor` abre a documentação;
`--com-lite` sobe também o Lite). Antes de servir, atualiza os dados se algum arquivo da pasta da arquitetura (`.dsl`, `.md`,
`.json`, `.py`, `.groovy`, fora das pastas geradas) estiver mais novo que o `dados.js`. Abaixo, as opções estão na forma da CLI do Python; no `.ps1` são `-Abrir`,
`-ComLite`, `-Porta`, `-PortaExplorador`, `-SemNavegador`:

| Página | Endereço padrão | Configuração |
|---|---|---|
| Explorador | `http://127.0.0.1:8791/explorador/` | `--porta-explorador`; campo `explorador` do `lodemap.json` |
| Leitor de documentação | `http://127.0.0.1:8791/leitor/` | o mesmo servidor do explorador; também abre por `file://` |
| Structurizr Lite (opcional) | `http://localhost:8790` | só com `--com-lite`; `--porta`; campo `lite` do `lodemap.json` (`novo_mapa.py --porta-lite`) |
| Site estático (opcional) | `http://127.0.0.1:8791/site/` | só existe depois de `atualizar.py --com-site` |

Sem `--porta` e `--porta-explorador`, o script usa as portas do `lodemap.json`; os valores acima são só o padrão
do `novo_mapa.py`.

O explorador é servido por `python -m http.server --bind 127.0.0.1` na pasta da arquitetura. Se a porta já tem um
explorador no ar, o script só abre o navegador; se está ocupada por outro programa, avisa e abre o arquivo local,
sem encerrar nada. Escolha portas livres do projeto. Sem `--com-lite` (ou `--abrir lite`/`ambos`) o Lite não
sobe; `--sem-navegador` só sobe os servidores. Quem subiu um servidor para conferir algo encerra o processo
dele no fim (só ele: o `python -m http.server <porta>` com a pasta do projeto na linha de comando, ou o `java` com
`structurizr-lite`).
