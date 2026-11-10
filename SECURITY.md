# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub: open the **Security** tab of
[skarL007/lodemap](https://github.com/skarL007/lodemap) and choose **Report a vulnerability** (private vulnerability
reporting / Security Advisories). Do not open a public issue for a security problem. Include the version
(`python -m lodemap --version`), your OS, and the steps to reproduce.

## Scope

In scope: the installer (`python -m lodemap instalar` / `reverter`, which edits files under `~/.claude`), the git hook
installed in user repositories, and the scripts in `scripts/`, `hooks/` and `templates/`.

Out of scope: vulnerabilities in Claude Code, Structurizr CLI, Graphviz or Java themselves; report those upstream.

## What the tool does with data

- The scripts run locally and make no network calls. `python -m lodemap doctor` and `plano` are read-only and spend
  0 tokens.
- Steps that use a model are run by Claude Code and send the files they read to Anthropic under your Claude Code
  account. They run only after you consent (`python -m lodemap consentir`), and the consent can be revoked.
- The installer never changes a file owned by someone else without `--forcar`, and every change is recorded in a
  manifest with sha256 so `reverter` can undo it.
