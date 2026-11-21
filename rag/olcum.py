"""Geri çağırma ölçümü (Adım 2). Girdi: ham talep_metni; beklenen_kaynak'ı olan talepler.

İki ayrı ölçüt (karar: ilk ölçümden sonra ikiye ayrıldı; ilk ölçüm sonuclar/ilk_olcum_rag.md'de donduruldu):
(a) ÖNCELİK KURALI geri çağırması: yalnızca beklenen_kaynak içindeki Doküman 02 maddeleri.
    tümü = o talebin 02 maddelerinin hepsi ilk k'da | en_az_biri = en az biri ilk k'da
(b) HESAP/ONAY maddeleri (01, 03) ve 04: RAG ile ÖLÇÜLMEZ; atıfları Adım 5'te kod, çalıştırdığı araca göre ekler.
    Burada yalnızca kaç tane olduğu sayılır.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from rag.arama import retrieve

_ONEK = {"01": "01_sla_sozlesmesi", "02": "02_oncelik_rehberi",
         "03": "03_eskalasyon_proseduru", "04": "04_destek_sss"}


def beklenen_coz(s: str) -> tuple[str, str]:
    d, m = s.split(":", 1)
    return _ONEK[d], (f"Soru {m}" if d == "04" and not m.startswith("Soru") else m)


def calistir(ks=(3, 5), dokuman=None):
    """(a) ölçütü. dokuman: retrieve filtresi (None = filtresiz)."""
    talepler = [t for t in json.loads((config.DATA_DIR / "test_seti.json").read_text(encoding="utf-8"))["talepler"]
                if t.get("beklenen_kaynak")]
    sonuc = {k: {"tumu": 0, "en_az_biri": 0, "kacan": []} for k in ks}
    kmax, n02, rag_disi = max(ks), 0, 0
    for t in talepler:
        tum = {beklenen_coz(s) for s in t["beklenen_kaynak"]}
        bek = {x for x in tum if x[0] == "02_oncelik_rehberi"}
        rag_disi += len(tum) - len(bek)
        if not bek:
            continue
        n02 += 1
        getirilen = [(r["dokuman"], r["madde"]) for r in retrieve(t["talep_metni"], k=kmax, dokuman=dokuman)]
        for k in ks:
            bulunan = bek & set(getirilen[:k])
            r = sonuc[k]
            r["tumu"] += bulunan == bek
            r["en_az_biri"] += bool(bulunan)
            if bulunan != bek:
                r["kacan"].append((t["id"], t.get("set"), sorted(m for _, m in bek - bulunan)))
    return n02, rag_disi, sonuc


if __name__ == "__main__":
    n, rag_disi, sonuc = calistir()
    print(f"(a) öncelik kuralı (02) geri çağırma, {n} talep; (b) RAG dışı beklenen madde sayısı: {rag_disi} (ölçülmez)")
    for k, r in sonuc.items():
        print(f"\nk={k}: tümü {r['tumu']}/{n} | en az biri {r['en_az_biri']}/{n}")
        print("  kaçırılanlar (talep, set, eksik 02 maddeleri):")
        for x in r["kacan"]:
            print("   ", x)
