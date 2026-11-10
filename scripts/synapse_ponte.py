"""Ponte da skill lodemap com o Synapse MCP (leitura, observação e proposta).

Subcomandos (só biblioteca padrão; nunca derrubam o pipeline: sem Synapse, gravam o motivo e saem com 0):
  contexto  lições do projeto (synapse_get_learnings_scoped com projeto explícito) e notas da busca híbrida;
            grava .lodemap/synapse-contexto.json para o modelador ler antes de decidir.
  observar  monta a observação do mapa (nota do gate, pendências, contagens) a partir do .lodemap/estado.json e do
            explorador/dados.js; sem --aplicar só mostra; com --aplicar grava pelo synapse_add_observation.

Lição nova NÃO sai daqui: o agente propõe pelo synapse_record_learning_scoped (vai para a quarentena e o dono aprova).

Endereço e token vêm de ~/.claude.json (mcpServers.synapse); o token nunca é impresso nem gravado.

Uso:
  python synapse_ponte.py contexto --repo <repo> --arq <repo>/docs/architecture/structurizr
  python synapse_ponte.py observar --repo <repo> --arq <pasta da arquitetura> [--aplicar]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def project_id(repo: str) -> str | None:
    """Nome canônico do repositório pelo git common-dir (igual no checkout principal e nos worktrees)."""
    try:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    comum = Path(r.stdout.strip())
    raiz = comum.parent if comum.name == ".git" else comum
    return re.sub(r"[^a-z0-9_-]", "_", raiz.name.lower())[:64] or None


def config_synapse(home: Path | None = None) -> tuple[str, dict] | None:
    arq = (home or Path.home()) / ".claude.json"
    try:
        s = json.loads(arq.read_text(encoding="utf-8-sig"))["mcpServers"]["synapse"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    url = s.get("url")
    return (url, dict(s.get("headers") or {})) if url else None


def _corpo(resp) -> dict:
    texto = resp.read().decode("utf-8", errors="replace")
    if "text/event-stream" in (resp.headers.get("Content-Type") or ""):
        dados = [l[5:].strip() for l in texto.splitlines() if l.startswith("data:")]
        texto = dados[-1] if dados else "{}"
    return json.loads(texto or "{}")


class ClienteMcp:
    def __init__(self, url: str, headers: dict, timeout: float = 20):
        self.url, self.timeout, self.id = url, timeout, 0
        self.headers = {**headers, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        r = self._post({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "lodemap", "version": "1"}}})
        sid = r.headers.get("Mcp-Session-Id")
        _corpo(r)
        if sid:
            self.headers["Mcp-Session-Id"] = sid
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}).read()

    def _post(self, msg: dict):
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode("utf-8"), method="POST", headers=self.headers)
        return urllib.request.urlopen(req, timeout=self.timeout)

    def chamar(self, ferramenta: str, args: dict) -> object:
        self.id += 1
        r = _corpo(self._post({"jsonrpc": "2.0", "id": self.id, "method": "tools/call",
                               "params": {"name": ferramenta, "arguments": args}}))
        if "error" in r:
            raise RuntimeError(f"{ferramenta}: {r['error'].get('message', r['error'])}")
        res = r.get("result") or {}
        if res.get("isError"):
            raise RuntimeError(f"{ferramenta}: " + " ".join(c.get("text", "") for c in res.get("content", []))[:300])
        if "structuredContent" in res:
            return res["structuredContent"]
        texto = " ".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        try:
            return json.loads(texto)
        except ValueError:
            return texto


def conectar() -> ClienteMcp:
    cfg = config_synapse()
    if not cfg:
        raise RuntimeError("mcpServers.synapse ausente em ~/.claude.json")
    return ClienteMcp(*cfg)


def _curto(v, n: int) -> str:
    s = re.sub(r"\s+", " ", str(v or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def enxugar_licao(x) -> dict:
    if not isinstance(x, dict):
        return {"texto": _curto(x, 400)}
    return {"id": x.get("id"), "titulo": _curto(x.get("title"), 160), "solucao": _curto(x.get("solution"), 400),
            "invariante": bool(x.get("is_invariant")), "papel": x.get("papel")}


def enxugar_nota(x) -> dict:
    if not isinstance(x, dict):
        return {"texto": _curto(x, 300)}
    return {"entidade": _curto(x.get("entity"), 120), "trecho": _curto(x.get("snippet") or x.get("content"), 300)}


def contexto(repo: str, arq: Path, consulta: str, limite: int, cliente: ClienteMcp | None = None,
             com_globais: bool = False) -> dict:
    pid = project_id(repo)
    saida = {"gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"), "projeto": pid,
             "disponivel": False, "licoes": [], "notas": [], "motivo": None,
             "uso": "Contexto, não verdade: confira no código antes de usar; cite o id da lição usada e registre o "
                    "desfecho com synapse_learning_outcome."}
    if not pid:
        saida["motivo"] = "repositório sem git: project_id indefinido"
    else:
        try:
            c = cliente or conectar()
            filtro = {"projeto": pid, "limit": limite, "incluir_invariantes_globais": com_globais}
            if consulta:
                filtro["query"] = consulta  # com query, só voltam as lições que casam com o texto
            licoes = c.chamar("synapse_get_learnings_scoped", filtro)
            notas = c.chamar("synapse_search_hybrid", {"query": f"{pid} {consulta or 'arquitetura'}", "limit": 8,
                                                        "snippet_chars": 400})
            licoes = licoes.get("learnings", licoes.get("triads", licoes)) if isinstance(licoes, dict) else licoes
            notas = notas.get("results", notas.get("rows", notas)) if isinstance(notas, dict) else notas
            saida["licoes"] = [enxugar_licao(x) for x in licoes] if isinstance(licoes, list) else []
            saida["notas"] = [enxugar_nota(x) for x in notas] if isinstance(notas, list) else []
            saida["disponivel"] = True
        except (OSError, urllib.error.URLError, RuntimeError, ValueError) as e:
            saida["motivo"] = f"Synapse indisponível: {str(e)[:200]}"
    destino = arq / ".lodemap" / "synapse-contexto.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return saida


def montar_observacao(repo: str, arq: Path) -> dict:
    pid = project_id(repo) or arq.resolve().parents[2].name.lower()
    estado = {}
    try:
        estado = json.loads((arq / ".lodemap" / "estado.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        pass
    q = estado.get("qualidade") or {}
    try:
        commit = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        commit = None
    pend = q.get("pendencias") or []
    texto = (f"Mapa de arquitetura (lodemap) do projeto {pid} no commit {commit or '?'}: gate de qualidade "
             f"{q.get('total', '?')} ({'aprovado' if q.get('aprovado') else 'reprovado ou não medido'}); "
             f"pendências: {', '.join(map(str, pend)) if pend else 'nenhuma'}. Fonte: {arq.as_posix()}/.lodemap/estado.json.")
    return {"entity": f"arquitetura:{pid}", "content": texto,
            "tags": ["lodemap", pid, "gate-aprovado" if q.get("aprovado") else "gate-pendente"]}


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("contexto")
    c.add_argument("--repo", default=".")
    c.add_argument("--arq", default="docs/architecture/structurizr")
    c.add_argument("--consulta", default="", help="filtra as lições por texto; vazio = todas as do projeto")
    c.add_argument("--limite", type=int, default=40)
    c.add_argument("--com-globais", action="store_true", help="inclui as invariantes globais (a sessão já as recebe)")
    o = sub.add_parser("observar")
    o.add_argument("--repo", default=".")
    o.add_argument("--arq", default="docs/architecture/structurizr")
    o.add_argument("--aplicar", action="store_true")
    a = ap.parse_args(argv)
    arq = Path(a.arq) if Path(a.arq).is_absolute() else Path(a.repo) / a.arq
    if a.cmd == "contexto":
        s = contexto(a.repo, arq, a.consulta, a.limite, com_globais=a.com_globais)
        print(json.dumps({"projeto": s["projeto"], "disponivel": s["disponivel"], "licoes": len(s["licoes"] or []),
                          "notas": len(s["notas"] or []), "motivo": s["motivo"],
                          "arquivo": str(arq / ".lodemap" / "synapse-contexto.json")}, ensure_ascii=False))
        return 0
    obs = montar_observacao(a.repo, arq)
    print(json.dumps(obs, ensure_ascii=False, indent=2))
    if not a.aplicar:
        print("(plano: nada gravado; use --aplicar)")
        return 0
    try:
        r = conectar().chamar("synapse_add_observation", obs)
        print("gravado:", json.dumps(r, ensure_ascii=False)[:300])
    except (OSError, urllib.error.URLError, RuntimeError, ValueError) as e:
        print(f"não gravado (Synapse indisponível): {str(e)[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
