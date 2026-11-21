"""SLA araçlarının birim testleri.

Beklenen değerlerin TAMAMI ELLE hesaplanmıştır (kodun çıktısından türetilmedi).
Takvim: 2026-11-18 Çarşamba, 11-20 Cuma, 11-21 Cumartesi, 11-23 Pazartesi;
        2026-10-29 Perşembe (tatil); 2026-12-31 Perşembe, 2027-01-01 Cuma (tatil).
"""
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sla_araclari as s  # noqa: E402


def dt(metin: str) -> datetime:
    return datetime.fromisoformat(metin)


# ------------------------------------------------------------------ config
def test_config_sureleri_dogru_aktarilmis():
    beklenen = {
        "standart": {"P1": 240, "P2": 480, "P3": 960, "P4": 1440},
        "gelismis": {"P1": 120, "P2": 240, "P3": 480, "P4": 960},
        "kurumsal": {"P1": 60, "P2": 120, "P3": 240, "P4": 480},
    }
    assert s.CONFIG["ilk_yanit_dk"] == beklenen


def test_config_kredi_ve_tatiller_dogru_aktarilmis():
    assert s.CONFIG["kredi_yuzde"] == {
        "gelismis": {"P1": 3, "P2": 1, "aylik_tavan": 10},
        "kurumsal": {"P1": 5, "P2": 2, "aylik_tavan": 20},
    }
    assert s.CONFIG["tatiller"] == ["2026-10-29", "2027-01-01", "2027-04-23", "2027-05-01"]
    assert s.CONFIG["yedi_yirmi_dort"] == [{"paket": "kurumsal", "oncelik": "P1"}]


# ------------------------------------------------------------------ takvim
@pytest.mark.parametrize(
    "gun, beklenen",
    [
        (date(2026, 11, 20), True),   # Cuma
        (date(2026, 11, 21), False),  # Cumartesi
        (date(2026, 11, 22), False),  # Pazar
        (date(2026, 10, 29), False),  # tatil (Perşembe)
        (date(2027, 1, 1), False),    # tatil (Cuma)
    ],
)
def test_is_gunu_mu(gun, beklenen):
    assert s.is_gunu_mu(gun) is beklenen


@pytest.mark.parametrize(
    "an, beklenen",
    [
        ("2026-11-18T10:00", "2026-11-18T10:00"),  # mesai içi: aynen
        ("2026-11-18T08:00", "2026-11-18T09:00"),  # mesai öncesi
        ("2026-11-18T18:00", "2026-11-19T09:00"),  # tam bitiş anı: ertesi gün
        ("2026-11-20T22:00", "2026-11-23T09:00"),  # Cuma gecesi -> Pazartesi
        ("2026-11-21T10:00", "2026-11-23T09:00"),  # Cumartesi -> Pazartesi
        ("2026-10-28T18:30", "2026-10-30T09:00"),  # 29 Ekim tatil atlanır
        ("2026-12-31T18:00", "2027-01-04T09:00"),  # 1 Ocak tatil + hafta sonu
    ],
)
def test_sonraki_mesai_baslangici(an, beklenen):
    assert s.sonraki_mesai_baslangici(dt(an)) == dt(beklenen)


# ------------------------------------------------------------- süre ekleme
@pytest.mark.parametrize(
    "baslangic, dakika, beklenen",
    [
        ("2026-11-18T10:00", 60, "2026-11-18T11:00"),
        ("2026-11-18T17:00", 60, "2026-11-18T18:00"),    # gün sonunda tam biter
        ("2026-11-18T17:30", 60, "2026-11-19T09:30"),    # ertesi güne taşar
        ("2026-11-18T16:00", 960, "2026-11-20T14:00"),   # 120 + 540 + 300
        ("2026-11-20T22:00", 240, "2026-11-23T13:00"),   # Cuma gecesi
        ("2026-12-31T17:00", 120, "2027-01-04T10:00"),   # 60 + tatil/hafta sonu + 60
    ],
)
def test_mesai_suresi_ekle(baslangic, dakika, beklenen):
    assert s.mesai_suresi_ekle(dt(baslangic), dakika) == dt(beklenen)


@pytest.mark.parametrize(
    "a, b, beklenen",
    [
        ("2026-11-18T16:00", "2026-11-20T14:00", 960),
        ("2026-11-20T17:00", "2026-11-23T10:00", 120),   # 60 Cuma + 60 Pazartesi
        ("2026-11-21T10:00", "2026-11-21T12:00", 0),     # hafta sonu
        ("2026-11-23T12:00", "2026-11-23T10:00", 0),     # b < a
    ],
)
def test_mesai_dakikasi(a, b, beklenen):
    assert s.mesai_dakikasi(dt(a), dt(b)) == beklenen


