"""Doküman <-> config <-> kod tutarlılık denetimi.

Çalıştırma:  python tutarlilik_kontrolu.py
Çıkış kodu 0 = tutarlı, 1 = tutarsızlık var. Aynı kontroller pytest ile de çalışır
(tests/test_tutarlilik.py). Hesap rakamlarının tek kaynağı data/sla_config.json'dur;
dokümanlar bu rakamları metin olarak tekrar eder, burada birebir karşılaştırılır.
"""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

AYLAR = {"Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6, "Temmuz": 7,
         "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12}
PAKET_AD = {"Standart": "standart", "Gelişmiş": "gelismis", "Kurumsal": "kurumsal"}
DOKUMANLAR = ["01_sla_sozlesmesi", "02_oncelik_rehberi", "03_eskalasyon_proseduru", "04_destek_sss"]
BASLIK_SAYISI = {"01_sla_sozlesmesi": 8, "02_oncelik_rehberi": 10, "03_eskalasyon_proseduru": 10}
ESKI_ADLAR = ["Lodos"]


def yukle(kok: Path):
    kok = Path(kok)
    cfg = json.loads((kok / "data" / "sla_config.json").read_text(encoding="utf-8"))
    docs = {d: (kok / "docs" / f"{d}.md").read_text(encoding="utf-8") for d in DOKUMANLAR}
    docs["karar_sirasi"] = (kok / "tasarim" / "karar_sirasi.md").read_text(encoding="utf-8")
    return cfg, docs


def _bolum(metin: str, madde: int) -> str:
    m = re.search(rf"^## Madde {madde} –.*?(?=^## |\Z)", metin, flags=re.S | re.M)
    return m.group(0) if m else ""


def _tablo_satirlari(bolum: str):
    for satir in bolum.splitlines():
        if satir.startswith("|"):
            yield [h.strip() for h in satir.strip().strip("|").split("|")]


# ----------------------------------------------------------------------
def _sureler(cfg, d01, hata):
    bolum = _bolum(d01, 3)
    bulunan, yildiz = {}, set()
    for hucreler in _tablo_satirlari(bolum):
        if hucreler[0] in PAKET_AD and len(hucreler) == 5:
            paket = PAKET_AD[hucreler[0]]
            for oncelik, h in zip(["P1", "P2", "P3", "P4"], hucreler[1:]):
                m = re.match(r"(\d+) saat(\*?)$", h)
                if not m:
                    hata.append(f"Süre tablosu: {hucreler[0]} {oncelik} hücresi okunamadı: {h!r}")
                    continue
                bulunan[(paket, oncelik)] = int(m.group(1)) * 60
                if m.group(2):
                    yildiz.add((paket, oncelik))
    for paket, satir in cfg["ilk_yanit_dk"].items():
        for oncelik, dk in satir.items():
            if bulunan.get((paket, oncelik)) != dk:
                hata.append(f"Süre uyuşmazlığı: {paket} {oncelik}: doküman={bulunan.get((paket, oncelik))} dk, config={dk} dk")
    beklenen = {(x["paket"], x["oncelik"]) for x in cfg["yedi_yirmi_dort"]}
    if yildiz != beklenen:
        hata.append(f"7/24 işareti (*) uyuşmazlığı: doküman={sorted(yildiz)}, config={sorted(beklenen)}")


def _kredi(cfg, d01, hata):
    bulunan = {}
    for h in _tablo_satirlari(_bolum(d01, 7)):
        if h[0] in PAKET_AD and len(h) == 4 and all(re.fullmatch(r"%\d+", x) for x in h[1:]):
            p1, p2, tavan = (int(x[1:]) for x in h[1:])
            bulunan[PAKET_AD[h[0]]] = {"P1": p1, "P2": p2, "aylik_tavan": tavan}
    if bulunan != cfg["kredi_yuzde"]:
        hata.append(f"Kredi tablosu uyuşmazlığı: doküman={bulunan}, config={cfg['kredi_yuzde']}")


def _takvim(cfg, d01, hata):
    s4 = _bolum(d01, 4)
    satir41 = next((s for s in s4.splitlines() if s.startswith("4.1")), "")
    b, e = cfg["mesai"]["baslangic"], cfg["mesai"]["bitis"]
    if f"{b}–{e}" not in satir41 or "Pazartesi–Cuma" not in satir41 or cfg["mesai"]["is_gunleri"] != [0, 1, 2, 3, 4]:
        hata.append(f"Mesai uyuşmazlığı: doküman 4.1 satırı {b}–{e} Pazartesi–Cuma ile uyuşmuyor")
    satir43 = next((s for s in s4.splitlines() if s.startswith("4.3")), "")
    tarihler = {f"{int(y):04d}-{AYLAR[a]:02d}-{int(g):02d}"
                for g, a, y in re.findall(r"(\d{1,2}) (" + "|".join(AYLAR) + r") (\d{4})", satir43)}
    if tarihler != set(cfg["tatiller"]):
        hata.append(f"Tatil uyuşmazlığı: doküman={sorted(tarihler)}, config={sorted(cfg['tatiller'])}")


def _esik(cfg, d01, hata):
    satir = next((s for s in _bolum(d01, 6).splitlines() if s.startswith("6.1")), "")
    yuzdeler = set(re.findall(r"%(\d+)", satir))
    beklenen = {str(cfg["risk"]["yuksek_risk_orani_yuzde"])}
    if yuzdeler != beklenen:
        hata.append(f"Risk eşiği uyuşmazlığı: 6.1 satırındaki yüzdeler={sorted(yuzdeler)}, config={sorted(beklenen)}")


def _etiketler(cfg, docs, hata):
    for etiket in cfg["risk"]["seviyeler"]:
        for d in ("01_sla_sozlesmesi", "03_eskalasyon_proseduru"):
            if etiket not in docs[d]:
                hata.append(f"Risk etiketi {etiket} {d} içinde yok")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sla_araclari as s
    kodlar = set()
    for p, r, k in itertools.product(["P1", "P2", "P3", "P4"], cfg["risk"]["seviyeler"], [0, 2]):
        kodlar |= set(s.onay_gerekli(p, r, k)[1])
    for kod in sorted(kodlar):
        if kod not in docs["03_eskalasyon_proseduru"]:
            hata.append(f"Onay neden kodu {kod} 03 içinde yok")


def _basliklar(docs, hata):
    for d, n in BASLIK_SAYISI.items():
        bulunan = [int(x) for x in re.findall(r"^## Madde (\d+) –", docs[d], flags=re.M)]
        if bulunan != list(range(1, n + 1)):
            hata.append(f"Madde başlıkları {d}: beklenen 1..{n}, bulunan {bulunan}")
    sorular = [int(x) for x in re.findall(r"^## Soru (\d+) –", docs["04_destek_sss"], flags=re.M)]
    if sorular != list(range(1, 11)):
        hata.append(f"Soru başlıkları 04: beklenen 1..10, bulunan {sorular}")


ATIF = re.compile(r"(?P<on>SLA Sözleşmesi|SLA|Doküman 0[1-4]\)?|\(?0[1-4]|Öncelik Belirleme Rehberi)?\s*Madde (?P<no>\d+(?:\.\d+)?)")
ON_DOKUMAN = {"SLA": "01", "Doküman 01": "01", "Doküman 02": "02", "Doküman 03": "03", "Doküman 04": "04",
              "Öncelik Belirleme Rehberi": "02"}
NO_DOSYA = {"01": "01_sla_sozlesmesi", "02": "02_oncelik_rehberi", "03": "03_eskalasyon_proseduru"}
VARSAYILAN = {"01_sla_sozlesmesi": "01", "02_oncelik_rehberi": "02", "03_eskalasyon_proseduru": "03"}


def _on_coz(on: str | None):
    if not on:
        return None
    on = on.strip("()").strip()
    if on.startswith("SLA"):
        return "01"
    if on in ON_DOKUMAN:
        return ON_DOKUMAN[on]
    return on[-2:] if re.fullmatch(r"0[1-4]", on[-2:]) else None


def _atiflar(docs, hata):
    var = {}
    for no, d in NO_DOSYA.items():
        t = docs[d]
        var[no] = set(re.findall(r"^## Madde (\d+) –", t, flags=re.M)) | set(re.findall(r"^(\d+\.\d+) ", t, flags=re.M))
    for d, t in docs.items():
        for satir in t.splitlines():
            onceki = None
            for m in ATIF.finditer(satir):
                hedef = _on_coz(m.group("on"))
                if hedef is None:
                    ara = satir[onceki.end():m.start()] if onceki else ""
                    if onceki and ara.strip() in ("ve", ","):
                        hedef = onceki_hedef
                    else:
                        hedef = VARSAYILAN.get(d)
                onceki, onceki_hedef = m, hedef
                if hedef is None or hedef == "04":
                    continue
                if m.group("no") not in var[hedef]:
                    hata.append(f"Kırık atıf: {d}: 'Madde {m.group('no')}' Doküman {hedef} içinde yok")


def _firma(cfg, docs, hata):
    for d in DOKUMANLAR:
        if cfg["firma_adi"] not in docs[d]:
            hata.append(f"Firma adı ({cfg['firma_adi']}) {d} içinde yok")
    for d, t in docs.items():
        for eski in ESKI_ADLAR:
            if eski in t:
                hata.append(f"Eski firma adı {eski!r} {d} içinde duruyor")


def kontrol_et(cfg: dict, docs: dict) -> list[str]:
    hata: list[str] = []
    _sureler(cfg, docs["01_sla_sozlesmesi"], hata)
    _kredi(cfg, docs["01_sla_sozlesmesi"], hata)
    _takvim(cfg, docs["01_sla_sozlesmesi"], hata)
    _esik(cfg, docs["01_sla_sozlesmesi"], hata)
    _etiketler(cfg, docs, hata)
    _basliklar(docs, hata)
    _atiflar(docs, hata)
    _firma(cfg, docs, hata)
    return hata


def main() -> int:
    cfg, docs = yukle(Path(__file__).resolve().parent)
    hatalar = kontrol_et(cfg, docs)
    if hatalar:
        print("TUTARSIZLIK VAR:")
        for h in hatalar:
            print(" -", h)
        return 1
    print("TUTARSIZLIK YOK (süre, kredi, tatil, mesai, eşik, etiket, başlık, atıf, firma adı)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
