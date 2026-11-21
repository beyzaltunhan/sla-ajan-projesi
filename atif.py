"""Hesap araçlarının kaynak atfı (karar_sirasi.md §7, Adım 5).

Atfı LLM değil KOD ekler; hangi madde, hangi aracın çalıştığına ve sonucuna göre belirlenir.
Madde numaraları docs/ dosyalarından alınmıştır:
  01: 3.1 süre tablosu, 3.2 Kurumsal P1 7/24, 3.3 diğer süreler mesai | 4.1 mesai saatleri,
      4.2 hafta sonu/tatil mesai dışı, 4.3 tatil listesi | 5.1 sayaç başlangıcı, 5.2 mesai dışı kayıt,
      5.3 süre yalnızca mesaide işler | 6.1 yüksek risk, 6.2 ihlal, 6.4 risk etiketleri |
      7.1 kredi kapsamı, 7.2 kredi dışı paket/öncelik, 7.3 oranlar ve tavan tablosu, 7.4 aylık tavan, 7.5 onayla uygulama
  03: 2.1 onay gerektiren durumlar, 2.2 birden fazla durum, 3.1 P1/ihlal eskalasyonu, 3.2 yüksek risk,
      4.1 onaysız yapılamayacak işlemler, 5.1 onay paketi, 6.4 yönetici kararına kadar bekleme
"""
from __future__ import annotations

from datetime import datetime, timedelta

import sla_araclari as s

D01, D02, D03 = "01_sla_sozlesmesi", "02_oncelik_rehberi", "03_eskalasyon_proseduru"


def _gunler(a: datetime, b: datetime):
    gun = a.date()
    while gun <= b.date():
        yield gun
        gun += timedelta(days=1)


def son_tarih_atfi(olusturma: datetime, sd: dict) -> list[tuple[str, str]]:
    """son_tarih_hesapla çalıştı: sd = aracın döndürdüğü sözlük."""
    m = [(D01, "3.1"), (D01, "5.1")]
    if sd["takvim"] == "7/24":
        m.append((D01, "3.2"))
        return m
    m += [(D01, "3.3"), (D01, "4.1")]
    if sd["sayac_baslangici"] != olusturma:
        m.append((D01, "5.2"))
    if sd["son_tarih"].date() > sd["sayac_baslangici"].date():
        m.append((D01, "5.3"))
    gunler = list(_gunler(olusturma, sd["son_tarih"]))
    if any(g.weekday() not in s.IS_GUNLERI for g in gunler):
        m.append((D01, "4.2"))
    if any(g in s.TATILLER for g in gunler):
        m.append((D01, "4.3"))
    return m


def risk_atfi(risk: str) -> list[tuple[str, str]]:
    """risk_degerlendir çalıştı."""
    return [(D01, "6.2" if risk == "IHLAL" else "6.1"), (D01, "6.4")]


def kredi_atfi(kr: dict) -> list[tuple[str, str]]:
    """kredi_hesapla çalıştı: kr = aracın döndürdüğü sözlük."""
    m = [(D01, "7.1")]
    neden = kr["neden"]
    if neden in ("paket_krediye_dahil_degil", "oncelik_krediye_dahil_degil"):
        m.append((D01, "7.2"))
    if neden in ("tam_oran", "tavan_nedeniyle_azaltildi", "tavan_doldu"):
        m.append((D01, "7.3"))
    if neden in ("tavan_nedeniyle_azaltildi", "tavan_doldu"):
        m.append((D01, "7.4"))
    if kr["yuzde"] > 0:
        m.append((D01, "7.5"))
    return m


def onay_atfi(onay: bool, nedenler: list[str]) -> list[tuple[str, str]]:
    """onay_gerekli çalıştı."""
    m = [(D03, "2.1")]
    if not onay:
        return m
    if len(nedenler) > 1:
        m.append((D03, "2.2"))
    if "p1_kritik" in nedenler or "ihlal" in nedenler:
        m.append((D03, "3.1"))
    if "yuksek_risk" in nedenler:
        m.append((D03, "3.2"))
    if "kredi_onerisi" in nedenler:
        m.append((D03, "4.1"))
    m += [(D03, "5.1"), (D03, "6.4")]
    return m


def tekil(sirali: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return list(dict.fromkeys(sirali))
