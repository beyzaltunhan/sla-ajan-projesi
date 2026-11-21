"""Retrieval ayar denemesi: yalnızca geliştirme sorguları. Çıktı: ayar tablosu."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deneme.gelistirme_sorgulari import ETIKETLER
from rag.arama import retrieve

AYARLAR = [("filtresiz", 5, None), ("02 filtre", 5, "02_oncelik_rehberi"), ("02 filtre", 8, "02_oncelik_rehberi"),
           ("02 filtre", 10, "02_oncelik_rehberi"), ("filtresiz", 10, None)]

if __name__ == "__main__":
    print(f"{len(ETIKETLER)} gelistirme sorgusu")
    print("| ayar | k | tümü | en az biri | madde |\n|---|---|---|---|---|")
    kacan = {}
    for ad, k, f in AYARLAR:
        tum = biri = bul = top = 0
        kc = []
        for i, (q, bek) in enumerate(ETIKETLER):
            g = {(r["dokuman"], r["madde"]) for r in retrieve(q, k=k, dokuman=f)}
            b = bek & g
            tum += b == bek; biri += bool(b); bul += len(b); top += len(bek)
            if b != bek: kc.append((i, sorted(m for _, m in bek - b)))
        print(f"| {ad} | {k} | {tum}/{len(ETIKETLER)} | {biri}/{len(ETIKETLER)} | {bul}/{top} |")
        kacan[(ad, k)] = kc
    for key in [("02 filtre", 10), ("02 filtre", 5)]:
        print(f"\nKaçırılan {key}:", kacan[key])
