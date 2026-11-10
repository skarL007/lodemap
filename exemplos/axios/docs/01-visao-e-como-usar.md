# Overview and how to use

This is the architecture of axios in the C4 model, written in Structurizr. `workspace.dsl` and the fragments in
`model/` and `views/` are the source. Everything shown in the diagrams, the explorer, the reader and the derived
documents comes from them.

## How to open

To regenerate, on any system (Windows, Linux and macOS; Python 3.10+ and the Structurizr CLI), in the architecture folder:

```
python scripts/atualizar.py                       # validates and regenerates docs, reader and explorer, opens nothing
python scripts/atualizar.py --incremental --checkpoint "merge feat/x"
python scripts/atualizar.py --com-site            # also the Structurizr static site
```

`atualizar.py` finds the Structurizr CLI in `STRUCTURIZR_CLI`, then in `~/.structurizr/cli/`, then on the PATH
(`structurizr.bat` on Windows, `structurizr.sh` elsewhere). On Windows, `atualizar.ps1` still exists as a thin wrapper
that calls `atualizar.py` with the same parameters (`-Incremental`, `-Checkpoint`, `-ComSite`).

To open, in PowerShell (Windows):

```
.\scripts\ver-arquitetura.ps1                 # explorer (diagrams and flows) on localhost
.\scripts\ver-arquitetura.ps1 -Abrir Leitor   # docs and decisions reader
.\scripts\ver-arquitetura.ps1 -ComLite        # Structurizr Lite as well
```

Outside Windows, serve the folder with `python -m http.server --bind 127.0.0.1` and open `explorador/index.html` or `leitor/index.html`.

The explorer is at `http://127.0.0.1:8791/explorador/` and the reader at `http://127.0.0.1:8791/leitor/`, both served by `python -m http.server --bind 127.0.0.1`; they also open straight from disk. Structurizr Lite (`http://localhost:8790`) only starts with `-ComLite`. The URLs live in `lodemap.json` (`lite` and `explorador`). If the port already serves the architecture, the script only opens the browser.

The Structurizr static site is off by default: `atualizar.py --com-site`. Your own scripts, outside the repository, plug in as local extensions: list them under `"extensoes"` in `lodemap.json` (or in `LODEMAP_EXTENSOES`, separated by `;` and, outside Windows, also by `:`); each one receives `workspace.json`, `--arq` and `--repo`.

## Language

The generated outputs follow `"idioma"` in `lodemap.json` (`pt` by default, `en` available). The explorer and the reader have a PT | EN switch in the top bar; the choice is remembered in the browser. Status values in the DSL may be written in either language ("Em andamento" or "In progress"); the generators read both.

## Checkpoint updates

`--checkpoint` (`-Checkpoint` in the `.ps1`) writes the label to `.lodemap/estado.json` (and passes it to local extensions); `--incremental` only regenerates when something
changed since the last generation (`scripts/lodemap_diff.py`). The git hook is opt-in:
`.\scripts\instalar-gancho.ps1 -Python <python> -Ferramentas <folder>` (and `-Remover`). It runs `atualizar.ps1` (which calls `atualizar.py`)
in the background on every commit that touches the code or the DSL and on every merge, logging to `.lodemap/ultimo-atualizar.log`.

## Interactive explorer

`explorador/index.html` reads `explorador/dados.js` (generated; do not edit by hand). Click a node to light up its
links; `Shift`+click shows the path between two nodes; double click opens its neighborhood in the whole model; the
dynamic views play step by step. The panel shows status, code (VS Code and GitHub), observability, metrics (current ×
target, date and source), the impact of a change and the links to the reader. The address `index.html#<DSL identifier>`
opens the smallest view that contains the element, already focused.

## Docs and decisions reader

`leitor/index.html` reads `leitor/dados.js`, generated from `docs/*.md` and `adrs/*.md` by `scripts/gerar_leitor.py` (do not edit by hand). Documents are grouped into Explanation, Guides and Reference (the generated 02, 90 and 91) and the ADRs sit on a timeline with their status. It has a side table of contents, full-text search (`/` key), light and dark themes (`?tema=claro` or `?tema=escuro`) and stable anchors: `leitor/index.html#doc-<file without .md>` and `#adr-<4-digit id>`. Every element it cites links to the map (`explorador/index.html#<identifier>`).

## Decisions (ADRs)

One format, in `adrs/NNNN-<title>.md`: a YAML header with `id`, `titulo`, `status` (`proposta`, `aceita`, `substituida` or `rejeitada`; shown as Proposed, Accepted, Superseded, Rejected), `data`, `date` (a copy of `data`, read by Structurizr), `decisores`, `elementos` (model identifiers), `substitui`, `substituida_por` and `evidencia`; then the sections Context, Decision, Alternatives and Consequences. The index `92-indice-de-decisoes.md` is generated, and the test `test_adrs_formato.py` fails if an ADR cites an element that does not exist, if a supersession is not reciprocal or if the status is invalid.

## Colors and shapes

| Color | Status | Meaning |
|---|---|---|
| Green | Done | In the code, tested and integrated. |
| Amber | In progress | Someone is working on it now. |
| Purple | Waiting | Waiting for review, a decision or another team. |
| Dashed blue-gray | Planned | In the design, not in the code. |
| Dimmed gray | Out of focus | Exists, but is not a priority. |

| Shape | Tag | Meaning |
|---|---|---|
| Cylinder | Dados | Stores data. |
| Hexagon | Gate | Privacy, cost or contract guard. |
| Robot | Modelo | Process that serves a model. |
| Browser | WebBrowser | Page. |
| Window | Janela | Desktop window. |
| Pipe | Barramento | Event stream. |
| Dashed orange border | Externo, Nuvem | Off the machine. |
| Thick yellow border | Privacidade | Touches private data. |

## How to change it

1. Edit the right fragment in `model/` or `views/`.
2. Run `python scripts/atualizar.py` (or `scripts\atualizar.ps1` on Windows).
3. Record the reason in `99-registro-de-atualizacoes.md`.
4. Run the tests `test_arquitetura_cobertura.py`, `test_arquitetura_metricas.py`, `test_adrs_formato.py` and `test_leitor_gerador.py`.