# -------------------------------------------------------------- son tarih
@pytest.mark.parametrize(
    "olusturma, paket, oncelik, sayac, son, takvim",
    [
        # Gelişmiş P2 = 240 dk, Cuma 22:00 -> sayaç Pzt 09:00 -> Pzt 13:00
        ("2026-11-20T22:00", "gelismis", "P2", "2026-11-23T09:00", "2026-11-23T13:00", "mesai"),
        # Kurumsal P1 = 60 dk, 7/24 -> Cuma 23:00
        ("2026-11-20T22:00", "kurumsal", "P1", "2026-11-20T22:00", "2026-11-20T23:00", "7/24"),
        # Kurumsal P2 = 120 dk, mesai -> Pzt 09:00 + 2 saat
        ("2026-11-20T22:00", "kurumsal", "P2", "2026-11-23T09:00", "2026-11-23T11:00", "mesai"),
        # Gelişmiş P1 = 120 dk (7/24 DEĞİL) -> Pzt 11:00
        ("2026-11-20T22:00", "gelismis", "P1", "2026-11-23T09:00", "2026-11-23T11:00", "mesai"),
        # Standart P1 = 240 dk, Çarşamba 16:00 -> 120 + 120 -> Perşembe 11:00
        ("2026-11-18T16:00", "standart", "P1", "2026-11-18T16:00", "2026-11-19T11:00", "mesai"),
        # Standart P4 = 1440 dk, Pazartesi 09:00 -> 540 + 540 + 360 -> Çarşamba 15:00
        ("2026-11-23T09:00", "standart", "P4", "2026-11-23T09:00", "2026-11-25T15:00", "mesai"),
    ],
)
def test_son_tarih_hesapla(olusturma, paket, oncelik, sayac, son, takvim):
    r = s.son_tarih_hesapla(dt(olusturma), paket, oncelik)
    assert r["sayac_baslangici"] == dt(sayac)
    assert r["son_tarih"] == dt(son)
    assert r["takvim"] == takvim


@pytest.mark.parametrize("paket, oncelik", [("platin", "P1"), ("standart", "P5"), ("", "P1")])
def test_son_tarih_gecersiz_girdi(paket, oncelik):
    with pytest.raises(ValueError):
        s.son_tarih_hesapla(dt("2026-11-18T10:00"), paket, oncelik)


# ------------------------------------------------------------------- risk
# Gelişmiş P2: toplam 240 dk, son tarih Pzt 13:00. %25 = 60 dk.
SON = "2026-11-23T13:00"


@pytest.mark.parametrize(
    "simdi, risk, kalan, asim",
    [
        ("2026-11-23T09:00", "NORMAL", 240, 0),
        ("2026-11-23T12:00", "NORMAL", 60, 0),     # tam %25: eşiğin ALTINDA değil
        ("2026-11-23T12:01", "YUKSEK", 59, 0),
        ("2026-11-23T13:00", "YUKSEK", 0, 0),      # bitiş anında: aşılmadı
        ("2026-11-23T13:01", "IHLAL", 0, 1),
        ("2026-11-21T10:00", "NORMAL", 240, 0),    # Cumartesi: sayaç henüz başlamadı
    ],
)
def test_risk_mesai(simdi, risk, kalan, asim):
    r = s.risk_degerlendir(dt(SON), dt(simdi), "mesai", 240)
    assert (r["risk"], r["kalan_dk"], r["asim_dk"]) == (risk, kalan, asim)


def test_risk_ihlal_takvim_boslugunda():
    # Son tarih Cuma 18:00, şimdi Cumartesi 10:00: aradaki mesai 0 dk ama süre geçti.
    r = s.risk_degerlendir(dt("2026-11-20T18:00"), dt("2026-11-21T10:00"), "mesai", 240)
    assert r["risk"] == "IHLAL"
    assert r["asim_dk"] == 0


@pytest.mark.parametrize(
    "simdi, risk, kalan, asim",
    [
        ("2026-11-20T22:00", "NORMAL", 60, 0),
        ("2026-11-20T22:50", "YUKSEK", 10, 0),    # 10 < 15 (%25 of 60)
        ("2026-11-20T23:01", "IHLAL", 0, 1),
    ],
)
def test_risk_yedi_yirmi_dort(simdi, risk, kalan, asim):
    r = s.risk_degerlendir(dt("2026-11-20T23:00"), dt(simdi), "7/24", 60)
    assert (r["risk"], r["kalan_dk"], r["asim_dk"]) == (risk, kalan, asim)


