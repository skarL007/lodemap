"""Checagem final do mapa de arquitetura: JS válido e explorador abrindo sem erro.

Uso: python verificar.py --arq <pasta da arquitetura>
                         [--sem-navegador] [--capturas <pasta>] [--qualidade]

1. node --check em explorador/dados.js e nos <script> embutidos do explorador e do leitor;
2. abre o explorador no Chromium headless (Playwright): sem pageerror nem console.error, com o grafo desenhado,
   um fluxo tocado por 3 passos e o foco por #<identificador> do primeiro componente com nota.
3. com --qualidade (opcional): roda qualidade.py (rubrica de nota por critério contra a linha de base) e falha
   se reprovar no gate; a lista de reprovados vai para a saída.
Sai com 1 se algo falhar. A etapa 2 é pulada (com aviso) se o Playwright não estiver instalado.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def passo(nome: str, ok: bool, detalhe: str = "") -> bool:
    print(f"[{'ok' if ok else 'FALHOU'}] {nome}" + (f": {detalhe}" if detalhe else ""))
    return ok


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arq", required=True)
    ap.add_argument("--sem-navegador", action="store_true")
    ap.add_argument("--capturas")
    ap.add_argument("--qualidade", action="store_true", help="roda também o qualidade.py (gate da linha de base)")
    ap.add_argument("--repo", help="com --qualidade: raiz do repositório (padrão: raiz do git da pasta da arquitetura)")
    a = ap.parse_args(argv)
    arq = Path(a.arq).resolve()
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig"))
    tudo_ok = True

    # 1. node --check
    node = shutil.which("node")
    if node:
        dados = arq / "explorador" / "dados.js"
        r = subprocess.run([node, "--check", str(dados)], capture_output=True, text=True)
        tudo_ok &= passo("node --check dados.js", r.returncode == 0, r.stderr.strip()[:300])
        for pagina in ("explorador", "leitor"):
            indice = arq / pagina / "index.html"
            if not indice.is_file():
                if pagina == "explorador":
                    tudo_ok &= passo("explorador/index.html existe", False, str(indice))
                else:
                    print(f"[pulado] node --check de {pagina}/index.html: página ausente")
                continue
            html = indice.read_text(encoding="utf-8")
            blocos = re.findall(r"<script>(.*?)</script>", html, re.S)
            with tempfile.TemporaryDirectory() as tmp:
                js = Path(tmp) / f"{pagina}-inline.js"
                js.write_text("\n".join(blocos), encoding="utf-8")
                r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
            tudo_ok &= passo(f"node --check do script de {pagina}/index.html", r.returncode == 0, r.stderr.strip()[:300])
    else:
        print("[pulado] node --check: node não está no PATH")

    # 2. qualidade (opcional)
    if a.qualidade:
        cmd = [sys.executable, str(Path(__file__).resolve().parent / "qualidade.py"), "--arq", str(arq),
               "--listar-reprovados"]
        if a.repo:
            cmd += ["--repo", a.repo]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        try:
            q = json.loads(r.stdout)
            g = q.get("gate", {})
            ok = r.returncode == 0
            tudo_ok &= passo("qualidade (gate do baseline)", ok,
                             f"total {q['total']} (linha de base {g.get('totalBaselineComparavel', '?')}, mínimo {g.get('minimoTotal', '?')})")
            if not ok:
                print(json.dumps({"falhas": g.get("falhas"), "reprovados": q.get("reprovados")}, ensure_ascii=False, indent=1))
        except (ValueError, KeyError):
            tudo_ok &= passo("qualidade (gate do baseline)", False, (r.stderr or r.stdout).strip()[:300])

    # 3. navegador
    if a.sem_navegador:
        return 0 if tudo_ok else 1
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[pulado] navegador: instale com 'pip install playwright' e 'playwright install chromium'")
        return 0 if tudo_ok else 1
    texto = (arq / "explorador" / "dados.js").read_text(encoding="utf-8")
    dados = json.loads(texto[texto.index("=") + 1:].strip().rstrip(";"))
    comp = next((e for e in dados["elementos"] if e["tipo"] == "Componente" and e.get("ident")), None)
    fluxo_v = next((v for v in dados["visoes"] if v["tipo"] == "dinamica" and v.get("fluxo")), None)
    fluxo = fluxo_v["chave"] if fluxo_v else None
    url = (arq / "explorador" / "index.html").as_uri()
    erros: list[str] = []
    capt = Path(a.capturas) if a.capturas else None
    if capt:
        capt.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 950})
        pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
        pg.on("console", lambda m: erros.append(f"console: {m.text}") if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_selector("#cy canvas", timeout=30000)
        pg.wait_for_timeout(800)
        if capt:
            pg.screenshot(path=str(capt / "inicial.png"))
        if fluxo:
            pg.click(f"[data-visao='{fluxo}']")
            pg.wait_for_timeout(600)
            n = min(3, len(fluxo_v["fluxo"]))
            for _ in range(n):
                pg.click("#passoProx")
                pg.wait_for_timeout(200)
            tudo_ok &= passo(f"fluxo {fluxo}", f"{n}/" in pg.inner_text("#legendaPasso"), pg.inner_text("#legendaPasso")[:90])
        if comp:
            pg.goto(url + "#" + comp["ident"])
            pg.reload()
            pg.wait_for_timeout(1200)
            tudo_ok &= passo(f"foco por #{comp['ident']}", comp["nome"] in pg.inner_text("#detalhes"))
            if capt:
                pg.screenshot(path=str(capt / "foco.png"))
        b.close()
    tudo_ok &= passo("explorador sem erro de JS", not erros, "; ".join(erros[:5]))
    return 0 if tudo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
