"""Geliştirme seti ve few-shot metinleri test setiyle çakışmamalı; few-shot, geliştirme setinden ayrı olmalı."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deneme import gelistirme_seti as g  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
TEST = [t["talep_metni"] for t in json.loads((KOK / "data" / "test_seti.json").read_text(encoding="utf-8"))["talepler"]]


def _n(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def _tumu(*gruplar):
    return [m for grup in gruplar for m, _ in grup]


def test_test_setiyle_ayni_metin_yok():
    test = {_n(t) for t in TEST}
    ortak = [m for m in _tumu(g.GELISTIRME_1B, g.GELISTIRME_1C, g.GELISTIRME_1D,
                              g.FEWSHOT_1B, g.FEWSHOT_1C, g.FEWSHOT_1D) if _n(m) in test]
    assert ortak == []


def test_fewshot_gelistirme_setinden_ayri():
    for fs, gs in ((g.FEWSHOT_1B, g.GELISTIRME_1B), (g.FEWSHOT_1C, g.GELISTIRME_1C), (g.FEWSHOT_1D, g.GELISTIRME_1D)):
        assert not ({_n(m) for m, _ in fs} & {_n(m) for m, _ in gs})


def test_boyut_ve_etiketler():
    assert all(20 <= len(x) <= 30 for x in (g.GELISTIRME_1B, g.GELISTIRME_1C, g.GELISTIRME_1D))
    assert {e for _, e in g.GELISTIRME_1C} == {"destek_talebi", "kapsam_disi", "dokumanda_olmayan"}
    assert {e for _, e in g.GELISTIRME_1B} == {True, False}
    assert any(e is None for _, e in g.GELISTIRME_1D) and any(e for _, e in g.GELISTIRME_1D)


def test_1d_adlar_metinde_birebir_geciyor():
    for m, ad in g.GELISTIRME_1D + g.FEWSHOT_1D:
        assert ad is None or ad in m


def test_1d_kayitli_musteri_yok():
    import sla_araclari as s
    musteriler = json.loads((KOK / "data" / "musteriler.json").read_text(encoding="utf-8"))["musteriler"]
    for m, _ in g.GELISTIRME_1D + g.FEWSHOT_1D:
        assert s.musteri_metinde_ara(m, musteriler)[0] == "BULUNAMADI", m
