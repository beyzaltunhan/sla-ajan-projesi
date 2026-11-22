"""Ölçüm sonuçlarını dosyalardan OKUR (sayılar kodda elle yazılmaz): ham jsonl -> degerlendirme/ ölçüm mantığı."""
from __future__ import annotations

import statistics
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
SONUCLAR = KOK / "sonuclar"
ILK_HAM = SONUCLAR / "ilk_kosu_ham.jsonl"
SONRA_HAM = SONUCLAR / "duzeltme_sonrasi_ham.jsonl"
ILK_RAPOR = SONUCLAR / "ilk_kosu_rapor.md"
SONRA_RAPOR = SONUCLAR / "duzeltme_sonrasi_rapor.md"

NOT = ("Düzeltme sonrası sayılar, test hatalarının kategorisine bakılarak yapılan düzeltmelerden sonra alındı; "
       "temiz sayım ilk koşudur.")


def _kosu(yol: Path, ad: str):
    for p in (str(KOK), str(KOK / "degerlendirme")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from degerlendirme.karsilastir import Kosu  # noqa: WPS433
    return Kosu(yol, ad)


def kn(a: int, b: int) -> str:
    return f"{a}/{b}"


def _ort(v):
    return round(statistics.mean(v), 1) if v else None


def kosu_ozeti(K) -> dict:
    """Tek koşunun özeti (kaç/N sayıları ve ortalamalar)."""
    ana = [i for i in K.ids if K.test[i]["set"] == "ana"]
    zor = [i for i in K.ids if K.test[i]["set"] == "zor"]
    bag = [i for i in K.ids if K.test[i]["yazar"] == "kullanici"]
    hesap = [i for i in K.ids if K.test[i]["beklenen"]["davranis"] == "HESAPLA" and K.test[i]["beklenen"].get("onay_gerekli") is not None]
    onay_gereken = [i for i in hesap if K.test[i]["beklenen"]["onay_gerekli"]]
    onay_yok = [i for i in hesap if not K.test[i]["beklenen"]["onay_gerekli"]]
    yakalanan = sum(1 for i in onay_gereken if K.cikti(i).get("onay_gerekli"))
    yanlis_alarm = sum(1 for i in onay_yok if K.cikti(i).get("onay_gerekli"))
    sure = [K.kayit[i]["toplam_sn"] for i in K.ids]
    sure_h = [K.kayit[i]["toplam_sn"] for i in K.ids if i not in K.supheli]
    hata_turleri = {}
    for ad, idl in (("Ana set", ana), ("Zor set", zor)):
        hata_turleri[ad] = dict(Counter(K.H[i][0] for i in idl if K.H[i]))
    return {
        "ad": K.ad, "meta": K.meta, "n": len(K.ids),
        "tam": {"Ana set": (K.tam(ana), len(ana)), "Zor set": (K.tam(zor), len(zor)), "Bağımsız 15": (K.tam(bag), len(bag))},
        "dav": {"Ana set": (K.dav(ana), len(ana)), "Zor set": (K.dav(zor), len(zor)), "Bağımsız 15": (K.dav(bag), len(bag))},
        "onay_yakalama": (yakalanan, len(onay_gereken)), "yanlis_alarm": (yanlis_alarm, len(onay_yok)),
        "gecikme_ort": _ort(sure), "gecikme_ort_supheli_haric": _ort(sure_h), "supheli": sorted(K.supheli),
        "hata_turleri": hata_turleri,
        "hatali": [i for i in K.ids if not K.D[i]["tam"]],
    }


def karsilastir(ilk_yol: Path = ILK_HAM, sonra_yol: Path = SONRA_HAM) -> dict:
    A, B = _kosu(ilk_yol, "İlk koşu"), _kosu(sonra_yol, "Düzeltme sonrası")
    ortak = [i for i in A.ids if i in B.kayit]
    duzeldi = [i for i in ortak if not A.D[i]["tam"] and B.D[i]["tam"]]
    bozuldu = [i for i in ortak if A.D[i]["tam"] and not B.D[i]["tam"]]
    hala = [i for i in ortak if not A.D[i]["tam"] and not B.D[i]["tam"]]
    return {"ilk": kosu_ozeti(A), "sonra": kosu_ozeti(B), "duzeldi": duzeldi, "bozuldu": bozuldu, "hala_hatali": hala,
            "degismedi_dogru": len(ortak) - len(duzeldi) - len(bozuldu) - len(hala)}


def rapor_oku(yol: Path) -> str | None:
    """Rapor markdown'ını olduğu gibi okur; dosya yoksa None."""
    try:
        return yol.read_text(encoding="utf-8")
    except OSError:
        return None
