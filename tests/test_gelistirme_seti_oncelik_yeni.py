"""Adım 4 düzeltme turu geliştirme seti: dağılım, test setinden ayrılık, few-shot ayrılığı."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deneme import gelistirme_seti_oncelik as g  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
TEST = [t["talep_metni"] for t in json.loads((KOK / "data" / "test_seti.json").read_text(encoding="utf-8"))["talepler"]]


def _kel(s):
    return set(re.findall(r"\w+", s.lower()))


def _j(a, b):
    a, b = _kel(a), _kel(b)
    return len(a & b) / len(a | b)


def test_dagilim():
    assert len(g.GELISTIRME_ONCELIK_YENI) == 10
    assert Counter(x[2] for x in g.GELISTIRME_ONCELIK_YENI) == {"gecici_cozum": 6, "gecici_cozum_yok": 4}
    assert Counter(x[1] for x in g.GELISTIRME_ONCELIK_YENI) == {"P3": 5, "P4": 1, "P2": 4}


def test_test_setine_yakin_metin_yok():
    for m, *_ in g.GELISTIRME_ONCELIK_YENI:
        assert max(_j(m, t) for t in TEST) < 0.4, m


def test_diger_setlerle_cakisma_yok():
    n = lambda s: re.sub(r"\s+", " ", s.lower()).strip()  # noqa: E731
    yeni = {n(m) for m, *_ in g.GELISTIRME_ONCELIK_YENI}
    assert not yeni & {n(m) for m, _ in g.GELISTIRME_ONCELIK + g.FEWSHOT_ONCELIK}


def test_fewshot_test_ve_gelistirme_setlerine_yakin_degil():
    for m, _ in g.FEWSHOT_ONCELIK:
        assert max(_j(m, t) for t in TEST) < 0.4, m
        assert max(_j(m, x[0]) for x in g.GELISTIRME_ONCELIK_YENI) < 0.5, m
        assert max(_j(m, x[0]) for x in g.GELISTIRME_ONCELIK) < 0.5, m
