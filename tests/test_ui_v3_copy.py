"""UI v3 copy and look: no filler words anywhere on screen, the renamed Word guide, headlines that make a point, and
none of the removed 'AI look' pieces (glow, glass blur, gradient text, aurora, dot grid, shimmer, looping motion)."""
import re
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from dashboard import copy as C  # noqa: E402
from dashboard import theme as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILLER = ["seamlessly", "seamless", "powerful", "unlock", "leverage", "delve", "cutting-edge", "in today's world", "journey",
          "empower", "game-changer", "revolutionise", "revolutionize", "elevate"]
FILLER_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in FILLER) + r")\b", re.IGNORECASE)


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from _strings(v)


def test_no_filler_words_in_the_on_screen_copy():
    texts = [s for v in vars(C).values() for s in _strings(v)]
    for mod in ("explain.py", "logic.py", "logic_forecasts.py", "components.py", "components_3d.py"):
        texts += re.findall(r'"([^"\n]{12,})"', (ROOT / "src" / "dashboard" / mod).read_text(encoding="utf-8"))
    hits = [(t[:80], m.group(0)) for t in texts for m in [FILLER_RE.search(t)] if m]
    assert not hits, hits


def test_word_guide_name_and_headlines():
    assert C.GLOSSARY_BUTTON == "Word guide"
    for key, head in C.HEAD.items():  # a headline says something, not just names the page
        assert len(head.split()) >= 4 or "{" in head, (key, head)  # {a} fills in a choice name of several words


def test_ai_look_is_gone():
    css = (ROOT / "src" / "dashboard" / "styles.css").read_text(encoding="utf-8")
    assert "backdrop-filter" not in css and "background-clip: text" not in css and "background-clip:text" not in css
    assert not re.search(r"aurora|shimmer|dot-grid|aiwi-orb", css)
    assert not re.search(r"animation:[^;]*infinite", css)  # no looping motion
    assert len(re.findall(r"@keyframes", css)) <= 2  # one entrance plus the line draw-on
    for theme in ("light", "dark"):
        tok = T.TOKENS[theme] if hasattr(T, "TOKENS") else None
        if tok:
            assert not any(k.startswith(("glow", "aurora", "dot")) for k in tok)
    assert T.RADIUS["sm"] == 8 and T.RADIUS["md"] == 12 and "Fraunces" in T.DISPLAY_FONT
