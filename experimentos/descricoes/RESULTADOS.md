# Are the lean route's sentences true? (2026-11-10)

## Question

`scripts/descrever.py` writes one sentence per module with Haiku. The rich and axios scores measure form and agreement
with a reference, not truth. This experiment asks how many of the written sentences are false when someone reads the
code, and whether the truth check added on 2026-11-10 lowers that number.

The truth check has three parts:
- quoted evidence;
- code names that must exist in the module;
- a second Haiku call that reads the code and corrects or rejects sentences.

`references/rota-enxuta.md` describes it.

## Method

- **Repositories:** go-chi/chi (36 modules) and axios/axios (72 modules), at the commits of the public demos.
- **Runs:** each run starts from a fresh `git archive` copy and describes every module from scratch (`--todos`).
  - "Before" is the code at `c695c0e`.
  - "With the check" is the working tree of this change.
  - There are two independent runs per repository.
- **Judge:** Sonnet, effort medium, with Read, Grep and Glob, run inside the copy (`julgar.py`), in batches of 12
  sentences. Verdicts: `verdadeira`, `falsa`, `vaga`. The judge is a different model from the writer, and it never
  saw the reviewer's verdicts.
- **What is counted:** a sentence the route left for the modeler was not written by the route, so it is excluded
  (`resumir.py`). Tokens are those of `descrever.py`; the judge's tokens are not included.

Raw verdicts and reports: `dados/`.

## Results

| Run | Written | False (judge) | Left for the modeler | Reviewer: false / corrected / uncertain | Tokens |
|---|---:|---:|---:|---|---:|
| chi, before | 36 | 5 | 0 | — | 32,288 |
| chi, check, run 1 | 36 | 2 | 0 | 3 / 3 / 0 | 123,016 |
| chi, check, run 2 | 36 | 1 | 0 | 7 / 7 / 0 | 119,904 |
| axios, before | 72 | 10 | 0 | — | 56,127 |
| axios, check, run 1 | 69 | 2 | 3 | 10 / 8 / 1 | 205,696 |
| axios, check, run 2 | 72 | 0 | 0 | 6 / 6 / 3 | 205,743 |

- **Before:** 15 false of 108 (13.9%).
- **With the check:** 5 false of 213 (2.3%), across 4 runs.
- **Cost:** a full description pass costs about 3.7 times the tokens:
  - before: 88,415 for both repositories;
  - with the check: 328,712 for run 1 and 325,647 for run 2.

What remained false:
- chi run 1: `middleware/content_charset.go` and `middleware/logger.go`.
- chi run 2: `middleware/logger.go`.
- axios run 1: `lib/core/buildFullPath.js` and `lib/core/settle.js`.

**One verdict is disputable.** The `logger.go` sentence says color is used only when stdout is a TTY. The judge
read only `init()` and marked it false. However, the doc comment at `middleware/logger.go:25` states it, and
`middleware/terminal.go:56` checks `IsTTY` before writing color. Counted as the judge said; without it, 3 of 213.

## Reading

- The check cuts false sentences by about a factor of six (13.9% → 2.3%) in these two repositories.
- It is not zero. Phase B still asks the modeler to confirm sentences against the code.
- Most false sentences before the check invented a purpose ("so that …") or stated a detail too precisely. The first
  version of the reviewer missed 7 of 10 such sentences on axios. Only after both prompts stopped asking for "the why"
  did it catch them. A reviewer prompt that asks for reasons undoes the check.
- **Limits:**
  - two repositories, two runs each, one judge model;
  - the judge can be wrong, as the `logger.go` verdict shows;
  - the before arm has one run per repository.
