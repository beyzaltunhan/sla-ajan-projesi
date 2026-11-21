"""1c ölçümü: eski geliştirme seti (25) ve yeni düzeltme seti (16). data/test_seti.json KULLANILMAZ.
Kullanım: python deneme/olcum_1c.py [eski|yeni|hepsi]"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm_adimlari as L
from deneme import gelistirme_seti as g


def kos(veri, ad):
    t, yanlis = [], []
    for m, e, *grup in veri:
        s = L.talep_turu_bul(m)
        t.append(s.sure_sn)
        if s.deger != e:
            yanlis.append((m, e, s.deger, grup[0] if grup else ""))
    print(f"\n=== {ad}: doğru {len(veri) - len(yanlis)}/{len(veri)} | gecikme ort {statistics.mean(t):.1f} sn, maks {max(t):.1f} sn")
    for m, e, a, gr in yanlis:
        print(f"  YANLIŞ [{gr}] beklenen={e} alınan={a} | {m}")
    return yanlis


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    L.talep_turu_bul("Isınma: panel açılmıyor.")
    if mod in ("yeni", "hepsi"):
        y = kos(g.GELISTIRME_1C_YENI, "YENİ 16")
        for grup in ("kullanim", "kapsam_disi", "dokumanda_olmayan"):
            n = sum(1 for x in g.GELISTIRME_1C_YENI if x[2] == grup)
            print(f"  grup {grup}: hata {sum(1 for r in y if r[3] == grup)}/{n}")
        print(f"  kapsam_disi+dokumanda_olmayan (8): hata {sum(1 for r in y if r[3] != 'kullanim')}/8")
    if mod in ("eski", "hepsi"):
        kos(g.GELISTIRME_1C, "ESKİ 25")
