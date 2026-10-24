"""
Static checks of the browser front end in `paraverse_graph/web/`: the design-token discipline
of the stylesheet (ported from tbd's web viewer tests), the module graph, and the rules
that keep the page safe to embed (no CDN, no HTML parsing of API data).
"""

from __future__ import annotations

import colorsys
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from paraverse_graph.mapping import LABELS

WEB = Path(__file__).resolve().parents[1] / "src" / "paraverse_graph" / "web"
CSS = (WEB / "style.css").read_text(encoding="utf-8")
JS_FILES = sorted(WEB.rglob("*.js"))

# Hex, rgb() or hsl() written in a rule rather than referenced through a token.
COLOR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\s*\(")
IMPORT = re.compile(r"""(?:^|\n)\s*import\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]""")


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _block(css: str, selector: str) -> str:
    """The body of the first rule whose selector matches, braces balanced."""
    source = _strip_comments(css)
    start = source.index(selector)
    open_at = source.index("{", start)
    depth = 0
    for i in range(open_at, len(source)):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        if depth == 0:
            return source[open_at + 1 : i]
    raise AssertionError(f"unbalanced block after {selector}")


def _declarations(block: str) -> dict[str, str]:
    return {
        name.strip(): value.strip()
        for name, _, value in (d.partition(":") for d in block.split(";") if ":" in d)
    }


def test_color_literals_only_in_base_root():
    base = _block(CSS, ":root {")
    rest = _strip_comments(CSS).replace(base, "", 1)
    assert COLOR_LITERAL.findall(rest) == []


def test_dark_themes_are_pure_remaps_and_agree():
    explicit = _declarations(_block(CSS, ":root[data-theme='dark']"))
    system = _declarations(_block(_block(CSS, "@media (prefers-color-scheme: dark)"), ":root:not("))
    assert explicit == system
    base = _declarations(_block(CSS, ":root {"))
    for name, value in explicit.items():
        if name == "color-scheme":
            continue
        assert value == f"var(--dark-{name[2:]})", name
        assert f"--dark-{name[2:]}" in base, name


def test_every_used_token_is_defined():
    css = _strip_comments(CSS)
    defined = set(re.findall(r"(--[\w-]+)\s*:", css))
    used = set(re.findall(r"var\((--[\w-]+)", css))
    # --kc is set per element from JS (the kind color of a dot).
    assert used - defined - {"--kc"} == set()


def _hsl(value: str) -> tuple[float, float, float]:
    """`hsl(215 15% 9%)` as an sRGB triple (the alpha form is not a text color)."""
    match = re.fullmatch(r"hsl\((\S+) (\S+) (\S+)\)", value)
    assert match, value
    hue, saturation, lightness = (float(v.rstrip("%")) for v in match.groups())
    return colorsys.hls_to_rgb(hue / 360, lightness / 100, saturation / 100)


def _contrast(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    def luminance(c: tuple[float, float, float]) -> float:
        r, g, b_ = (v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_

    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("prefix", ["--", "--dark-"])
def test_text_tokens_meet_wcag_aa_on_both_surfaces(prefix: str):
    # Small text in these colors sits on the page and on panels (pills, top bar).
    base = _declarations(_block(CSS, ":root {"))
    for surface in ("bg", "panel"):
        for token in ("text", "muted", "accent", "info", "success", "warning", "error"):
            ratio = _contrast(_hsl(base[prefix + token]), _hsl(base[prefix + surface]))
            assert ratio >= 4.5, f"{prefix}{token} on {prefix}{surface}: {ratio:.2f}"


def test_every_kind_has_a_color_token():
    for kind in LABELS:
        assert f"--kind-{kind}:" in CSS, kind


def test_every_imported_module_exists_and_none_is_orphaned():
    reached: set[Path] = set()
    pending = [WEB / "app.js"]
    while pending:
        path = pending.pop()
        if path in reached:
            continue
        assert path.is_file(), f"missing module {path.relative_to(WEB)}"
        reached.add(path)
        for spec in IMPORT.findall(path.read_text(encoding="utf-8")):
            assert spec.startswith("./") or spec.startswith("../"), f"non-relative import {spec!r}"
            pending.append((path.parent / spec).resolve())
    assert set(JS_FILES) == reached


def test_index_loads_only_local_cache_busted_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    # The server rewrites these exact strings to versioned URLs.
    assert '<script type="module" src="/static/app.js">' in html
    assert '<link rel="stylesheet" href="/static/style.css">' in html
    assert not re.search(r"""(?:src|href)=["']https?:""", html)
    for path in JS_FILES:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"""import\s*\(?\s*['"]https?:""", text), path.name
    assert "@import" not in CSS


def test_markup_is_parsed_only_from_constant_icons():
    # API data reaches the page only as text nodes and attributes.
    risky = re.compile(
        r"\.innerHTML\b|\.outerHTML\s*=|insertAdjacentHTML|document\.write|\beval\(|new Function\("
    )
    for path in JS_FILES:
        hits = risky.findall(path.read_text(encoding="utf-8"))
        if path.name == "icons.js":
            assert hits == [".innerHTML"]
        else:
            assert hits == [], path.name


def test_external_links_are_isolated():
    for path in JS_FILES:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "target: '_blank'" in line:
                assert "rel: 'noopener noreferrer'" in line, f"{path.name}: {line.strip()}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_modules_parse():
    for path in JS_FILES:
        subprocess.run(["node", "--check", str(path)], check=True, capture_output=True)


def test_live_reload_preserves_draft_filters_and_cancels_old_callbacks():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed for the frontend lifecycle regression")
    subprocess.run(
        [node, str(Path(__file__).with_name("frontend_reload.mjs")), str(WEB)],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
