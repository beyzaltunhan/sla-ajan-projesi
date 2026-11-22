"""SLA hesap araçlarını MCP (Model Context Protocol) üzerinden dışarı açan sunucu (FastMCP, stdio).

Yalnızca DETERMİNİSTİK araçlar açılır; sla_araclari.py'deki mevcut fonksiyonlar sarmalanır (mantık kopyalanmaz).
Model/LLM çağrısı yoktur, Ollama gerekmez. Çalıştırma:  python mcp_sunucusu.py
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from mcp.server.fastmcp import FastMCP

import config
import sla_araclari as s
from schemas.onay_paketi import Kredi

mcp = FastMCP("sla-hesap-araclari")

Paket = Literal["standart", "gelismis", "kurumsal"]
Oncelik = Literal["P1", "P2", "P3", "P4"]


def _zaman(deger: str, alan: str) -> datetime:
    """ISO 8601 metnini (ör. 2026-11-19T10:00:00) saat dilimsiz datetime'a çevirir; hata durumunda anlaşılır mesaj verir."""
    try:
        d = datetime.fromisoformat(deger)
    except (TypeError, ValueError):
        raise ValueError(f"{alan} geçerli bir ISO 8601 zamanı olmalı (örn. 2026-11-19T10:00:00); gelen değer: {deger!r}") from None
    if d.tzinfo is not None:
        raise ValueError(f"{alan} saat dilimi içermemeli (yerel saat kabul edilir); gelen değer: {deger!r}")
    return d


def _musteriler() -> list[dict]:
    return json.loads((config.DATA_DIR / "musteriler.json").read_text(encoding="utf-8"))["musteriler"]


@mcp.tool()
def musteri_ara(ad: str) -> dict:
    """Kayıtlı müşteriler arasında firma adını arar (büyük/küçük harf ve Türkçe karakter farkı gözetilmez).

    Dönen 'durum': TEK (tek müşteri bulundu, 'kayit' dolu), BELIRSIZ (birden fazla müşteriye uyuyor),
    YOK (kayıtlı değil), BOS (ad boş). 'kayit' yalnızca TEK durumunda dolar: ad, paket (standart/gelismis/kurumsal),
    aylik_ucret (TL, KDV hariç), bu_ay_kredi_yuzdesi, ozel_anlasma. Paket asla tahmin edilmez.
    """
    durum, kayit = s.musteri_ara(ad, _musteriler())
    return {"durum": durum, "kayit": kayit}


@mcp.tool()
def son_tarih_hesapla(talep_zamani: str, paket: Paket, oncelik: Oncelik) -> dict:
    """Bir talep için ilk yanıt SON TARİHİNİ hesaplar (SLA Sözleşmesi Madde 3-5).

    talep_zamani: talebin sisteme kaydedildiği an, ISO 8601, saat dilimsiz (örn. 2026-11-19T10:00:00).
    paket: standart | gelismis | kurumsal. oncelik: P1 | P2 | P3 | P4.
    Süre mesai saatiyle (hafta içi 09:00-18:00, resmî tatiller hariç) ölçülür; kurumsal P1 7/24 işler.
    Dönen: takvim (mesai | 7/24), sure_dk (tanımlı ilk yanıt süresi), sayac_baslangici ve son_tarih (ISO 8601).
    """
    r = s.son_tarih_hesapla(_zaman(talep_zamani, "talep_zamani"), paket, oncelik)
    return {**r, "sayac_baslangici": r["sayac_baslangici"].isoformat(), "son_tarih": r["son_tarih"].isoformat()}


@mcp.tool()
def risk_degerlendir(talep_zamani: str, simdi: str, paket: Paket, oncelik: Oncelik) -> dict:
    """Talebin SLA ihlal riskini değerlendirir: NORMAL, YUKSEK (kalan süre toplamın %25'inin altında) veya IHLAL.

    Önce talep_zamani + paket + oncelik ile son tarihi hesaplar, sonra 'simdi' anına göre riski verir.
    Zamanlar ISO 8601, saat dilimsiz. Süre bitiş anında (simdi == son_tarih) ihlal sayılmaz; tam %25 kalan NORMAL'dir.
    Dönen: risk, kalan_dk (ihlalde 0), asim_dk (yalnızca ihlalde dolu), son_tarih, takvim, sure_dk.
    """
    sd = s.son_tarih_hesapla(_zaman(talep_zamani, "talep_zamani"), paket, oncelik)
    r = s.risk_degerlendir(sd["son_tarih"], _zaman(simdi, "simdi"), sd["takvim"], sd["sure_dk"])
    return {**r, "son_tarih": sd["son_tarih"].isoformat(), "takvim": sd["takvim"], "sure_dk": sd["sure_dk"]}


@mcp.tool()
def kredi_hesapla(paket: Paket, oncelik: Oncelik, ihlal_var: bool, aylik_ucret: int, bu_ay_uygulanan_yuzde: int = 0) -> dict:
    """Hizmet kredisi ÖNERİSİ hesaplar (SLA Madde 7). Kredinin uygulanması yönetici onayına bağlıdır; bu araç uygulamaz.

    Kredi yalnızca ihlal varsa, Gelişmiş/Kurumsal paketin P1-P2 talepleri için söz konusudur ve aylık tavanla sınırlıdır.
    aylik_ucret: KDV hariç aylık destek paketi bedeli (TL, tam sayı, 0 veya büyük).
    bu_ay_uygulanan_yuzde: bu takvim ayında müşteriye zaten uygulanan toplam kredi yüzdesi (0-100).
    Dönen: yuzde, tutar (TL) ve neden (ihlal_yok | tam_oran | tavan_nedeniyle_azaltildi | tavan_doldu |
    paket_krediye_dahil_degil | oncelik_krediye_dahil_degil).
    """
    if aylik_ucret < 0:
        raise ValueError(f"aylik_ucret negatif olamaz; gelen değer: {aylik_ucret}")
    if not 0 <= bu_ay_uygulanan_yuzde <= 100:
        raise ValueError(f"bu_ay_uygulanan_yuzde 0-100 arasında olmalı; gelen değer: {bu_ay_uygulanan_yuzde}")
    r = s.kredi_hesapla(paket, oncelik, ihlal_var, aylik_ucret, bu_ay_uygulanan_yuzde)
    return Kredi(**r).model_dump(mode="json")          # ajanın kullandığı şema doğrulaması


if __name__ == "__main__":
    mcp.run()          # stdio
