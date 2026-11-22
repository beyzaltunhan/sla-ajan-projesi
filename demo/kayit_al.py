"""Demo örneklerini gerçek modelle bir kez çalıştırıp demo/kayitli_sonuclar.json'a kaydeder.
Kullanım: python demo/kayit_al.py"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from arayuz import bicimle as B  # noqa: E402
from arayuz import stil  # noqa: F401,E402
from demo.calistir import gecici_graf, ornek_calistir  # noqa: E402

CIKTI = Path(__file__).resolve().parent / "kayitli_sonuclar.json"


def main():
    klasor, _ = gecici_graf()
    kayitlar = []
    try:
        for i, ad in enumerate(B.ornekler(datetime.now()), 1):
            r = ornek_calistir(ad, i)
            s = r["sonuc"]
            print(f"{ad}: {(s['cikti'] or {}).get('davranis')} {s['durum']} {s['toplam_sn']} sn", flush=True)
            kayitlar.append({"ad": ad, "metin": r["metin"], "kayit_zamani": r["kayit_zamani"], "simdi": r["simdi"],
                             "soru_soruldu": r["soru_soruldu"], "kayit_tarihi": datetime.now().strftime("%d.%m.%Y %H:%M"),
                             "sonuc": {k: s.get(k) for k in ("thread_id", "durum", "cikti", "onay_sonucu", "bekleyen_onay",
                                                              "adim_sureleri", "hata", "toplam_sn")}})
    finally:
        klasor.cleanup()
    CIKTI.write_text(json.dumps({"_meta": {"chat_model": config.CHAT_MODEL, "embed_model": config.EMBED_MODEL,
                                          "aciklama": "Önceden çalıştırılmış kayıtlar (canlı değil)."},
                                 "kayitlar": kayitlar}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(kayitlar)} kayıt -> {CIKTI}")


if __name__ == "__main__":
    main()
