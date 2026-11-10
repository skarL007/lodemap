# Changelog

All notable changes to Lodemap. Dates are when the change landed on `main`.

## Unreleased

- **Terminal in English:** the `python -m lodemap` CLI, `scripts/` and the scripts copied into a repository
  (`templates/structurizr/scripts/`) print their messages and `--help` in English or Portuguese. One rule, in
  `lodemap/idioma.py`: `LODEMAP_IDIOMA=pt|en` wins; else the map's `"idioma"` in `lodemap.json` when the command
  points at a map; else the system locale (`pt*` gives Portuguese); else English. Commands and options gained English
  names (`install`, `revert`, `plan`, `consent`, `revoke`, `check`; `--profile`, `--apply`, `--without`, `--with`,
  `--force`, `--scopes`, `--monthly-budget`, `--scope`, `--cost`, `--all`, `--manifest`, `--source`, ...) and the
  Portuguese ones keep working as aliases. Data (JSON keys, scope values `gerar`/`gancho`/`modelo`, files) is unchanged.
  Tests set `LODEMAP_IDIOMA` explicitly; `tests/conftest.py` defaults it to `pt`.

## 0.1.0 (unreleased, first public version)

- **Validation round (repetition, Linux, Go):** the axios update was repeated three times (US$ 0.29 to 0.47,
  same structure each time); the suite, the full regeneration, the delivered tests, the quality gate and the real
  git hook ran on Linux; a Go repository (go-chi/chi) was mapped from scratch and updated across a release.
  Figures in `references/benchmark-e-custo.md`. What it changed in the skill:
  - `"ignorar"` in `lodemap.json`: globs for files that sit next to the code and are not modules (tests,
    examples, fixtures), with defaults per language; every script and the coverage test read the same list.
  - `novo_mapa.py` detects the code root: the first conventional folder that has code, otherwise the repository
    root (`"raiz_codigo": ""`, globs such as `**/*.go`).
  - Go edges by symbol instead of by package: on chi, 6 wrong edges became 31, all confirmed in the code.
  - Fingerprint version 2 (`2:` prefix): class and instance attributes, `__init__` parameters and public
    variables in Python; exported object keys, export lists, class members and multi-line parameters in JS/TS; the
    first doc line of exported symbols in Go. It catches 9 of the 12 surface changes version 1 missed in rich and
    axios with no extra review, and old maps migrate without a bulk review.
  - Pending work survives a second `rascunho`: undecided relations and pending reviews stay listed until someone
    decides; `renderizar` clears them.
  - Quality rubric reads the code: a component with no relation counts as an orphan only when the code links it,
    and the relations-per-component target follows what the code shows. A library of independent modules no longer
    fails with the right map.
  - Explorer: nodes with no link go to a grid below the graph instead of one tall column; area views show their
    own name in the sidebar instead of the same cut prefix.
  - `atualizar.py` also finds the template through `LODEMAP_SKILL`, so the hook refreshes the code proof without
    the skill installed in `~/.claude`.
- **Update policy (when to update, for zero tokens):** `scripts/lodemap_decidir.py` measures the map debt (modules
  outside the model, paths that are gone, changed public surfaces, new import relations, commits since the last run)
  and answers `nada`, `scripts`, `adiar`, `descrever`, `modelar` or `gerar`, with the reasons and the exact next
  command. Optional `"politica"` block in `lodemap.json`; with `tolerancia_modulos` above 0, new modules may wait in a
  versioned, dated `pendentes.json` and the coverage test passes until the limit or the deadline is crossed. Default
  stays strict. The `post-commit` hook now regenerates only when the answer is `scripts` (it used to run on every
  commit that touched code); `esqueleto.py pendencias` is the dry run behind the review and relation counts.
- **Explorer:** flows pick the direction that fits the canvas (a 13-step flow went from about half size, clipped at
  the edges, to fully visible); the legend starts closed, remembers the choice, and no node is framed under a floating
  box; relation labels no longer hide under nodes in column layouts; marker names follow the interface language and
  the inspector stops repeating status and area as markers.
- **Lean description route (default for name, description, area):** `scripts/descrever.py` fills name, one-sentence description and area of the
  pending components with one `claude -p` call (Haiku medium, no tools or MCP, JSON Schema output with the area as an
  enum, deterministic per-module card, one targeted retry through a gate). On rich: score 95–97, same band as the
  subagent, about half the tokens; on axios (JavaScript): area 0.90 agreement with a Sonnet reference, 70k vs 99k
  tokens. Falls back to the modeler on any failure.
- **Scope:** Lodemap is the architecture map and the project documentation only. The default agents, safety hooks,
  telemetry and the Agents view are not part of it (2026-11-06). The optional bridge to an external memory engine
  and its consent scope were removed before the first public version; the scopes are `gerar`, `gancho`
  and `modelo`.
- **Installer:** two profiles (`minimo`: skill + six `lodemap-*` agents; `padrao`: + one-time hint), dry run by
  default, byte-exact `reverter`, refuses to touch files owned by someone else without `--forcar`.
- **Permission:** `plano` (0 tokens), `consentir` per scope with a finite monthly ceiling, `revogar`; `plano` now warns
  when the default globs find no module instead of printing a zero-cost estimate.
- **Docs reader:** draws Mermaid diagrams offline (embedded tiny build, loaded only when a page has one), with theme,
  real size, view source and full screen.
- **Security:** git hook launcher runs only scripts whose hash was approved; agent names restricted to
  `[A-Za-z0-9-]`; absolute personal paths removed from versioned files, and the private repositories used in the
  import-precision measurement are named R1 to R5. `SECURITY.md` says how to report a vulnerability.
