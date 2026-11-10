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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lodemap.idioma import opcao, t, usar_mapa  # noqa: E402


def passo(nome: str, ok: bool, detalhe: str = "") -> bool:
    print(f"[{'ok' if ok else t('FALHOU', 'FAILED')}] {nome}" + (f": {detalhe}" if detalhe else ""))
    return ok


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=t("Checagem final do mapa de arquitetura: JS válido e explorador abrindo "
                                               "sem erro.",
                                               "Final check of the architecture map: valid JS and the explorer opening "
                                               "without errors."))
    ap.add_argument("--arq", "--arch", required=True, help=t("pasta structurizr do projeto", "the project's structurizr folder"))
    ap.add_argument(*opcao("--no-browser", "--sem-navegador"), dest="sem_navegador", action="store_true",
                    help=t("pula a etapa do navegador (Playwright)", "skip the browser step (Playwright)"))
    ap.add_argument(*opcao("--screenshots", "--capturas"), dest="capturas", metavar=t("PASTA", "DIR"),
                    help=t("pasta onde salvar as capturas de tela", "folder where to save the screenshots"))
    ap.add_argument(*opcao("--quality", "--qualidade"), dest="qualidade", action="store_true",
                    help=t("roda também o qualidade.py (gate da linha de base)",
                           "also run qualidade.py (the baseline gate)"))
    ap.add_argument("--repo", help=t("com --qualidade: raiz do repositório (padrão: raiz do git da pasta da arquitetura)",
                                     "with --qualidade: repository root (default: the git root of the architecture folder)"))
    a = ap.parse_args(argv)
    arq = Path(a.arq).resolve()
    usar_mapa(arq)
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
                    tudo_ok &= passo(t("explorador/index.html existe", "explorador/index.html exists"), False, str(indice))
                else:
                    print(t(f"[pulado] node --check de {pagina}/index.html: página ausente",
                            f"[skipped] node --check of {pagina}/index.html: page missing"))
                continue
            html = indice.read_text(encoding="utf-8")
            blocos = re.findall(r"<script>(.*?)</script>", html, re.S)
            with tempfile.TemporaryDirectory() as tmp:
                js = Path(tmp) / f"{pagina}-inline.js"
                js.write_text("\n".join(blocos), encoding="utf-8")
                r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
            tudo_ok &= passo(t(f"node --check do script de {pagina}/index.html",
                               f"node --check of the script in {pagina}/index.html"), r.returncode == 0,
                             r.stderr.strip()[:300])
    else:
        print(t("[pulado] node --check: node não está no PATH", "[skipped] node --check: node is not on PATH"))

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
            tudo_ok &= passo(t("qualidade (gate do baseline)", "quality (baseline gate)"), ok,
                             t(f"total {q['total']} (linha de base {g.get('totalBaselineComparavel', '?')}, "
                               f"mínimo {g.get('minimoTotal', '?')})",
                               f"total {q['total']} (baseline {g.get('totalBaselineComparavel', '?')}, "
                               f"minimum {g.get('minimoTotal', '?')})"))
            if not ok:
                print(json.dumps({"falhas": g.get("falhas"), "reprovados": q.get("reprovados")}, ensure_ascii=False, indent=1))
        except (ValueError, KeyError):
            tudo_ok &= passo(t("qualidade (gate do baseline)", "quality (baseline gate)"), False,
                             (r.stderr or r.stdout).strip()[:300])

    # 3. navegador
    if a.sem_navegador:
        return 0 if tudo_ok else 1
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(t("[pulado] navegador: instale com 'pip install playwright' e 'playwright install chromium'",
                "[skipped] browser: install with 'pip install playwright' and 'playwright install chromium'"))
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
            tudo_ok &= passo(t(f"fluxo {fluxo}", f"flow {fluxo}"), f"{n}/" in pg.inner_text("#legendaPasso"),
                             pg.inner_text("#legendaPasso")[:90])
        if comp:
            pg.goto(url + "#" + comp["ident"])
            pg.reload()
            pg.wait_for_timeout(1200)
            tudo_ok &= passo(t(f"foco por #{comp['ident']}", f"focus by #{comp['ident']}"),
                             comp["nome"] in pg.inner_text("#detalhes"))
            if capt:
                pg.screenshot(path=str(capt / "foco.png"))
        b.close()
    tudo_ok &= passo(t("explorador sem erro de JS", "explorer without JS errors"), not erros, "; ".join(erros[:5]))
    return 0 if tudo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