# ------------------------------------------------------------------ kredi
@pytest.mark.parametrize(
    "paket, oncelik, ihlal, ucret, bu_ay, yuzde, tutar, neden",
    [
        ("gelismis", "P1", False, 25000, 0, 0, 0, "ihlal_yok"),
        ("standart", "P1", True, 10000, 0, 0, 0, "paket_krediye_dahil_degil"),
        ("gelismis", "P3", True, 25000, 0, 0, 0, "oncelik_krediye_dahil_degil"),
        ("kurumsal", "P4", True, 60000, 0, 0, 0, "oncelik_krediye_dahil_degil"),
        ("gelismis", "P1", True, 25000, 0, 3, 750, "tam_oran"),
        ("gelismis", "P2", True, 25000, 0, 1, 250, "tam_oran"),
        ("kurumsal", "P1", True, 60000, 0, 5, 3000, "tam_oran"),
        ("kurumsal", "P2", True, 65000, 0, 2, 1300, "tam_oran"),
        ("kurumsal", "P1", True, 60000, 18, 2, 1200, "tavan_nedeniyle_azaltildi"),  # tavan 20: 20-18=2
        ("gelismis", "P1", True, 28000, 8, 2, 560, "tavan_nedeniyle_azaltildi"),    # tavan 10: 10-8=2
        ("gelismis", "P1", True, 25000, 10, 0, 0, "tavan_doldu"),
        ("kurumsal", "P2", True, 60000, 20, 0, 0, "tavan_doldu"),
    ],
)
def test_kredi_hesapla(paket, oncelik, ihlal, ucret, bu_ay, yuzde, tutar, neden):
    r = s.kredi_hesapla(paket, oncelik, ihlal, ucret, bu_ay)
    assert (r["yuzde"], r["tutar"], r["neden"]) == (yuzde, tutar, neden)


def test_kredi_gecersiz_girdi():
    with pytest.raises(ValueError):
        s.kredi_hesapla("platin", "P1", True, 10000, 0)
    with pytest.raises(ValueError):
        s.kredi_hesapla("gelismis", "P9", True, 10000, 0)


# ----------------------------------------------------------- onay kapısı
@pytest.mark.parametrize(
    "oncelik, risk, kredi_yuzde, gerekli, nedenler",
    [
        ("P3", "NORMAL", 0, False, []),
        ("P1", "NORMAL", 0, True, ["p1_kritik"]),
        ("P3", "YUKSEK", 0, True, ["yuksek_risk"]),
        ("P4", "IHLAL", 0, True, ["ihlal"]),
        ("P2", "IHLAL", 1, True, ["ihlal", "kredi_onerisi"]),
        ("P1", "IHLAL", 5, True, ["p1_kritik", "ihlal", "kredi_onerisi"]),
    ],
)
def test_onay_gerekli(oncelik, risk, kredi_yuzde, gerekli, nedenler):
    assert s.onay_gerekli(oncelik, risk, kredi_yuzde) == (gerekli, nedenler)


# --------------------------------------------------------------- müşteri
MUSTERILER = [
    {"ad": "Mavi Kargo Ltd.", "paket": "standart", "aylik_ucret": 10000},
    {"ad": "Kaya Enerji A.Ş.", "paket": "kurumsal", "aylik_ucret": 65000},
    {"ad": "Kaya Gıda A.Ş.", "paket": "standart", "aylik_ucret": 12000},
]


@pytest.mark.parametrize(
    "aranan, beklenen_ad",
    [
        ("Mavi Kargo Ltd.", "Mavi Kargo Ltd."),   # tam eşleşme
        ("MAVİ KARGO LTD.", "Mavi Kargo Ltd."),   # büyük harf / Türkçe karakter
        ("mavi kargo", "Mavi Kargo Ltd."),        # tekil kısmi eşleşme
        ("Kaya Enerji", "Kaya Enerji A.Ş."),
    ],
)
def test_musteri_bul_basarili(aranan, beklenen_ad):
    assert s.musteri_bul(aranan, MUSTERILER)["ad"] == beklenen_ad


@pytest.mark.parametrize("aranan", ["Kaya", "Bilinmeyen Firma", "", "   "])
def test_musteri_bul_belirsiz_veya_yok(aranan):
    # "Kaya" iki müşteriye uyar -> belirsiz -> None (paket varsayılmaz)
    assert s.musteri_bul(aranan, MUSTERILER) is None


