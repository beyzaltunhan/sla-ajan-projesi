"""SLA hesap araçları (ajanın çağıracağı deterministik fonksiyonlar).

Tasarım ilkeleri:
- Hiçbir fonksiyon datetime.now() kullanmaz; "şimdi" ve talep zamanı dışarıdan verilir.
- Hiçbir fonksiyon LLM çağırmaz; aynı girdi her zaman aynı çıktıyı verir.
- Tüm sayılar data/sla_config.json dosyasından okunur (tek kaynak).
- Saat dilimi yoktur; tüm datetime nesneleri "naive" (yerel saat) kabul edilir.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

CONFIG_YOLU = Path(__file__).resolve().parent / "data" / "sla_config.json"


def config_yukle(yol: Path = CONFIG_YOLU) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


CONFIG = config_yukle()

MESAI_BASLANGIC = time.fromisoformat(CONFIG["mesai"]["baslangic"])
MESAI_BITIS = time.fromisoformat(CONFIG["mesai"]["bitis"])
IS_GUNLERI = set(CONFIG["mesai"]["is_gunleri"])
TATILLER = {date.fromisoformat(t) for t in CONFIG["tatiller"]}


# ------------------------------------------------------------------ takvim
def is_gunu_mu(gun: date) -> bool:
    """Hafta içi ve resmî tatil değilse True."""
    return gun.weekday() in IS_GUNLERI and gun not in TATILLER


def sonraki_mesai_baslangici(an: datetime) -> datetime:
    """`an` mesai içindeyse aynen döner; değilse bir sonraki mesai başlangıcını verir."""
    gun = an.date()
    if is_gunu_mu(gun):
        if an.time() < MESAI_BASLANGIC:
            return datetime.combine(gun, MESAI_BASLANGIC)
        if an.time() < MESAI_BITIS:
            return an
    gun += timedelta(days=1)
    while not is_gunu_mu(gun):
        gun += timedelta(days=1)
    return datetime.combine(gun, MESAI_BASLANGIC)


def mesai_suresi_ekle(baslangic: datetime, dakika: int) -> datetime:
    """Başlangıçtan itibaren yalnızca mesai dakikalarını sayarak bitiş anını bulur."""
    if dakika <= 0:
        raise ValueError("dakika pozitif olmalı")
    an = sonraki_mesai_baslangici(baslangic)
    kalan = dakika
    while True:
        gun_sonu = datetime.combine(an.date(), MESAI_BITIS)
        musait = int((gun_sonu - an).total_seconds() // 60)
        if kalan <= musait:
            return an + timedelta(minutes=kalan)
        kalan -= musait
        an = sonraki_mesai_baslangici(gun_sonu)


def mesai_dakikasi(a: datetime, b: datetime) -> int:
    """a ile b arasındaki mesai dakikası (b <= a ise 0)."""
    if b <= a:
        return 0
    toplam = 0
    an = sonraki_mesai_baslangici(a)
    while an < b:
        gun_sonu = datetime.combine(an.date(), MESAI_BITIS)
        parca_sonu = min(gun_sonu, b)
        toplam += int((parca_sonu - an).total_seconds() // 60)
        an = sonraki_mesai_baslangici(gun_sonu)
    return toplam


def _takvim_dakikasi(a: datetime, b: datetime) -> int:
    return max(0, int((b - a).total_seconds() // 60))


# ---------------------------------------------------------------- son tarih
def yedi_yirmi_dort_mu(paket: str, oncelik: str) -> bool:
    return {"paket": paket, "oncelik": oncelik} in CONFIG["yedi_yirmi_dort"]


def son_tarih_hesapla(olusturma: datetime, paket: str, oncelik: str) -> dict:
    """İlk yanıt için son tarihi hesaplar (SLA Madde 3-5)."""
    sureler = CONFIG["ilk_yanit_dk"]
    if paket not in sureler or oncelik not in sureler[paket]:
        raise ValueError(f"Tanımsız paket/öncelik: {paket!r} / {oncelik!r}")
    sure = sureler[paket][oncelik]
    if yedi_yirmi_dort_mu(paket, oncelik):
        takvim = "7/24"
        sayac = olusturma
        son = olusturma + timedelta(minutes=sure)
    else:
        takvim = "mesai"
        sayac = sonraki_mesai_baslangici(olusturma)
        son = mesai_suresi_ekle(olusturma, sure)
    return {
        "paket": paket,
        "oncelik": oncelik,
        "takvim": takvim,
        "sure_dk": sure,
        "sayac_baslangici": sayac,
        "son_tarih": son,
    }


# -------------------------------------------------------------------- risk
def risk_degerlendir(son_tarih: datetime, simdi: datetime, takvim: str, toplam_dk: int) -> dict:
    """IHLAL / YUKSEK / NORMAL.

    - Süre bitiş anında (simdi == son_tarih) henüz aşılmış sayılmaz.
    - Kalan süre toplamın %25'inin *altındaysa* YUKSEK (tam %25 NORMAL).
    """
    olc = mesai_dakikasi if takvim == "mesai" else _takvim_dakikasi
    if simdi > son_tarih:
        return {"risk": "IHLAL", "kalan_dk": 0, "asim_dk": olc(son_tarih, simdi)}
    kalan = olc(simdi, son_tarih)
    esik = CONFIG["risk"]["yuksek_risk_orani_yuzde"]
    risk = "YUKSEK" if kalan * 100 < esik * toplam_dk else "NORMAL"
    return {"risk": risk, "kalan_dk": kalan, "asim_dk": 0}


# ------------------------------------------------------------------- kredi
def kredi_hesapla(
    paket: str,
    oncelik: str,
    ihlal_var: bool,
    aylik_ucret: int,
    bu_ay_uygulanan_yuzde: int = 0,
) -> dict:
    """Hizmet kredisi ÖNERİSİ (SLA Madde 7). Uygulanması yönetici onayına bağlıdır."""
    if paket not in CONFIG["paketler"] or oncelik not in CONFIG["oncelikler"]:
        raise ValueError(f"Tanımsız paket/öncelik: {paket!r} / {oncelik!r}")
    if not ihlal_var:
        return {"yuzde": 0, "tutar": 0, "neden": "ihlal_yok"}
    oranlar = CONFIG["kredi_yuzde"].get(paket)
    if oranlar is None:
        return {"yuzde": 0, "tutar": 0, "neden": "paket_krediye_dahil_degil"}
    if oncelik not in ("P1", "P2"):
        return {"yuzde": 0, "tutar": 0, "neden": "oncelik_krediye_dahil_degil"}
    istenen = oranlar[oncelik]
    izin = max(0, oranlar["aylik_tavan"] - bu_ay_uygulanan_yuzde)
    if izin == 0:
        return {"yuzde": 0, "tutar": 0, "neden": "tavan_doldu"}
    yuzde = min(istenen, izin)
    neden = "tam_oran" if yuzde == istenen else "tavan_nedeniyle_azaltildi"
    return {"yuzde": yuzde, "tutar": int(round(aylik_ucret * yuzde / 100)), "neden": neden}


# ------------------------------------------------------------- onay kapısı
def onay_gerekli(oncelik: str, risk: str, kredi_yuzde: int) -> tuple[bool, list[str]]:
    """Kritik durumlarda insan onayı şarttır (karar_sirasi.md, adım 6)."""
    nedenler: list[str] = []
    if oncelik == "P1":
        nedenler.append("p1_kritik")
    if risk == "IHLAL":
        nedenler.append("ihlal")
    elif risk == "YUKSEK":
        nedenler.append("yuksek_risk")
    if kredi_yuzde > 0:
        nedenler.append("kredi_onerisi")
    return (bool(nedenler), nedenler)


# ----------------------------------------------------------------- müşteri
_TR = str.maketrans("ışğüöç", "isguoc")


def _norm(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "i").lower().translate(_TR).strip()


def musteri_ara(ad: str | None, musteriler: list[dict]) -> tuple[str, dict | None]:
    """Müşteri adını arar ve durumu ayırır (karar_sirasi.md Bölüm 4).

    Döner: (durum, kayit)
    - "BOS":      ad boş -> SORU_SOR (musteri_adi_eksik)
    - "TEK":      tam eşleşme, yoksa tekil kısmi eşleşme -> kayıt döner
    - "BELIRSIZ": birden fazla kayda uyuyor -> SORU_SOR (musteri_belirsiz)
    - "YOK":      hiçbir kayda uymuyor -> BILMIYORUM (musteri_kayitsiz)
    Kayıt yalnızca "TEK" durumunda döner; paket asla varsayılmaz.
    """
    hedef = _norm(ad or "")
    if not hedef:
        return "BOS", None
    tam = [m for m in musteriler if _norm(m["ad"]) == hedef]
    if len(tam) == 1:
        return "TEK", tam[0]
    if len(tam) > 1:
        return "BELIRSIZ", None
    kismi = [m for m in musteriler if hedef in _norm(m["ad"])]
    if len(kismi) == 1:
        return "TEK", kismi[0]
    return ("BELIRSIZ" if len(kismi) > 1 else "YOK"), None


def musteri_bul(ad: str, musteriler: list[dict]) -> dict | None:
    """Geriye dönük uyumluluk: yalnızca tek eşleşmede kayıt, aksi halde None."""
    durum, kayit = musteri_ara(ad, musteriler)
    return kayit if durum == "TEK" else None
