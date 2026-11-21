"""Adım 4 iki bağlam stratejisini GELİŞTİRME setinde karşılaştırır (data/test_seti.json kullanılmaz).
Kullanım: python deneme/oncelik_olcum.py"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import oncelik_onerisi as O
from deneme.gelistirme_seti_oncelik import GELISTIRME_ONCELIK
from rag.arama import retrieve

STRATEJILER = ("getirilen", "getirilen+cekirdek")


def main():
    # Retrieval bir kez yapılır; iki strateji aynı getirilen parçaları kullanır.
    getirilen = [[{"madde": r["madde"], "metin": r["metin"]} for r in retrieve(q, k=O.K, dokuman=O.DOKUMAN)]
                 for q, _ in GELISTIRME_ONCELIK]
    O.oncelik_oner("Isınma: panel açılmıyor.", getirilen[0])          # model yükleme süresi dışarıda
    for strateji in STRATEJILER:
        sonuclar = []
        for (q, etiket), g in zip(GELISTIRME_ONCELIK, getirilen):
            sonuclar.append((q, etiket, O.oncelik_oner(q, O.baglam_parcalari(strateji, g))))
        n = len(sonuclar)
        dogru = sum(1 for _, e, s in sonuclar if s.oncelik == e)
        p1 = [(q, e, s) for q, e, s in sonuclar if e == "P1"]
        bel = [(q, e, s) for q, e, s in sonuclar if e == "belirsiz"]
        t = [s.sure_sn for *_, s in sonuclar]
        print(f"\n===== STRATEJİ: {strateji} (bağlam parça sayısı ort. "
              f"{statistics.mean(len(O.baglam_parcalari(strateji, g)) for g in getirilen):.1f}) =====")
        print(f"genel doğruluk {dogru}/{n} | P1 yakalama {sum(s.oncelik == 'P1' for *_, s in p1)}/{len(p1)} | "
              f"belirsiz yakalama {sum(s.oncelik == 'belirsiz' for *_, s in bel)}/{len(bel)}")
        print(f"ham cevapta uydurma madde: {sum(len(s.uydurma) for *_, s in sonuclar)} "
              f"({sum(1 for *_, s in sonuclar if s.uydurma)} çağrıda) | nihai çıktıda uydurma: 0 (kodla süzülür) | "
              f"P1-P4 ama geçerli madde yok: {sum(1 for *_, s in sonuclar if s.oncelik not in (None, 'belirsiz') and not s.maddeler)}")
        print(f"ISLENEMEDI {sum(s.durum == 'ISLENEMEDI' for *_, s in sonuclar)} | yeniden denenen {sum(s.deneme == 2 for *_, s in sonuclar)} | "
              f"gecikme ort {statistics.mean(t):.1f} sn, maks {max(t):.1f} sn")
        for q, e, s in sonuclar:
            if s.oncelik != e:
                print(f"  YANLIŞ: beklenen={e} alınan={s.oncelik} durum={s.durum} maddeler={s.ham_maddeler} | {q}")
        for q, e, s in sonuclar:
            if s.uydurma:
                print(f"  UYDURMA MADDE: {s.uydurma} (etiket {e}) | {q[:70]}")
        print("  dağılım (etiket -> alınan):", {e: [s.oncelik for _, ee, s in sonuclar if ee == e] for e in ("P1", "P2", "P3", "P4", "belirsiz")})


if __name__ == "__main__":
    main()
