# Pre-registration: agent with vs without the map

Written on 2026-11-10, before the main run. A pilot was run first on 2 tasks (C1 and A1, 1 repetition per arm) only to
check the setup. Its numbers are in `resultados-piloto/` and are excluded from the analysis. Four "impact" tasks (C7, C8,
A7, A8) were added after the pilot and before the main run.

## Question

When a coding agent answers a code-navigation question, does it reach the same or a better answer with fewer tokens
when the repository carries a Lodemap map and the agent is told about it?

## Setup

- **Repositories.** Public copies at a fixed commit: go-chi/chi (Go, 35 modules) and axios (JavaScript, 69 modules).
  Each has its committed Lodemap map in `docs/architecture/`.
- **Arm A.** Full copy, plus one paragraph in the system prompt that points to the map. This is the text a user would
  put in CLAUDE.md.
- **Arm B.** The same copy with `docs/architecture/` deleted and without the paragraph.
- **Agent.** `claude -p --model sonnet --effort medium`, Claude Code 2.1.319, accessed by subscription.
  - Tools: Read, Grep and Glob only.
  - No MCP, no user settings, hooks or CLAUDE.md (`--setting-sources ""`), and no persisted session.
  - The agent answers through the structured-output tool: a list of files and a justification.
- **Tasks.** 16 questions in `tarefas.json`: 12 localization questions (C1–C6, A1–A6) and 4 impact questions (C7, C8,
  A7, A8). Each answer key was taken from the code (grep and reading), never from the map.
  - `deve`: the files the answer must name.
  - `aceita`: files that may appear without counting as errors.
- **Repetitions.** 3 per task per arm, which makes 96 runs. Run order is shuffled with seed 20261110, so the two arms
  are interleaved in time.

## Metrics (per run)

- **recall**: share of the `deve` files that the answer names.
- **wrong**: files named that are in neither `deve` nor `aceita`.
- **tokens**: input + cache creation + cache read + output, as reported by the CLI's `usage` field.
- **output tokens**, **turns** and **seconds**.

## Hypotheses and decision rules

Each run's metrics are averaged over the 3 repetitions of its task and arm. Tasks are then compared in pairs (A vs B).

- **H1, economy.** Arm A uses fewer tokens.
  - Demonstrated if A has lower mean tokens on at least 12 of 16 tasks. This is a one-sided sign test, p = 0.038.
  - Also report the median, over tasks, of the ratio tokens_A / tokens_B.
- **H2, accuracy not worse.** Mean recall of A ≥ mean recall of B − 0.05, and mean wrong files of A ≤ B + 0.25.
- **H3, accuracy better.** A has a higher mean recall on more tasks than it has a lower one, with at least 12 of the
  non-tied tasks in its favour. Otherwise H3 is not demonstrated.
- **Subgroups.** Localization and impact tasks are reported separately, as description only, with no test.

## What this does not measure

- Whether a code change made with the map is better.
- Other models, or agents that have a code index such as CodeGraph.
- Monorepos.
- Tasks with no clear file answer.

The result is published whatever it is.
