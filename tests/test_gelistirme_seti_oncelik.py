"""Adım 4 geliştirme seti: test setinden ayrı, few-shot ayrı, etiket dağılımı yeterli."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deneme.gelistirme_seti_oncelik import FEWSHOT_ONCELIK, GELISTIRME_ONCELIK  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
TEST = {re.sub(r"\s+", " ", t["talep_metni"].lower()).strip()
        for t in json.loads((KOK / "data" / "test_seti.json").read_text(encoding="utf-8"))["talepler"]}


def _n(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def test_boyut_ve_etiketler():
    assert 28 <= len(GELISTIRME_ONCELIK) <= 35
    sayac = Counter(e for _, e in GELISTIRME_ONCELIK)
    assert set(sayac) == {"P1", "P2", "P3", "P4", "belirsiz"}
    assert all(v >= 3 for v in sayac.values())


def test_test_setiyle_ayni_metin_yok():
    assert [m for m, _ in GELISTIRME_ONCELIK + FEWSHOT_ONCELIK if _n(m) in TEST] == []


def test_fewshot_gelistirme_setinden_ayri():
    assert not ({_n(m) for m, _ in FEWSHOT_ONCELIK} & {_n(m) for m, _ in GELISTIRME_ONCELIK})
    assert {e for _, e in FEWSHOT_ONCELIK} == {"P1", "P2", "P3", "P4", "belirsiz"}
