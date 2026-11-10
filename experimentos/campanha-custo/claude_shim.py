"""Passes every call through to the real `claude` and appends its cost line to $LODEMAP_CAMP_LOG.

`descrever.py` runs `claude -p` itself, outside the orchestrator's session. This shim (set as LODEMAP_CLAUDE) is how
the campaign counts those calls. It changes nothing in the call: same arguments, same stdin, same stdout and exit code.
"""
import json
import os
import shutil
import subprocess
import sys

real = os.environ.get("LODEMAP_CAMP_REAL_CLAUDE") or shutil.which("claude")
entrada = sys.stdin.buffer.read() if not sys.stdin.isatty() else None
r = subprocess.run([real, *sys.argv[1:]], input=entrada, capture_output=True)
log = os.environ.get("LODEMAP_CAMP_LOG")
if log:
    try:
        j = json.loads(r.stdout.decode("utf-8", "replace"))
        linha = {"total_cost_usd": j.get("total_cost_usd"), "modelUsage": j.get("modelUsage"), "usage": j.get("usage"),
                 "duration_ms": j.get("duration_ms"), "is_error": j.get("is_error")}
    except (json.JSONDecodeError, ValueError):
        linha = {"nao_json": True, "rc": r.returncode}
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha) + "\n")
sys.stdout.buffer.write(r.stdout)
sys.stderr.buffer.write(r.stderr)
sys.exit(r.returncode)
