# Contributing

Thanks for helping. Keep changes small and verifiable.

1. **Python 3.11+, standard library only** for everything under `lodemap/`, `hooks/` and `scripts/`.
2. **Run the tests** before opening a pull request:
   `python -m pytest tests -q -p no:cacheprovider`
   The installer tests run against a temporary HOME; never test against your real `~/.claude`.
3. **Installer changes** must keep the contract: dry run by default, a manifest with sha256 before/after for every
   touched file, byte-exact revert, and refusal (without `--forcar`) to change anything owned by someone else.
   A second `instalar` right after `--aplicar` must report 0 operations.
4. **Map agent changes**: edit `agents/lodemap-*.md`. The installer copies them verbatim to `~/.claude/agents/`, and
   `tests/test_instalador.py` checks that all six are installed by the `minimo` profile.
5. **Claims need evidence**: a cost, a limit or a behavior of Claude Code in the docs or README needs a source (a
   measurement file or the official documentation).
6. Write commit messages that say what changed and why.

## Tests and CI

- Run the suite from the repository root with `python -m pytest -q` (`pytest.ini` limits collection to `tests/`).
- `templates/tests/` holds tests that are copied into the *user's* project when a map is created; they expect that
  project's layout (`docs/architecture/...`), so most of them do not run from this repository. Only
  `test_codegraph_ponte.py` and `test_qualidade.py` run standalone from the root; run them explicitly:
  `python -m pytest -q templates/tests/test_codegraph_ponte.py templates/tests/test_qualidade.py`.
- CI is CircleCI (`.circleci/config.yml`): Linux on Python 3.11 and 3.12, plus a Windows job.
- Report security problems as described in `SECURITY.md`, not in public issues.
