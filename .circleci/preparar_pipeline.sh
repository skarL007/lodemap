#!/usr/bin/env bash
# Prepares the end-to-end pipeline test (tests/test_exemplo_axios.py) on Linux and macOS.
# - Structurizr CLI, pinned release, checked by sha256, into $STRUCTURIZR_FERRAMENTAS/cli (default ~/.structurizr/cli)
# - axios at v1.21.1, checked by commit, into $LODEMAP_EXEMPLO_AXIOS (default ~/axios)
# Java (17+) must already be on PATH; the CI job installs it per OS.
set -euo pipefail

CLI_VERSAO="v2025.11.09"
CLI_SHA256="f5365a463fc44d539ed19bec00c48ba1e1ecda0ccfd1ba40d2e7472d264eb79a"
AXIOS_TAG="v1.21.1"
AXIOS_COMMIT="335e2f8464f58a3ab485486b8d6964fea3e3f30a"

FERR="${STRUCTURIZR_FERRAMENTAS:-$HOME/.structurizr}"
AXIOS="${LODEMAP_EXEMPLO_AXIOS:-$HOME/axios}"

java -version
tmp="$(mktemp -d)"
curl -fsSL -o "$tmp/structurizr-cli.zip" \
  "https://github.com/structurizr/cli/releases/download/${CLI_VERSAO}/structurizr-cli.zip"
if command -v sha256sum >/dev/null; then
  echo "${CLI_SHA256}  $tmp/structurizr-cli.zip" | sha256sum -c -
else
  echo "${CLI_SHA256}  $tmp/structurizr-cli.zip" | shasum -a 256 -c -
fi
mkdir -p "$FERR/cli"
unzip -q -o "$tmp/structurizr-cli.zip" -d "$FERR/cli"
chmod +x "$FERR/cli/structurizr.sh"
rm -rf "$tmp"

if [ ! -d "$AXIOS/.git" ]; then
  git clone -q --depth 1 --branch "$AXIOS_TAG" https://github.com/axios/axios.git "$AXIOS"
fi
test "$(git -C "$AXIOS" rev-parse HEAD)" = "$AXIOS_COMMIT"
echo "pipeline ready: CLI ${CLI_VERSAO} in $FERR/cli, axios ${AXIOS_TAG} in $AXIOS"
