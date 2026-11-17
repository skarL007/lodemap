"""Regressão: o leitor não deve transformar destinos não confiáveis em links clicáveis."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "templates" / "structurizr" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import gerar_leitor as gl  # noqa: E402


@pytest.fixture()
def ctx():
    return gl.Contexto({"guia"}, {"0001-decisao.md": "0001"}, {}, "doc-guia")


@pytest.mark.parametrize("destino", [
    "javascript:alert",
    "JaVaScRiPt:alert",
    "data:text/html,malicious",
    "vbscript:msgbox",
    "file:///etc/passwd",
    "ftp://example.org/archive",
    "http:not-an-absolute-url",
    "//example.org/redirect",
    "/etc/passwd",
    r"C:\Users\example\secret",
    "../../secret.txt",
    "../explorador/../../secret.txt",
    "../explorador/%2e%2e/%2e%2e/secret.txt",
    "../explorador/%2f..%2f..%2fsecret.txt",
    "../explorador\..\..\secret.txt",
    "https://bad host.example",
    "javascript:\nalert",
])
def test_insecure_destination_is_plain_text(ctx, destino):
    assert ctx.href(destino) == ("", False)
    assert gl._link(destino, "Text", ctx, "docs") == "Text"


def test_untrusted_markdown_link_preserves_escaped_label(ctx):
    out = gl.markdown("[<b>Open</b>](JaVaScRiPt:alert)", ctx)
    assert "&lt;b&gt;Open&lt;/b&gt;" in out
    assert "<a " not in out


def test_safe_links_and_cross_document_rewrites_still_work(ctx):
    assert ctx.href("https://example.org/page") == ("https://example.org/page", True)
    assert ctx.href("http://example.org/page") == ("http://example.org/page", True)
    assert ctx.href("mailto:hello@example.org") == ("mailto:hello@example.org", False)
    assert ctx.href("guia.md") == ("#doc-guia", False)
    assert ctx.href("../adrs/0001-decisao.md") == ("#adr-0001", False)
    assert ctx.href("../explorador/index.html#graph") == (
        "../explorador/index.html#graph", False
    )
    out = gl.markdown("[site](https://example.org) [map](../explorador/index.html#graph)", ctx)
    assert 'href="https://example.org" rel="noopener noreferrer"' in out
    assert 'href="../explorador/index.html#graph"' in out