# --- Risk etiketi tutarlılığı (config <-> kod <-> dokümanlar) ---
def test_risk_etiketleri_config_kod_dokuman_uyumlu():
    import json, pathlib
    kok = pathlib.Path(__file__).resolve().parent.parent
    cfg = json.load(open(kok / "data" / "sla_config.json", encoding="utf-8"))
    etiketler = set(cfg["risk"]["seviyeler"])
    assert etiketler == {"NORMAL", "YUKSEK", "IHLAL"}
    from datetime import datetime, timedelta
    from sla_araclari import risk_degerlendir
    son = datetime(2026, 11, 18, 12, 0)
    for simdi in (son - timedelta(minutes=200), son - timedelta(minutes=10), son + timedelta(minutes=1)):
        r = risk_degerlendir(son, simdi, "7/24", 240)
        assert r["risk"] in etiketler
    for dosya in ("01_sla_sozlesmesi.md", "03_eskalasyon_proseduru.md"):
        metin = (kok / "docs" / dosya).read_text(encoding="utf-8")
        for e in etiketler:
            assert e in metin, f"{dosya} içinde {e} yok"


# --- musteri_ara: üç durumu ayırır (karar_sirasi.md Bölüm 4) ---
@pytest.mark.parametrize(
    "aranan, durum",
    [
        ("Kaya", "BELIRSIZ"),            # birden fazla kayda uyar -> SORU_SOR
        ("Bilinmeyen Firma", "YOK"),     # hiçbirine uymaz -> BILMIYORUM
        ("", "BOS"),                     # ad yok -> SORU_SOR (musteri_adi_eksik)
        ("   ", "BOS"),
        (None, "BOS"),
    ],
)
def test_musteri_ara_durumlar(aranan, durum):
    assert s.musteri_ara(aranan, MUSTERILER)[0] == durum
    assert s.musteri_ara(aranan, MUSTERILER)[1] is None


def test_musteri_ara_tek_eslesme_kaydi_dondurur():
    durum, kayit = s.musteri_ara(MUSTERILER[0]["ad"], MUSTERILER)
    assert durum == "TEK" and kayit["ad"] == MUSTERILER[0]["ad"]


def test_musteri_bul_eski_davranis_korunur():
    assert s.musteri_bul("Kaya", MUSTERILER) is None
    assert s.musteri_bul("Bilinmeyen Firma", MUSTERILER) is None


# --- data/musteriler.json (gerçek veri dosyası) ---
def _musteri_verisi():
    import json, pathlib
    kok = pathlib.Path(__file__).resolve().parent.parent
    cfg = json.load(open(kok / "data" / "sla_config.json", encoding="utf-8"))
    veri = json.load(open(kok / "data" / "musteriler.json", encoding="utf-8"))
    return cfg, veri["musteriler"]


def test_musteriler_json_yapisi():
    cfg, m = _musteri_verisi()
    assert len(m) == 10
    assert len({x["ad"] for x in m}) == 10
    for x in m:
        assert set(x) == {"ad", "paket", "aylik_ucret", "bu_ay_kredi_yuzdesi", "ozel_anlasma"}
        assert x["paket"] in cfg["paketler"]
        assert x["aylik_ucret"] > 0 and x["aylik_ucret"] % 1000 == 0
        assert isinstance(x["ozel_anlasma"], bool)
        tavan = cfg["kredi_yuzde"].get(x["paket"], {}).get("aylik_tavan", 0)
        assert 0 <= x["bu_ay_kredi_yuzdesi"] <= tavan


def test_musteriler_json_senaryo_kapsami():
    cfg, m = _musteri_verisi()
    assert {x["paket"] for x in m} == set(cfg["paketler"])          # üç paket de var
    assert 1 <= sum(x["ozel_anlasma"] for x in m) <= 2               # özel anlaşmalı 1-2
    assert any(x["bu_ay_kredi_yuzdesi"] > 0 for x in m)              # kredi geçmişi olan var
    tavan_dolu = [x for x in m if x["paket"] != "standart"
                  and x["bu_ay_kredi_yuzdesi"] == cfg["kredi_yuzde"][x["paket"]]["aylik_tavan"]]
    assert tavan_dolu                                                 # tavanı dolu müşteri var


def test_musteriler_json_arama_senaryolari():
    _, m = _musteri_verisi()
    for x in m:                                                       # her müşteri tam adıyla bulunur
        assert s.musteri_ara(x["ad"], m)[0] == "TEK"
    assert s.musteri_ara("Anadolu", m)[0] == "BELIRSIZ"              # benzer adlı iki müşteri
    assert s.musteri_ara("Marmara", m)[0] == "TEK"
    assert s.musteri_ara("Yıldız Danışmanlık", m)[0] == "YOK"
