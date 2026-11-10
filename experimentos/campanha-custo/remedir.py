"""Re-measures every finished run with the current `medir()` (coverage test with --noconftest) and updates its JSON.

The campaign process loaded `medir()` before the --noconftest fix, so a project with its own conftest (click) was
recorded as a coverage failure. This keeps the old value under `cobertura_original` and writes the new one.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rodar_campanha as rc  # noqa: E402

for f in sorted((rc.BASE / "resultados").glob("*.json")):
    if f.name.startswith("piloto-"):
        continue
    r = json.loads(f.read_text(encoding="utf-8"))
    m = rc.medir(Path(r["pasta"]))
    if "cobertura_original" not in r:
        r["cobertura_original"] = {"cobertura": r.get("cobertura"), "cobertura_ok": r.get("cobertura_ok")}
    r.update(m)
    f.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f.stem, r.get("qualidade_total"), r.get("componentes"), r.get("cobertura_ok"), r.get("cobertura"))
