"""Instalador do Lodemap: perfis, plano (dry-run), aplicar com manifesto (sha antes/depois) e reverter.

Perfis:
  minimo    a skill Lodemap (junção/symlink de ~/.claude/skills/lodemap para este repositório) e os seus seis
            agentes do mapa (~/.claude/agents/lodemap-*.md)
  padrao    + aviso único por repositório sem mapa (hook SessionStart)
Cada opção é desligável (--sem aviso) e as de fora do perfil entram com --com.

Regras: nunca troca chave, arquivo ou link de outro dono sem --forcar; todo arquivo tocado ganha backup e sha; o
reverter só restaura se o arquivo ainda estiver como o instalador deixou. Não mexe em hooks de outros donos
(Synapse, CodeGraph, RTK): só acrescenta o seu.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from lodemap import MARCA, PASTA_HOOKS, RAIZ

OPCOES = {
    "skill": "skill Lodemap em ~/.claude/skills/lodemap e os seus seis agentes do mapa",
    "aviso": "hook SessionStart com aviso único em repositório sem mapa",
}
PERFIS = {
    "minimo": ["skill"],
    "padrao": ["skill", "aviso"],
}
HOOKS = {
    "aviso": [("SessionStart", "aviso_lodemap.py")],
}


def sha(p: Path) -> str | None:
    return sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def ler_json(p: Path) -> dict:
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{p}: JSON inválido ({e})") from e


def texto_json(dado: dict) -> str:
    return json.dumps(dado, ensure_ascii=False, indent=2) + "\n"


def opcoes_do(perfil: str, sem: list[str] = (), com: list[str] = ()) -> list[str]:
    if perfil not in PERFIS:
        raise ValueError(f"perfil desconhecido: {perfil} (use {', '.join(PERFIS)})")
    desconhecidas = (set(sem) | set(com)) - set(OPCOES)
    if desconhecidas:
        raise ValueError(f"opção desconhecida: {', '.join(sorted(desconhecidas))}")
    pedidas = (set(PERFIS[perfil]) | set(com)) - set(sem)
    return [o for o in OPCOES if o in pedidas]


def _e_link(p: Path) -> bool:
    return p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())


def _mesmo(a: Path, b: Path) -> bool:
    try:
        return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))
    except OSError:
        return False


def criar_link(alvo: Path, origem: Path) -> None:
    alvo.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(origem), str(alvo))
    else:
        os.symlink(origem, alvo, target_is_directory=True)


def remover_link(alvo: Path) -> None:
    if alvo.is_symlink():
        alvo.unlink()
    elif _e_link(alvo):
        os.rmdir(alvo)  # junção: remove só o ponto de montagem, nunca o conteúdo


def _comando(python: str, script: str) -> str:
    return f'"{python}" "{(PASTA_HOOKS / script).as_posix()}"'


def planejar(perfil: str = "padrao", home: Path | None = None, *, sem=(), com=(), forcar: bool = False,
             python: str | None = None) -> dict:
    home = Path(home or Path.home())
    python = (python or sys.executable).replace("\\", "/")
    opcoes = opcoes_do(perfil, sem, com)
    claude = home / ".claude"
    settings_p = claude / "settings.json"
    settings = ler_json(settings_p)
    novo = json.loads(json.dumps(settings))
    ops, conflitos, textos, links = [], [], [], []

    def arquivo(alvo: Path, conteudo: str, opcao: str, nosso: bool) -> None:
        atual = alvo.read_bytes() if alvo.is_file() else None
        if atual == conteudo.encode("utf-8"):
            return
        if atual is not None and not nosso and not forcar:
            conflitos.append(f"{alvo} já existe e não é do Lodemap; use --forcar")
            return
        textos.append({"alvo": str(alvo), "conteudo": conteudo})
        ops.append({"opcao": opcao, "tipo": "arquivo", "alvo": str(alvo),
                    "acao": "troca" if atual is not None else "cria"})

    if "skill" in opcoes:
        alvo = claude / "skills" / "lodemap"
        if alvo.exists() or _e_link(alvo):
            if not _mesmo(alvo, RAIZ):
                if forcar:
                    links.append({"alvo": str(alvo), "origem": str(RAIZ), "mover_existente": True})
                    ops.append({"opcao": "skill", "tipo": "link", "alvo": str(alvo), "acao": "troca (backup)"})
                else:
                    conflitos.append(f"{alvo} já existe e não aponta para {RAIZ}; use --forcar (move para o backup)")
        else:
            links.append({"alvo": str(alvo), "origem": str(RAIZ), "mover_existente": False})
            ops.append({"opcao": "skill", "tipo": "link", "alvo": str(alvo), "acao": "cria"})
        # A skill chama os seus seis agentes do mapa (agents/lodemap-*.md): instalá-la sem eles a deixa sem a pilha.
        for fonte in sorted((RAIZ / "agents").glob("lodemap-*.md")):
            alvo_ag = claude / "agents" / fonte.name
            atual = alvo_ag.read_text(encoding="utf-8", errors="replace") if alvo_ag.is_file() else ""
            nosso = f"name: {fonte.stem}\n" in atual.replace("\r\n", "\n")
            arquivo(alvo_ag, fonte.read_text(encoding="utf-8"), "skill", nosso)

    hooks = novo.setdefault("hooks", {}) if any(o in opcoes for o in HOOKS) else {}
    for opcao, itens in HOOKS.items():
        if opcao not in opcoes:
            continue
        for evento, script in itens:
            cmd = _comando(python, script)
            grupos = hooks.setdefault(evento, [])
            if any(h.get("command") == cmd for g in grupos for h in g.get("hooks", [])):
                continue
            grupos.append({"matcher": "", "hooks": [{"type": "command", "command": cmd, "timeout": 10}]})
            ops.append({"opcao": opcao, "tipo": "hook", "evento": evento, "comando": cmd})

    if "hooks" in novo and not novo["hooks"] and "hooks" not in settings:
        del novo["hooks"]
    return {"perfil": perfil, "opcoes": opcoes, "settings": str(settings_p),
            "settings_novo": novo if novo != settings else None, "textos": textos, "links": links,
            "ops": ops, "conflitos": conflitos, "home": str(home)}


def aplicar(plano: dict) -> Path | None:
    if plano["conflitos"]:
        raise SystemExit("conflitos; nada foi aplicado:\n  " + "\n  ".join(plano["conflitos"]))
    if not plano["ops"]:
        return None
    home = Path(plano["home"])
    pasta = home / ".claude" / ".lodemap-instalador" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    pasta.mkdir(parents=True, exist_ok=True)
    alvos = ([plano["settings"]] if plano["settings_novo"] is not None else []) + [t["alvo"] for t in plano["textos"]]
    tocados = []
    for i, alvo in enumerate(alvos):
        p = Path(alvo)
        bak = pasta / f"{i:02d}-{p.name}.bak" if p.is_file() else None
        if bak:
            shutil.copy2(p, bak)
        tocados.append({"alvo": alvo, "backup": str(bak) if bak else None, "sha_antes": sha(p)})
    if plano["settings_novo"] is not None:
        sp = Path(plano["settings"])
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(texto_json(plano["settings_novo"]), encoding="utf-8", newline="\n")
    for t in plano["textos"]:
        p = Path(t["alvo"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(t["conteudo"].encode("utf-8"))
    links = []
    for ln in plano["links"]:
        alvo = Path(ln["alvo"])
        anterior = None
        if ln["mover_existente"]:
            if _e_link(alvo):
                anterior = {"link_para": str(alvo.resolve())}
                remover_link(alvo)
            else:
                anterior = str(pasta / "skill-lodemap.anterior")
                shutil.move(str(alvo), anterior)
        criar_link(alvo, Path(ln["origem"]))
        links.append({"alvo": str(alvo), "origem": ln["origem"], "anterior": anterior})
    for t in tocados:
        t["sha_depois"] = sha(Path(t["alvo"]))
    manifesto = pasta / "manifesto.json"
    manifesto.write_text(texto_json({"marca": MARCA, "perfil": plano["perfil"], "opcoes": plano["opcoes"],
                                     "aplicado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
                                     "ops": plano["ops"], "arquivos": tocados, "links": links}),
                         encoding="utf-8", newline="\n")
    return manifesto


def reverter(manifesto: Path) -> list[str]:
    manifesto = Path(manifesto)
    if not manifesto.is_file():
        raise SystemExit(f"manifesto não encontrado: {manifesto}")
    m = ler_json(manifesto)
    if m.get("revertido_em"):
        raise SystemExit(f"{manifesto} já foi revertido em {m['revertido_em']}")
    for t in m.get("arquivos", []):
        p = Path(t["alvo"])
        if sha(p) != t["sha_depois"]:
            como = f"a partir de {t['backup']}" if t["backup"] else "(o instalador criou este arquivo: apague-o)"
            raise SystemExit(f"{p} mudou depois da instalação; reverta à mão {como}")
    for ln in m.get("links", []):
        alvo = Path(ln["alvo"])
        if not _e_link(alvo) or not _mesmo(alvo, Path(ln["origem"])):
            raise SystemExit(f"{alvo} não é mais o link do Lodemap; reverta à mão")
    feitos = []
    for t in m.get("arquivos", []):
        p = Path(t["alvo"])
        if t["backup"]:
            shutil.copy2(t["backup"], p)
        else:
            p.unlink()
        feitos.append(str(p))
    for ln in m.get("links", []):
        alvo = Path(ln["alvo"])
        remover_link(alvo)
        ant = ln.get("anterior")
        if isinstance(ant, dict):
            criar_link(alvo, Path(ant["link_para"]))
        elif ant:
            shutil.move(ant, str(alvo))
        feitos.append(str(alvo))
    m["revertido_em"] = datetime.now().astimezone().isoformat(timespec="seconds")
    manifesto.write_text(texto_json(m), encoding="utf-8", newline="\n")
    if manifesto.resolve().parent.parent.name == ".lodemap-instalador":
        _limpar_pastas_vazias([Path(x) for x in feitos], manifesto.resolve().parent.parent.parent)
    return feitos


def _limpar_pastas_vazias(tocados: list[Path], claude: Path) -> None:
    """Remove só as pastas que ficaram vazias sob ~/.claude depois de reverter; nunca a própria ~/.claude."""
    claude = claude.resolve()
    for p in tocados:
        pai = p.parent
        while pai.resolve() != claude and claude in pai.resolve().parents:
            try:
                pai.rmdir()
            except OSError:
                break
            pai = pai.parent


def ultimo_manifesto(home: Path | None = None) -> Path | None:
    pasta = Path(home or Path.home()) / ".claude" / ".lodemap-instalador"
    ms = sorted(pasta.glob("*/manifesto.json")) if pasta.is_dir() else []
    ms = [x for x in ms if not ler_json(x).get("revertido_em")]
    return ms[-1] if ms else None
