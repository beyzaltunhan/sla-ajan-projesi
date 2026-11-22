"""Adım 4 (öncelik) ölçümü: üretim yapılandırması (strateji 2). data/test_seti.json KULLANILMAZ.
Kullanım: python deneme/olcum_oncelik.py [yeni|eski|hepsi]"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import oncelik_onerisi as O
from deneme.gelistirme_seti_oncelik import GELISTIRME_ONCELIK, GELISTIRME_ONCELIK_YENI

STRATEJI = "getirilen+cekirdek"


def kos(veri, ad):
    t, yanlis, uyd, bos = [], [], 0, 0
    for m, e, *grup in veri:
        s = O.oncelik_oner(m, O.baglam_parcalari(STRATEJI, talep=m))
        t.append(s.sure_sn)
        uyd += len(s.uydurma)
        bos += s.oncelik in ("P1", "P2", "P3", "P4") and not s.maddeler
        if s.oncelik != e:
            yanlis.append((m, e, s.oncelik, grup[0] if grup else "", s.ham_maddeler, s.etki))
    print(f"\n=== {ad}: doğru {len(veri) - len(yanlis)}/{len(veri)} | ham uydurma madde {uyd} | P1-P4 ama geçerli madde yok {bos} | "
          f"gecikme ort {statistics.mean(t):.1f} sn, maks {max(t):.1f} sn")
    for m, e, a, gr, mad, etki in yanlis:
        print(f"  YANLIŞ [{gr}] beklenen={e} alınan={a} maddeler={mad} | {m}\n      etki: {etki}")
    return yanlis


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    O.oncelik_oner("Isınma: panel açılmıyor.", O.baglam_parcalari(STRATEJI, talep="panel açılmıyor"))
    if mod in ("yeni", "hepsi"):
        y = kos(GELISTIRME_ONCELIK_YENI, "YENİ 10")
        for grup in ("gecici_cozum", "gecici_cozum_yok"):
            n = sum(1 for x in GELISTIRME_ONCELIK_YENI if x[2] == grup)
            print(f"  grup {grup}: hata {sum(1 for r in y if r[3] == grup)}/{n}")
    if mod in ("eski", "hepsi"):
        kos(GELISTIRME_ONCELIK, "ESKİ 31")
