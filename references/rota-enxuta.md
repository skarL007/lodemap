# Lean description route (`scripts/descrever.py`)

The repetitive part of phase B (a name, a one-sentence description and an area for each module) does not need a
full subagent. `descrever.py` does it with one call to the official Claude Code CLI in print mode, using the
subscription (never the API). Containers, areas, relations, status and flows stay with `lodemap-modelador`.

## What the call uses

| Feature | Flag | Measured effect |
|---|---|---|
| Lean prefix: no tools, no MCP, no settings | `--tools "" --strict-mcp-config --setting-sources ""` | fixed cost per call fell from 55,463 to 1,056 cache-creation tokens (52×) |
| Short, stable system prompt (cacheable) | `--system-prompt-file` | a second call with the same prefix read 46,621 tokens from cache |
| Structured output, area as an enum of the decided areas | `--json-schema` | 0 parse failures in 9 runs; no invented area |
| Answer only through the output tool | instruction in the system prompt | removes the extra turn where the model writes the JSON as text first and then again in the tool (that turn doubled the cost: 67,828 → 134,817 tokens) |
| Deterministic card per module instead of the raw file head | built by the script | 4× fewer tokens than the code head, same score |
| All modules in one call | `--lote 76` | 4 batches of 19 scored lower (94.6) and cost more (81,698 tokens) |
| Gate + one targeted retry | built by the script | rejected 2 of 76; the retry cost 5,870 tokens and did not move the score |

`--bare` is not used: it requires an API key. The Message Batches discount is API-only and is out for the same reason.

## Measurement on rich (Python, 76 modules)

Benchmark: [Textualize/rich](https://github.com/Textualize/rich), 76 modules, scored against the Sonnet reference with
the benchmark rubric: score = 25·area + 30·key facts + 25·similarity + 10·(1 − generic) + 10·length. The 95% interval
comes from a bootstrap (2,000 resamples). Model: Haiku, effort medium, through `claude -p`.

| Variant | Score | 95% interval | Area | Tokens | Turns |
|---|---:|---|---:|---:|---:|
| Subagent (previous route) | 96.9 | 93.1–98.6 | — | 129,385 | — |
| Code head, 1 call | 96.0 | 92.4–97.9 | 0.868 | 263,371 | 4 |
| Card, 1 call | 96.0 | 93.6–97.9 | 0.882 | 67,828 | 2 |
| Card, 4 × 19 | 94.6 | 92.3–96.6 | 0.842 | 81,698 | 4 × 2 |
| Card, repeat | 97.2 | 95.3–99.0 | 0.895 | 134,817 | 3 |
| **Card + output-tool instruction (shipped)** | **96.9** | 92.7–98.7 | 0.908 | **64,670** | 2 |
| same, repeat | 95.3 | 92.8–97.4 | 0.829 | 64,984 | 2 |

None of the runs produced a generic sentence, and every description was within the length range.

## Second repository: axios (JavaScript, 72 modules)

[axios/axios](https://github.com/axios/axios) at `a81d62a`, `lib/**/*.js`, with the same seven areas given to both
routes. The reference is a Sonnet high subagent that read the code (61 tool calls, 240 s). There is no key-fact gold
set for this repository, so the facts term of the score is not computed.

| Measure | Lean route (Haiku medium) | Sonnet subagent |
|---|---:|---:|
| Modules described | 71 of 72 (1 left for the modeler by the gate) | 72 |
| Area agrees with the reference | 0.901 | — |
| Mean similarity to the reference (min) | 0.796 (0.595) | — |
| Own description is the closest one to its reference (top-1) | 0.831 | — |
| Generic sentences | 0 | 0 |
| Length within range | 1.000 | 1.000 |
| Tokens | 70,178 (2 calls, 2 turns each, 3 items retried) | 98,869 reported by the harness |
| Time | 105 s | 240 s |

The seven area disagreements are modules the reference itself flagged as ambiguous (`cookies.js`, `null.js`,
`env/data.js`) or helpers that sit between two areas (`resolveConfig.js`, `isAxiosError.js`, `HttpStatusCode.js`,
`assertParamsAcyclic.js`). The three least similar pairs describe a different true fact of the same module (for
example prototype-pollution safety vs. adapter order in `defaults/index.js`), not a wrong one.

With rich and axios measured, the lean route is the default for name, description and area. The modeler remains the
fallback for anything the route leaves in `descricoes_para_modelador`.

## Reviews are conservative

When `rascunho` lists a module in `pendentes.componentes_revisar` (its public surface changed) and the module already
has a name, a description and a valid area, the route treats it as a review, not as a new description:

- the request carries the current sentence and asks for it back word for word unless the change made it false;
- the script keeps the name and the area whatever the model answers (those may be deliberate modeler decisions);
- a sentence returned unchanged is counted in `mantidos` and gets no new `descrito_por`.

Measured on axios, map made at v1.20.0 and updated to v1.21.1 (99 upstream commits; 27 files changed under `lib/`,
3 of them new; 16 existing modules with a changed public surface):

| | Without the rule | With the rule |
|---|---|---|
| Sentences rewritten, of 16 reviews | 16 | 1 |
| Names changed | 8 | 0 |
| Areas changed against the modeler's choice | 3 | 0 |
| Tokens (one call, 19 modules: 16 reviews + 3 new) | 20,304 | 26,029 |
| Time | 22 s | 34 s |

The one sentence that changed is `lib/helpers/cookies.js`, which gained a Cookie Store API path in that release. A
second run with the rule kept 14 of 16 (26,660 tokens, 37 s): it also added to `lib/core/AxiosError.js` that wrapped
stacks are now inlined. The request is larger because it carries the 16 current sentences. `--todos` turns the rule off and
describes everything from scratch.

## Limits

- Two repositories with a reference, Python and JavaScript. Rust, Java and monorepos are not measured.
- **Truth of the sentences, Go:** on go-chi/chi (35 modules, 31,213 tokens, 34 s) the modeler opened the files and
  checked every sentence: 6 of 35 stated something false about the module and 2 were vague. The score above
  measures form and agreement with a Sonnet reference, not truth, and on rich and axios the sentences were not
  checked against the code one by one. Treat the lean route as a draft the modeler confirms in phase B.
- Only Windows was run end to end; the call is the same `claude` CLI on Linux and macOS but was not exercised there.
- The reference is a Sonnet run, not a human gold set.
- Token counts come from the CLI's `usage` field. They are tokens, not money: billing is the subscription.
