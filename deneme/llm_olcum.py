"""1b/1c/1d adımlarını GELİŞTİRME setinde ölçer (data/test_seti.json kullanılmaz).
Kullanım: python deneme/llm_olcum.py   (ilk, ısınma çağrısı ölçüme katılmaz)"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm_adimlari as L
from deneme import gelistirme_seti as g


def calistir():
    L.talimat_tespit("Isınma çağrısı: panel açılmıyor.")      # model yükleme süresini dışarıda bırak
    cikti = {}
    sureler = {}
    for ad, fn, veri in (("1b", L.talimat_tespit, g.GELISTIRME_1B), ("1c", L.talep_turu_bul, g.GELISTIRME_1C),
                         ("1d", L.firma_adi_bul, g.GELISTIRME_1D)):
        satirlar = []
        for metin, beklenen in veri:
            s = fn(metin)
            satirlar.append((metin, beklenen, s))
        cikti[ad] = satirlar
        sureler[ad] = [s.sure_sn for *_, s in satirlar]
    return cikti, sureler


def rapor(cikti, sureler):
    ozet = {}
    for ad, satirlar in cikti.items():
        dogru = sum(1 for _, b, s in satirlar if s.deger == b and s.durum == "TAMAM")
        isl = sum(1 for *_, s in satirlar if s.durum == "ISLENEMEDI")
        yeniden = sum(1 for *_, s in satirlar if s.deneme == 2)
        t = sureler[ad]
        print(f"\n=== {ad}: doğru {dogru}/{len(satirlar)} | ISLENEMEDI {isl} | yeniden denenen {yeniden} | "
              f"gecikme ort {statistics.mean(t):.1f} sn, maks {max(t):.1f} sn")
        for metin, b, s in satirlar:
            if not (s.deger == b and s.durum == "TAMAM"):
                ek = f" (model ham ad: {s.ham_ad!r})" if ad == "1d" and s.ham_ad != s.deger else ""
                print(f"  YANLIŞ: beklenen={b!r} alınan={s.deger!r} durum={s.durum}{ek} | {metin}")
        ozet[ad] = satirlar
    b = ozet["1b"]
    kacan = sum(1 for _, e, s in b if e is True and s.deger is not True)
    yanlis_engel = sum(1 for _, e, s in b if e is False and s.deger is True)
    print(f"\n1b komutu kaçırma {kacan}/{sum(e is True for _, e, _ in b)} | masum engelleme {yanlis_engel}/{sum(e is False for _, e, _ in b)}")
    d = ozet["1d"]
    bulunan = sum(1 for _, e, s in d if e is not None and s.deger == e)
    ad_yok_ad_dondu = sum(1 for _, e, s in d if e is None and s.ham_ad)
    print(f"1d doğru ad {bulunan}/{sum(e is not None for _, e, _ in d)} | ad olmayan örnekte ad döndürme (süzmeden önce) "
          f"{ad_yok_ad_dondu}/{sum(e is None for _, e, _ in d)}")


if __name__ == "__main__":
    rapor(*calistir())
