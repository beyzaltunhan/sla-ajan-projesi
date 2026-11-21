"""Geri çağırma ölçümü (Adım 2). Tanımlar ölçümden önce sabitlendi:
- Girdi: talep_metni (ham), beklenen_kaynak'ı olan talepler. k=5 birincil, k=3 ek.
- tümü: beklenen maddelerin HEPSİ ilk k'da | en_az_biri: en az biri ilk k'da
- madde_recall: bulunan beklenen madde / toplam beklenen madde
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


def calistir(ks=(3, 5)):
    talepler = [t for t in json.loads((config.DATA_DIR / "test_seti.json").read_text(encoding="utf-8"))["talepler"]
                if t.get("beklenen_kaynak")]
    sonuc = {k: {"tumu": 0, "en_az_biri": 0, "bulunan": 0, "toplam": 0, "kacan": []} for k in ks}
    kmax = max(ks)
    for t in talepler:
        bek = {beklenen_coz(s) for s in t["beklenen_kaynak"]}
        getirilen = [(r["dokuman"], r["madde"]) for r in retrieve(t["talep_metni"], k=kmax)]
        for k in ks:
            bulunan = bek & set(getirilen[:k])
            r = sonuc[k]
            r["tumu"] += bulunan == bek
            r["en_az_biri"] += bool(bulunan)
            r["bulunan"] += len(bulunan)
            r["toplam"] += len(bek)
            if bulunan != bek:
                r["kacan"].append((t["id"], t.get("set"), sorted(f"{d[:2]}:{m}" for d, m in bek - bulunan)))
    return len(talepler), sonuc


if __name__ == "__main__":
    n, sonuc = calistir()
    for k, r in sonuc.items():
        print(f"\nk={k}: talep={n} | tümü bulundu {r['tumu']}/{n} | en az biri {r['en_az_biri']}/{n} | "
              f"madde {r['bulunan']}/{r['toplam']}")
        print("  kaçırılanlar (talep, set, eksik maddeler):")
        for x in r["kacan"]:
            print("   ", x)
