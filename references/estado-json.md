# `.lodemap/estado.json`

Arquivo local (fora do git) por onde os agentes passam estado e pendências.

```json
{
  "versao": 1,
  "projeto": "Nome",
  "ultimoCommit": "sha completo da última geração verde",
  "geradoEm": "2026-11-02T18:36:17-03:00",
  "checkpoint": "post-commit fd7f7d0: assunto",
  "fonteRelacoes": "codegraph|ast (de onde vieram as arestas do relacoes-codigo.json; no ast, sugerir ao dono indexar)",
  "qualidade": {"total": 0, "aprovado": true, "rodadas": 0, "pendencias": ["critério e componentes que ainda reprovam"]},
  "historico": [{"commit": "...", "geradoEm": "...", "checkpoint": "..."}],
  "passos": {
    "inventario":     {"status": "pendente|ok|falhou", "arquivos": [], "contagens": {}, "pendencias": []},
    "modelador":      {"status": "...", "arquivos": ["model/componentes-x.dsl"], "contagens": {"componentes": 0}, "pendencias": []},
    "qualidade":      {"status": "...", "arquivos": [], "contagens": {}, "pendencias": []},
    "metricas":       {"status": "...", "arquivos": [], "contagens": {}, "pendencias": []},
    "gerador":        {"status": "...", "arquivos": [], "contagens": {}, "pendencias": []},
    "verificador":    {"status": "...", "arquivos": [], "contagens": {}, "pendencias": []},
    "revisor-visual": {"status": "...", "arquivos": [], "contagens": {}, "pendencias": []}
  },
  "artefatos": {"inventario": "inventario.json", "modelo": "model/", "metricas": "metricas/metricas.json",
                "explorador": "explorador/dados.js", "documentos": "docs/", "site": "site/"}
}
```

O `atualizar.py` grava `ultimoCommit`, `geradoEm`, `checkpoint` e `historico` no fim de uma geração verde
(`lodemap_diff.py --marcar`). Os agentes escrevem só o próprio bloco de `passos`.

## `.lodemap/local.json`

Gravado pelo `gerar_explorador.py`: `{"repo": "<raiz do repositório nesta máquina>"}`. Serve só para o link "VS Code"
do explorador quando ele é servido em `127.0.0.1`. Fica fora do git como o resto de `.lodemap/` (menos o
`decisoes-modelo.json`). O `explorador/dados.js`, que é versionado, não leva caminho absoluto: guarda apenas `arqRel`,
a pasta da arquitetura a partir da raiz do repositório.

## `pendentes.json` e a política de atualização

Fica na pasta da arquitetura e **é versionado**: é a lista dos módulos que o dono deixou esperar fora do modelo.

```json
{"versao": 1, "modulos": {"lib/novo.js": {"desde": "2026-11-09", "commit": "abc1234"}}}
```

Quem grava é o `lodemap_decidir.py --adiar` (zero token): acrescenta os módulos fora do modelo, tira os que já
entraram ou sumiram, nunca muda o `desde` de quem já estava e apaga o arquivo quando ele ficaria vazio. Só grava se a
política deixar. O teste de cobertura lê o mesmo arquivo.

A política é o bloco opcional `"politica"` do `lodemap.json`:

| Chave | Padrão | O que decide |
|---|---:|---|
| `tolerancia_modulos` | 0 | quantos módulos podem esperar fora do modelo (0: gate estrito) |
| `tolerancia_dias` | 14 | por quantos dias um módulo adiado pode esperar |
| `revisoes_para_atualizar` | 10 | superfícies públicas mudadas que justificam uma rodada de `descrever.py` |
| `relacoes_para_atualizar` | 10 | relações novas no código que justificam chamar o modelador |
| `commits_para_regenerar` | 10 | de quantos em quantos commits o gancho regenera por scripts quando só o conteúdo mudou |