- **Portability:** the commit hook falls back to `pwsh` outside Windows; `verificar.py` fails clearly when
  `explorador/index.html` is missing.
- **Language:** Portuguese by default, English on request (`lodemap.json` `"idioma"` or `LODEMAP_IDIOMA`): docs,
  explorer, reader, DSL labels and generated views; PT | EN switch on the pages. Most terminal messages are still in
  Portuguese.
- **Deterministic views:** context, containers, per-container, per-area (12+ components) and per-status views are
  written by `esqueleto.py` into `views/visoes-geradas.dsl`; the model now writes only dynamic flows. Quality gate
  accepts English status labels.
- **Cross-platform pipeline:** `atualizar.py` (Windows, Linux, macOS; `atualizar.ps1` is a thin wrapper). Only
  Windows was run end to end.
- **AST relation proof:** imports in Python, JS/TS, Go, Rust, Java, Kotlin, C# and C/C++; precision on the new
  languages not measured yet.
- **Docs reader:** `mindmap`, `architecture` and KaTeX formulas load the full Mermaid build (5.3 MB) only on pages
  that need it.
- **Semantic fingerprint:** `esqueleto.py rascunho` stores a `digital` per component (public surface only) and lists
  in `pendentes.componentes_revisar` just the modules whose surface changed; body-only edits keep their description.
  Measured on five rich release pairs: 78 changed files, 29 reviews (63% fewer). See `references/digital-semantica.md`.
- **Removed:** the personal note-vault export; one undocumented, unused style tag (the documented shape tags are
  unchanged).
- **Measurement notes:** the three private repositories measured before the public demos appear as project A, B and
  C in `references/benchmark-e-custo.md` and `references/custo-equivalente.json` (round ids renamed to match). No
  figure changed.
- **Non-Python repositories out of the box:** without `--modulos`, `novo_mapa.py` and `plano` pick the globs from the
  language that dominates the code root (`lib/**/*.js` on a JavaScript package; Python keeps `raiz/*.py` +
  `raiz/*/`). Before, `plano` counted 7 modules on axios instead of 69.
- **Fixed: `**` in module globs.** `lib/**/*.js` did not match files directly under `lib/` when turning import edges
  into relations, so every edge from or to a root-level file was dropped (44 of 165 on axios). The match now follows
  `Path.glob`, the same rule the coverage test uses.
- **Manual relations:** a relation the imports cannot show (HTTP, config-selected adapter, late import) is added with
  `manual: true` and is no longer flagged `sumiu_do_codigo` on the next `rascunho`.
- **Conservative review:** on an update, `descrever.py` keeps the name and the area of a module that already had
  them and rewrites the sentence only when the change made it false. On axios v1.20.0 → v1.21.1: 1 of 16 sentences
  changed, against 16 of 16 (plus 8 names and 3 areas) before. `--resumo` prints a one-line report.
- **Quality gate:** `observabilidade` still counts in the total but has no floor of its own; a library with no logs
  or metrics scored 0 there with a correct model and failed the gate.
- **Versioned decisions:** the installed `.gitignore` keeps `.lodemap/decisoes-modelo.json` in git, so another
  machine or CI sees the same decisions and fingerprints instead of treating every module as new.
- **English output where it is read by others:** coverage-test failure messages, the summary lines of `rascunho`,
  `renderizar` and `descrever.py --resumo`, and the steps of `atualizar.py` follow the map language.
- **Fixed: the explorer data carried the absolute path of the repository.** `explorador/dados.js` is versioned, and
  it stored the local path (user name included) for the "VS Code" link. The path is gone from the file: opened as a
  file the explorer derives it from its own address, served on 127.0.0.1 it reads `.lodemap/local.json` (not in git),
  and a hosted copy has no such link.
- **Fixed: change panel and commit hook on `**` globs.** `lodemap_diff.py` and the git hook matched module globs with
  `fnmatch` plus a slash count, so with `lib/**/*.js` only files exactly one folder deep counted as changed modules.
- **Fixed: stale warning in `atualizar.py --incremental`.** "Modules with no component" was computed before the
  export, from the previous model, and fired even when the DSL already had the new components.
- **Update hand-off:** after describing a new module, `descrever.py` lists it in
  `pendentes.componentes_sem_container_ou_status`, so the modeler still knows what is left to decide.
- **Public demo:** a map of axios made at v1.20.0 and updated to v1.21.1, with the measured cost of both (README).
- **CLI:** `python -m lodemap --version` and `python -m lodemap doctor` (alias `diagnostico`; `--json`, `--repo`): a
  read-only check of Python, git, `claude`, Structurizr CLI, Graphviz, Java, Node, the installed skill and agents,
  and, with `--repo`, the map and the consent of that repository. Exit 1 only when something required is missing.
- **Quality gate baseline:** `references/baseline-qualidade.json`, described as what it is (the first map the
  skill produced), with the report key `totalBaselineComparavel`. Record your own with `qualidade.py --gravar-baseline`.
- **Docs:** `SKILL.md` cut from 49 KB to 26 KB; the detail moved to `references/` (scripts, quality gate, code edges,
  state file, reader and ADRs, serving, pitfalls) and is read only when a step needs it. README rewritten.
- **CI:** CircleCI (Linux on Python 3.11 and 3.12, Windows), running `tests/` and the two template tests that run
  standalone. The config compiles; the pipeline has not run yet (the repository is not published).
- **Tests:** 284 in `tests/`, plus 14 in the two standalone template files (`python -m pytest`).
