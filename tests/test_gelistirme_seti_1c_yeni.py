"""1c düzeltme turu geliştirme seti: test setinden ayrı (birebir ve yakın uyarlama yok), few-shot'tan ayrı."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deneme import gelistirme_seti as g  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
TEST = [t["talep_metni"] for t in json.loads((KOK / "data" / "test_seti.json").read_text(encoding="utf-8"))["talepler"]]


def _kel(s):
    return set(re.findall(r"\w+", s.lower()))


def _jaccard(a, b):
    a, b = _kel(a), _kel(b)
    return len(a & b) / len(a | b)


def test_dagilim():
    assert len(g.GELISTIRME_1C_YENI) == 16
    assert Counter(x[2] for x in g.GELISTIRME_1C_YENI) == {"kullanim": 8, "kapsam_disi": 4, "dokumanda_olmayan": 4}
    assert {x[1] for x in g.GELISTIRME_1C_YENI if x[2] == "kullanim"} == {"destek_talebi"}


def test_test_setine_yakin_metin_yok():
    for m, *_ in g.GELISTIRME_1C_YENI:
        assert max(_jaccard(m, t) for t in TEST) < 0.4, m


def test_eski_sette_ve_fewshot_ta_tekrar_yok():
    norm = lambda s: re.sub(r"\s+", " ", s.lower()).strip()  # noqa: E731
    yeni = {norm(m) for m, *_ in g.GELISTIRME_1C_YENI}
    assert not yeni & {norm(m) for m, _ in g.GELISTIRME_1C}
    assert not yeni & {norm(m) for m, _ in g.FEWSHOT_1C}


def test_fewshot_1c_test_ve_gelistirme_setlerinden_ayri():
    norm = lambda s: re.sub(r"\s+", " ", s.lower()).strip()  # noqa: E731
    fs = {norm(m) for m, _ in g.FEWSHOT_1C}
    assert not fs & {norm(t) for t in TEST}
    assert not fs & {norm(m) for m, _ in g.GELISTIRME_1C}
    for m, _ in g.FEWSHOT_1C:
        assert max(_jaccard(m, t) for t in TEST) < 0.4, m
        assert max(_jaccard(m, x[0]) for x in g.GELISTIRME_1C_YENI) < 0.5, m
