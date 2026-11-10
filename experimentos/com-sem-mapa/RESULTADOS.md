# Result: agent with vs without the map

Run on 2026-11-10 under the rules fixed in `PREREGISTRO.md`, which was committed before the run. There were 96
executions and none failed. The raw CLI output of every run is in `resultados/brutos/`. The numbers below come from
`python avaliar.py` and are saved in `resultados/resumo.json`.

## Verdict

| Hypothesis | Rule | Result |
|---|---|---|
| H1, the map saves tokens | A lower on ≥ 12 of 16 tasks | **Not demonstrated.** A was lower on 8 of 16 (p = 0.60). The median ratio A/B was 0.99. |
| H2, the map does not hurt accuracy | recall A ≥ B − 0.05, wrong files A ≤ B + 0.25 | **Demonstrated.** Recall was 0.991 for A and 0.977 for B. Wrong files averaged 0.19 in both arms. |
| H3, the map improves accuracy | A better on ≥ 12 non-tied tasks | **Not demonstrated.** A was better on 3 tasks and worse on none (p = 0.125). The other 13 tasks tied. |

Averages per run:

| Arm | Tokens | Seconds | Turns | Output tokens |
|---|---|---|---|---|
| A (map) | 21,303 | 11.5 | 4.71 | 770 |
| B (no map) | 21,291 | 10.5 | 4.27 | 682 |

With Sonnet, Read/Grep/Glob, and questions that have a file answer, the map neither saved tokens nor cost tokens. On
these two repositories (35 and 69 modules), grep finds the files about as cheaply as reading the map. Arm A took about
half a turn more per run, which is consistent with it opening the map first and then confirming in the code.

The accuracy gains are small and all in the same direction. They show up where the question needs the whole picture:
- A1, XSRF across three helpers: B missed a file in one of 3 runs.
- A7, every user of AxiosHeaders.
- C8, every middleware that rewrites the path.

The subgroup data points the same way: description only, as pre-registered, with no test.

| Subgroup | Tasks | Median tokens A/B | Recall A / B |
|---|---|---|---|
| Localization (C1–C6, A1–A6) | 12 | 1.03 | 1.000 / 0.991 |
| Impact (C7, C8, A7, A8) | 4 | 0.92 | 0.965 / 0.934 |

## Defects in the answer key, found after the run

The rules were fixed before the run, so the key is not changed. The defects are reported here.

- **C7.** Both arms named the same 3 files under `_examples/` in every run. Those files do use the routing context. The
  key asked for "non-test source files" and did not list examples, so both arms are equally penalised and the
  comparison is unchanged.
- **A7.** `lib/helpers/parseHeaders.js` mentions AxiosHeaders only inside a comment (`RawAxiosHeaders`), so it should
  not be in the key. Without it, recall on A7 is 0.97 for A and 0.94 for B, and the verdicts do not change.

## What this means for Lodemap

- The map is not a token saver for an agent that already has grep, at least on repositories of this size. The README
  and the page must not claim it is.
- The map did not make the agent worse, and it helped a little on "who depends on X" questions. A larger set of impact
  tasks is the next measurement worth making.
- The map's demonstrated value is still for people (explorer, reader, coverage gate in CI) and for keeping architecture
  documentation true. It has not been demonstrated as an agent accelerator.

## Limits

- One model (Sonnet, medium effort), two repositories, and 16 tasks with 3 repetitions each.
- Tool calls were not logged (`--output-format json` returns only the result), so how often arm A opened the map is
  inferred from the turn count and not counted.
- The tasks have file answers; an editing task could behave differently.
- The map text is in English; the pointer paragraph is the one in `rodar.py`.
