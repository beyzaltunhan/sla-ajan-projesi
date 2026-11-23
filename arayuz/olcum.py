"""Ölçüm sonuçlarını dosyalardan OKUR (sayılar kodda elle yazılmaz): ham jsonl -> degerlendirme/ ölçüm mantığı."""
from __future__ import annotations

import re
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
       "temiz sayım ilk ölçümdür.")


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


# ------------------------------------------------------------------ hata adı etiketleri ve "doğru kaynak bulma"
HATA_ADI = {"1a": "1a Müşteri bulma", "1b": "1b Komut tespiti", "1c": "1c Talep türü", "1d": "1d Firma adı yedeği",
            "4 öncelik önerisi": "Öncelik önerisi", "5": "Öncelik yönlendirme", "6": "Hesaplar"}


def hata_adi(a: str) -> str:
    """Hata adımı kodunu okunur ada çevirir (bilinmeyen kod olduğu gibi kalır)."""
    return HATA_ADI.get(a, a)


def _kac(metin: str) -> tuple[int, int]:
    a, b = metin.strip().split("/")
    return int(a), int(b)


def davranis_gecikme(rapor_metni: str | None) -> list[dict]:
    """duzeltme_sonrasi_rapor.md "Alınan davranışa göre toplam süre (sn)" tablosunu OKUR.
    Satır: davranis, ilk/sonra = {n, ort, maks} (sayılar rapordan, kodda yazılı değildir)."""
    if not rapor_metni:
        return []
    m = re.search(r"\*\*Alınan davranışa göre toplam süre \(sn\)\*\*(.*?)(?=^\*\*|^##\s|\Z)", rapor_metni, re.S | re.M)
    if not m:
        return []
    sonuc = []
    for satir in m.group(1).splitlines():
        h = [x.strip() for x in satir.strip().strip("|").split("|")]
        if len(h) != 9 or not h[0] or h[0].startswith(("-", "Alınan")):
            continue
        try:
            v = [float(x) for x in h[1:]]
        except ValueError:
            continue
        sonuc.append({"davranis": h[0], "ilk": {"n": int(v[0]), "ort": v[1], "maks": v[3]},
                      "sonra": {"n": int(v[4]), "ort": v[5], "maks": v[7]}})
    return sonuc


def kaynak_bulma(rapor_metni: str | None) -> list[dict]:
    """duzeltme_sonrasi_rapor.md içindeki "Doğru kaynak maddeyi bulma" tablosunu OKUR (sayılar kodda yazılı değildir).
    Satır: kume, grup, talep, ilk/sonra = {tumu, en_az_biri, madde} (her biri (doğru, N))."""
    if not rapor_metni:
        return []
    m = re.search(r"^##\s*\d+\.\s*Doğru kaynak maddeyi bulma.*?(?=^##\s|\Z)", rapor_metni, re.S | re.M)
    if not m:
        return []
    sonuc = []
    for satir in m.group(0).splitlines():
        h = [x.strip() for x in satir.strip().strip("|").split("|")]
        if len(h) != 5 or not h[2].isdigit():
            continue
        try:
            ilk = [_kac(x) for x in h[3].split(" / ")]
            sonra = [_kac(x) for x in h[4].split(" / ")]
        except ValueError:
            continue
        if len(ilk) != 3 or len(sonra) != 3:
            continue
        ad = ("tumu", "en_az_biri", "madde")
        sonuc.append({"kume": h[0], "grup": h[1], "talep": int(h[2]), "ilk": dict(zip(ad, ilk)), "sonra": dict(zip(ad, sonra))})
    return sonuc
