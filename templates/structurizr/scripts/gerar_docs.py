"""Gera os documentos derivados da arquitetura a partir do workspace.json exportado.

Uso: python gerar_docs.py <workspace.json> <pasta docs>

Produz:
  02-mapa-de-status.md               quanto está pronto, por status e por container, e o que falta
  90-catalogo-de-observabilidade.md  métricas, eventos, logs e painéis por componente
  91-metricas-e-benchmarks.md        métricas curadas (atual × meta, histórico e origem de cada número)
  92-indice-de-decisoes.md           índice dos ADRs (adrs/*.md no formato único), no lugar de listas manuais
Os nomes dos elementos levam ao mapa (../explorador/index.html#<identificador>). Só usa a biblioteca padrão.
O texto sai no idioma do lodemap.json ("idioma": "pt" ou "en"; padrão pt). Os nomes dos arquivos não mudam.
Não edite os arquivos gerados à mão: mude o DSL (ou o ADR) e rode de novo.
"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arq_comum as ac  # noqa: E402
import gerar_leitor as gl  # noqa: E402

ORDEM_STATUS = ["Pronto", "Em andamento", "Aguardando", "Planejado", "Fora do foco"]
MAPA = "../explorador/index.html"
IDIOMA = ac.IDIOMA_PADRAO  # main() troca pelo "idioma" do lodemap.json
STATUS_ADR_EN = {"proposta": "Proposed", "aceita": "Accepted", "substituida": "Superseded", "rejeitada": "Rejected"}

TEXTOS = {
    "pt": {
        "cab": "<!-- Gerado por scripts/gerar_docs.py a partir do workspace.json. Não edite à mão. -->\n\n",
        "signif": {"Pronto": "no código, testado e integrado", "Em andamento": "alguém está mexendo agora",
                   "Aguardando": "espera revisão, decisão ou outra equipe",
                   "Planejado": "existe no design, ainda não no código", "Fora do foco": "existe, mas não é prioridade"},
        "st_titulo": "# Mapa de status\n\n",
        "st_resumo": "**{prontos} de {total} componentes {v_pronto} ({pct}).** {andamento} {v_andamento} em andamento "
                     "e {planejados} {v_planejado} só no design. {v_conts} {conts} {s_conts}{sem}.\n\n",
        "plural": {"v_pronto": ("está pronto", "estão prontos"), "v_andamento": ("está", "estão"),
                   "v_planejado": ("existe", "existem"), "v_conts": ("É", "São"),
                   "s_conts": ("container", "containers"), "dele": ("dele", "deles")},
        "st_sem": ", {n} {dele} sem componentes detalhados",
        "st_fonte": "O status vem da propriedade `status` de cada elemento no DSL e muda no mesmo commit que muda o "
                    "código. Clique no nome de um componente para vê-lo no mapa.\n\n",
        "st_quanto": "## Quanto está pronto\n\n",
        "col_status": ["Status", "Significado", "Componentes", "Parte"],
        "st_por_cont": "\n## Por container\n\nQuantos componentes de cada container estão em cada status.\n\n",
        "col_cont": ["Container", "Total"],
        "st_zero": "\n“·” quer dizer zero. Fora da tabela, por não terem componentes detalhados no modelo: ",
        "sem_status": "sem status",
        "st_falta": "\n## O que falta\n\nOs componentes que ainda não estão prontos, agrupados por status.\n",
        "col_falta": ["Componente", "Container", "Grupo", "Código", "Equipe", "Nota"],
        "st_cont_np": "\n## Containers que não estão prontos\n\n",
        "col_cont_np": ["Container", "Status", "Nota"],
        "ob_titulo": "# Catálogo de observabilidade\n\n",
        "ob_resumo": "**{obs} elementos declaram o que dá para medir ou ver; {design} deles ainda só no design.** "
                     "Entre os componentes, {com} de {comps} ({pct}) têm observabilidade declarada.\n\n"
                     "Cada linha diz onde olhar: métricas, eventos, logs e painéis. Um elemento `{planejado}` tem a "
                     "observabilidade só no design: o nome existe, o código ainda não.\n",
        "col_obs": ["Elemento", "Status", "O que observar", "Métricas", "Existe no código"],
        "so_design": "não, só no design", "sim": "sim",
        "ob_area": "\n## Cobertura por área\n\nQuantos componentes de cada área dizem como ser observados.\n\n",
        "col_area": ["Área", "Componentes", "Com observabilidade", "Parte"],
        "me_titulo": "# Métricas e benchmarks\n\n",
        "me_vazio": "Nenhuma métrica curada ainda. Registre números medidos em `metricas/metricas.json`, com a origem "
                    "de cada um.\n",
        "me_resumo": "**{n} métricas; {passa} atingem a meta e {falha} ainda não.** "
                     "Cada número está ligado aos componentes que ele avalia e à evidência de onde saiu.\n\n"
                     "A fonte é `metricas/metricas.json`, um resumo curado: só números e a origem (arquivo de evidência, "
                     "ramo, commit e campo), nunca dados pessoais nem respostas. O teste "
                     "`tests/test_arquitetura_metricas.py` confere cada número contra o JSON no commit citado.\n",
        "sem_veredito": "sem veredito", "sem_grupo": "Sem grupo", "sem_meta": "sem meta",
        "passa": "**passa**", "falha": "falha",
        "me_atual": "\n## Situação atual\n",
        "col_me": ["Métrica", "Atual", "Meta", "Veredito", "Componentes", "Data"],
        "me_hist": "\n## Histórico e origem\n\nDe onde veio cada número, da medição mais antiga para a atual.\n",
        "atual": "atual: ", "campo": "campo",
        "col_hist": ["Medição", "Valor", "Data", "Origem"],
        "de_titulo": "# Índice de decisões\n\n",
        "de_vazio": "Nenhuma decisão registrada ainda. Crie `adrs/0001-<titulo>.md` no formato único (ver o ADR "
                    "modelo).\n",
        "de_resumo": "**{n} decisões: {resumo}.** Da mais nova para a mais antiga. Cada linha vem do cabeçalho do ADR; "
                     "no leitor (`leitor/index.html#decisoes`) elas aparecem numa linha do tempo.\n\n",
        "de_problemas": "> **Problemas no formato:** ",
        "substitui": "substitui ", "substituida_por": "substituída por ",
        "col_de": ["ADR", "Decisão", "Status", "Data", "Elementos", "Relação"],
        "fim": "{n} elementos lidos; {k} documentos gerados em {d}",
    },
    "en": {
        "cab": "<!-- Generated by scripts/gerar_docs.py from workspace.json. Do not edit by hand. -->\n\n",
        "signif": {"Pronto": "in the code, tested and integrated", "Em andamento": "someone is working on it now",
                   "Aguardando": "waiting for review, a decision or another team",
                   "Planejado": "in the design, not in the code yet", "Fora do foco": "exists, but is not a priority"},
        "st_titulo": "# Status map\n\n",
        "st_resumo": "**{prontos} of {total} components {v_pronto} done ({pct}).** {andamento} {v_andamento} in "
                     "progress and {planejados} {v_planejado} only in the design. There {v_conts} {conts} "
                     "{s_conts}{sem}.\n\n",
        "plural": {"v_pronto": ("is", "are"), "v_andamento": ("is", "are"), "v_planejado": ("exists", "exist"),
                   "v_conts": ("is", "are"), "s_conts": ("container", "containers"), "dele": ("it", "them")},
        "st_sem": ", {n} of {dele} with no detailed components",
        "st_fonte": "The status comes from each element's `status` property in the DSL and changes in the same commit "
                    "as the code. Click a component's name to see it on the map.\n\n",
        "st_quanto": "## How much is done\n\n",
        "col_status": ["Status", "Meaning", "Components", "Share"],
        "st_por_cont": "\n## By container\n\nHow many components of each container are in each status.\n\n",
        "col_cont": ["Container", "Total"],
        "st_zero": "\n“·” means zero. Left out of the table because they have no detailed components in the model: ",
        "sem_status": "no status",
        "st_falta": "\n## What is left\n\nThe components that are not done yet, grouped by status.\n",
        "col_falta": ["Component", "Container", "Group", "Code", "Team", "Note"],
        "st_cont_np": "\n## Containers that are not done\n\n",
        "col_cont_np": ["Container", "Status", "Note"],
        "ob_titulo": "# Observability catalog\n\n",
        "ob_resumo": "**{obs} elements declare what can be measured or seen; {design} of them only in the design so "
                     "far.** Among the components, {com} of {comps} ({pct}) declare observability.\n\n"
                     "Each row says where to look: metrics, events, logs and dashboards. A `{planejado}` element has "
                     "observability only in the design: the name exists, the code does not yet.\n",
        "col_obs": ["Element", "Status", "What to observe", "Metrics", "Exists in the code"],
        "so_design": "no, design only", "sim": "yes",
        "ob_area": "\n## Coverage by area\n\nHow many components in each area say how to observe them.\n\n",
        "col_area": ["Area", "Components", "With observability", "Share"],
        "me_titulo": "# Metrics and benchmarks\n\n",
        "me_vazio": "No curated metrics yet. Record measured numbers in `metricas/metricas.json`, with the source of "
                    "each one.\n",
        "me_resumo": "**{n} metrics; {passa} meet the target and {falha} do not yet.** "
                     "Every number is tied to the components it evaluates and to the evidence it came from.\n\n"
                     "The source is `metricas/metricas.json`, a curated summary: only numbers and their origin (evidence "
                     "file, branch, commit and field), never personal data or answers. The test "
                     "`tests/test_arquitetura_metricas.py` checks each number against the JSON at the cited commit.\n",
        "sem_veredito": "no verdict", "sem_grupo": "No group", "sem_meta": "no target",
        "passa": "**passes**", "falha": "fails",
        "me_atual": "\n## Current state\n",
        "col_me": ["Metric", "Current", "Target", "Verdict", "Components", "Date"],
        "me_hist": "\n## History and source\n\nWhere each number came from, from the oldest measurement to the "
                   "current one.\n",
        "atual": "current: ", "campo": "field",
        "col_hist": ["Measurement", "Value", "Date", "Source"],
        "de_titulo": "# Decision index\n\n",
        "de_vazio": "No decisions recorded yet. Create `adrs/0001-<title>.md` in the single format (see the sample "
                    "ADR).\n",
        "de_resumo": "**{n} decisions: {resumo}.** Newest first. Each row comes from the ADR header; in the reader "
                     "(`leitor/index.html#decisoes`) they show on a timeline.\n\n",
        "de_problemas": "> **Format problems:** ",
        "substitui": "supersedes ", "substituida_por": "superseded by ",
        "col_de": ["ADR", "Decision", "Status", "Date", "Elements", "Relation"],
        "fim": "{n} elements read; {k} documents generated in {d}",
    },
}


def t(chave):
    return TEXTOS[IDIOMA][chave]


def st(p: dict, padrao: str = "?") -> str:
    """Chave canônica do status (aceita rótulo em inglês e forma de tag); padrao quando não há status."""
    return ac.status_de({"props": p, "tags": []}) if p.get("status") else padrao


def rot(chave: str) -> str:
    return ac.rotulo_status(chave, IDIOMA)


def rotulo_adr(status: str) -> str:
    if IDIOMA == "en":
        return getattr(gl, "STATUS_ADR_EN", STATUS_ADR_EN).get(status, status)
    return gl.STATUS_ADR.get(status, status)


def coletar(ws):
    itens = []

    def item(tipo, sistema, cont, el, grupo=""):
        p = el.get("properties", {})
        return {
            "tipo": tipo,
            "sistema": sistema["name"],
            "container": cont["name"],
            "grupo": grupo,
            "nome": el["name"],
            "ident": p.get("structurizr.dsl.identifier", ""),
            "desc": el.get("description", ""),
            "tech": el.get("technology", ""),
            "p": p,
        }

    for sistema in ws["model"]["softwareSystems"]:
        for cont in sistema.get("containers", []):
            itens.append(item("container", sistema, cont, cont))
            for comp in cont.get("components", []):
                itens.append(item("componente", sistema, cont, comp, comp.get("group", "")))
    return itens


def cel(texto):
    return str(texto or "").replace("|", "\\|").replace("\n", " ").strip()


def link(i):
    """Nome do elemento como link para o mapa (quando há identificador)."""
    nome = cel(i["nome"])
    return f"[{nome}]({MAPA}#{i['ident']})" if i.get("ident") else nome


def pct(n, total):
    return f"{100 * n / total:.0f}%" if total else "0%"


def tabela(cabecalho, linhas, alinhamento=None):
    """Tabela Markdown; colunas totalmente vazias somem (menos ruído na leitura)."""
    if not linhas:
        return ""
    usadas = [k for k in range(len(cabecalho)) if k == 0 or any(str(l[k]).strip() for l in linhas)]
    alinhamento = alinhamento or ["---"] * len(cabecalho)
    out = ["| " + " | ".join(cabecalho[k] for k in usadas) + " |",
           "|" + "|".join(alinhamento[k] for k in usadas) + "|"]
    out += ["| " + " | ".join(str(l[k]) for k in usadas) + " |" for l in linhas]
    return "\n".join(out) + "\n"


def mapa_de_status(itens):
    comps = [i for i in itens if i["tipo"] == "componente"]
    conts = [i for i in itens if i["tipo"] == "container"]
    por_status = Counter(st(i["p"]) for i in comps)
    total = len(comps)
    prontos = por_status.get("Pronto", 0)
    sem_comp = [c for c in conts if not any(i["container"] == c["nome"] for i in comps)]
    out = [t("cab"), t("st_titulo")]
    andamento, planejados = por_status.get("Em andamento", 0), por_status.get("Planejado", 0)

    def pl(chave, n):
        return t("plural")[chave][0 if n == 1 else 1]

    out.append(t("st_resumo").format(
        prontos=prontos, total=total, pct=pct(prontos, total), andamento=andamento, planejados=planejados,
        conts=len(conts), v_pronto=pl("v_pronto", prontos), v_andamento=pl("v_andamento", andamento),
        v_planejado=pl("v_planejado", planejados), v_conts=pl("v_conts", len(conts)), s_conts=pl("s_conts", len(conts)),
        sem=t("st_sem").format(n=len(sem_comp), dele=pl("dele", len(conts))) if sem_comp else ""))
    out.append(t("st_fonte"))
    out.append(t("st_quanto"))
    linhas = [[f"**{rot(s)}**", t("signif").get(s, ""), por_status.get(s, 0), pct(por_status.get(s, 0), total)]
              for s in ORDEM_STATUS]
    linhas += [[f"**{rot(s)}**", "", n, pct(n, total)] for s, n in por_status.items() if s not in ORDEM_STATUS]
    out.append(tabela(t("col_status"), linhas, ["---", "---", "---:", "---:"]))

    out.append(t("st_por_cont"))
    linhas = []
    for c in conts:
        cs = [i for i in comps if i["container"] == c["nome"]]
        cont_st = Counter(st(i["p"]) for i in cs)
        if cs:
            linhas.append([link(c), len(cs)] + [cont_st.get(s, 0) or "·" for s in ORDEM_STATUS])
    out.append(tabela(t("col_cont") + [rot(s) for s in ORDEM_STATUS], linhas,
                      ["---"] + ["---:"] * (len(ORDEM_STATUS) + 1)))
    if sem_comp:
        out.append(t("st_zero") + ", ".join(
            link(c) + f" ({cel(rot(st(c['p'], '')) or t('sem_status'))})" for c in sem_comp) + ".\n")

    out.append(t("st_falta"))
    for s in ORDEM_STATUS:
        if s == "Pronto":
            continue
        lista = [i for i in comps if st(i["p"]) == s]
        if not lista:
            continue
        out.append(f"\n### {rot(s)} ({len(lista)})\n\n")
        linhas = [[link(i), cel(i["container"]), cel(i["grupo"]),
                   f"`{cel(i['p'].get('codigo'))}`" if i["p"].get("codigo") else "",
                   cel(i["p"].get("equipe", "")), cel(i["p"].get("nota", ""))] for i in lista]
        out.append(tabela(t("col_falta"), linhas))
    cont_nao_prontos = [i for i in conts if i["p"].get("status") and st(i["p"]) != "Pronto"]
    if cont_nao_prontos:
        out.append(t("st_cont_np"))
        out.append(tabela(t("col_cont_np"),
                          [[link(i), cel(rot(st(i["p"]))), cel(i["p"].get("nota", ""))] for i in cont_nao_prontos]))
    return "".join(out)


def catalogo(itens):
    obs = [i for i in itens if i["p"].get("observabilidade") or i["p"].get("metricas")]
    so_design = [i for i in obs if st(i["p"]) == "Planejado"]
    comps = [i for i in itens if i["tipo"] == "componente"]
    com_obs = [i for i in comps if i["p"].get("observabilidade")]
    out = [t("cab"), t("ob_titulo")]
    out.append(t("ob_resumo").format(obs=len(obs), design=len(so_design), com=len(com_obs), comps=len(comps),
                                     pct=pct(len(com_obs), len(comps)), planejado=rot("Planejado")))
    por_cont = OrderedDict()
    for i in obs:
        por_cont.setdefault(i["container"], []).append(i)
    for cont, lista in por_cont.items():
        out.append(f"\n## {cont}\n\n")
        linhas = [[link(i), cel(rot(st(i["p"], ""))), cel(i["p"].get("observabilidade", "")),
                   cel(i["p"].get("metricas", "")),
                   t("so_design") if st(i["p"]) == "Planejado" else t("sim")] for i in lista]
        out.append(tabela(t("col_obs"), linhas))
    por_area = {}
    for i in comps:
        a = i["p"].get("area", "?")
        d = por_area.setdefault(a, [0, 0])
        d[0] += 1
        if i["p"].get("observabilidade"):
            d[1] += 1
    out.append(t("ob_area"))
    out.append(tabela(t("col_area"),
                      [[cel(a.removeprefix("Area")), n, o, pct(o, n)] for a, (n, o) in sorted(por_area.items())],
                      ["---", "---:", "---:", "---:"]))
    return "".join(out)


def metricas_doc(ws, base):
    """91: as métricas curadas (metricas/metricas.json) com atual × meta, histórico e origem de cada número."""
    cfg = ac.ler_config(base)
    metricas = ac.ler_metricas(base, cfg)
    elementos, _ = ac.coletar(ws)
    nome_de = {e["ident"]: e["nome"] for e in elementos.values() if e["ident"]}
    out = [t("cab"), t("me_titulo")]
    if not metricas:
        out.append(t("me_vazio"))
        return "".join(out)
    vered = Counter((m.get("veredito") or "sem veredito") for m in metricas)
    out.append(t("me_resumo").format(n=len(metricas), passa=vered.get("passa", 0), falha=vered.get("falha", 0)))
    grupos = OrderedDict()
    for m in metricas:
        grupos.setdefault(m.get("grupo") or t("sem_grupo"), []).append(m)
    out.append(t("me_atual"))
    for g, lista in grupos.items():
        out.append(f"\n### {g}\n\n")
        linhas = []
        for m in lista:
            a = m["atual"]
            meta = (m.get("meta") or {}).get("texto", t("sem_meta"))
            comps = ", ".join(f"[{cel(nome_de.get(i, i))}]({MAPA}#{i})" for i in m.get("componentes", []))
            v = m.get("veredito", "")
            linhas.append([cel(m["nome"]), f"{ac.numero(a['valor'])} {cel(m.get('unidade', ''))}".strip(), cel(meta),
                           t("passa") if v == "passa" else (t("falha") if v == "falha" else cel(v)), comps,
                           a.get("data", "")])
        out.append(tabela(t("col_me"), linhas, ["---", "---:", "---", "---", "---", "---"]))
    out.append(t("me_hist"))
    for m in metricas:
        out.append(f"\n### {m['nome']}\n\n")
        linhas = []
        for x in m.get("historico", []) + [dict(m["atual"], rotulo=t("atual") + m["atual"].get("rotulo", ""))]:
            f = x["fonte"]
            url = ac.link_fonte(f, cfg)
            origem = f"`{f['arquivo'].rsplit('/', 1)[-1]}` @ `{f['commit']}` · {t('campo')} `{f['campo']}`"
            if url:
                origem = f"[{origem}]({url})"
            linhas.append([cel(x.get("rotulo", "")), f"{ac.numero(x['valor'])} {cel(m.get('unidade', ''))}".strip(),
                           x.get("data", ""), origem])
        out.append(tabela(t("col_hist"), linhas, ["---", "---:", "---", "---"]))
    return "".join(out)


def indice_decisoes(ws, base):
    """92: índice dos ADRs, gerado do cabeçalho de cada arquivo em adrs/ (substitui listas manuais)."""
    adrs = gl.ler_adrs(base / "adrs")
    elementos = gl.identificadores_do_workspace(ws)
    erros = gl.validar_adrs(adrs, set(elementos) if elementos else None)
    out = [t("cab"), t("de_titulo")]
    if not adrs:
        out.append(t("de_vazio"))
        return "".join(out)
    cont = Counter(a["status"] for a in adrs)
    resumo = ", ".join(f"{cont[s]} {rotulo_adr(s).lower()}{'s' if cont[s] > 1 and IDIOMA == 'pt' else ''}"
                       for s in gl.STATUS_ADR if cont.get(s))
    out.append(t("de_resumo").format(n=len(adrs), resumo=resumo))
    if erros:
        out.append(t("de_problemas") + "; ".join(cel(e) for e in erros) + "\n\n")
    linhas = []
    for a in sorted(adrs, key=lambda x: (x["data"], x["id"]), reverse=True):
        elems = ", ".join(f"[{cel(elementos.get(e, {}).get('nome', e))}]({MAPA}#{e})" for e in a["elementos"])
        rel = []
        if a["substitui"]:
            rel.append(t("substitui") + ", ".join(a["substitui"]))
        if a["substituida_por"]:
            rel.append(t("substituida_por") + ", ".join(a["substituida_por"]))
        linhas.append([f"[{a['id']}](../adrs/{a['arquivo']})", cel(a["titulo"]), cel(rotulo_adr(a["status"])),
                       a["data"], elems, "; ".join(rel)])
    out.append(tabela(t("col_de"), linhas))
    return "".join(out)


def main():
    global IDIOMA
    ws = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    destino = Path(sys.argv[2])
    itens = coletar(ws)
    base = destino.resolve().parent
    IDIOMA = ac.ler_config(base).get("idioma", ac.IDIOMA_PADRAO)
    arquivos = {
        "02-mapa-de-status.md": mapa_de_status(itens),
        "90-catalogo-de-observabilidade.md": catalogo(itens),
        "91-metricas-e-benchmarks.md": metricas_doc(ws, base),
        gl.INDICE_DECISOES + ".md": indice_decisoes(ws, base),
    }
    for nome, texto in arquivos.items():
        (destino / nome).write_text(texto, encoding="utf-8", newline="\n")
    print(t("fim").format(n=len(itens), k=len(arquivos), d=destino))


if __name__ == "__main__":
    main()
