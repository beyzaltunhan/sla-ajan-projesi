"""Onay paketi şemasının testleri (schemas/onay_paketi.py).

Şema, tasarim/karar_sirasi.md Bölüm 7-8'deki kuralları zorlar: geçersiz ya da
kendi içinde tutarsız çıktı yöneticiye ulaşmamalıdır.
"""
import itertools
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

import sla_araclari as s  # noqa: E402
from schemas.onay_paketi import BILMIYORUM_YANITI, KararCiktisi  # noqa: E402

KAYNAK = [{"dokuman": "01_sla_sozlesmesi", "madde": "3.1"}]


def hesapla(**ek):
    d = {
        "davranis": "HESAPLA", "musteri": "Marmara Perakende A.Ş.", "paket": "kurumsal",
        "oncelik": "P3", "son_tarih": "2026-11-20T14:00:00", "risk": "NORMAL",
        "kredi": None, "onay_gerekli": False, "onay_nedenleri": [],
        "kaynaklar": KAYNAK, "durum": "TAMAMLANDI", "mesaj": "Son tarih hesaplandı.",
    }
    d.update(ek)
    return d


def hata(d):
    with pytest.raises(ValidationError):
        KararCiktisi.model_validate(d)


# --- HESAPLA ---
def test_hesapla_onaysiz_gecerli():
    c = KararCiktisi.model_validate(hesapla())
    assert c.davranis == "HESAPLA" and c.durum == "TAMAMLANDI"


def test_hesapla_p1_onayli_gecerli():
    c = KararCiktisi.model_validate(hesapla(
        oncelik="P1", onay_gerekli=True, onay_nedenleri=["p1_kritik"], durum="BEKLEMEDE"))
    assert c.durum == "BEKLEMEDE"


def test_hesapla_ihlal_ve_kredi_tum_nedenler():
    c = KararCiktisi.model_validate(hesapla(
        oncelik="P2", risk="IHLAL", kredi={"yuzde": 2, "tutar": 1200.0, "neden": "tam_oran"},
        onay_gerekli=True, onay_nedenleri=["ihlal", "kredi_onerisi"], durum="BEKLEMEDE"))
    assert c.kredi.yuzde == 2


def test_hesapla_eksik_onay_nedeni_reddedilir():
    hata(hesapla(risk="IHLAL", onay_gerekli=True, onay_nedenleri=[], durum="BEKLEMEDE"))
    hata(hesapla(oncelik="P1", onay_gerekli=False))                      # P1 onaysız olamaz
    hata(hesapla(risk="YUKSEK", onay_gerekli=True, onay_nedenleri=["ihlal"], durum="BEKLEMEDE"))


def test_hesapla_fazla_onay_nedeni_reddedilir():
    hata(hesapla(onay_gerekli=True, onay_nedenleri=["p1_kritik"], durum="BEKLEMEDE"))  # P3, NORMAL


def test_hesapla_kredi_varsa_kredi_onerisi_sart():
    hata(hesapla(oncelik="P2", risk="IHLAL", kredi={"yuzde": 2, "tutar": 1200.0, "neden": "tam_oran"},
                 onay_gerekli=True, onay_nedenleri=["ihlal"], durum="BEKLEMEDE"))


def test_hesapla_durum_onayla_uyumlu_olmali():
    hata(hesapla(oncelik="P1", onay_gerekli=True, onay_nedenleri=["p1_kritik"], durum="TAMAMLANDI"))
    hata(hesapla(durum="BEKLEMEDE"))                                     # onay yokken beklemede olamaz


def test_hesapla_zorunlu_alanlar():
    for alan in ("musteri", "paket", "oncelik", "son_tarih", "risk"):
        hata(hesapla(**{alan: None}))
    hata(hesapla(kaynaklar=[]))                                          # kaynaksız HESAPLA olmaz


def test_hesapla_gecersiz_degerler():
    hata(hesapla(risk="ORTA"))
    hata(hesapla(oncelik="P5"))
    hata(hesapla(paket="platin"))
    hata(hesapla(kredi={"yuzde": 120, "tutar": 5.0, "neden": "tam_oran"}))
    hata(hesapla(kredi={"yuzde": 2, "tutar": -1.0, "neden": "tam_oran"}))
    hata(hesapla(son_tarih="yarın akşam"))


def test_fazladan_alan_reddedilir():
    hata(hesapla(yonetici_onayi_verildi=True))                          # LLM'in uydurduğu alan


def test_onay_nedenleri_sla_araclariyla_ayni_mantik():
    """Şema, sla_araclari.onay_gerekli ile tüm kombinasyonlarda aynı sonucu bulmalı."""
    for p, r, k in itertools.product(["P1", "P2", "P3", "P4"], ["NORMAL", "YUKSEK", "IHLAL"], [0, 2]):
        gerekli, nedenler = s.onay_gerekli(p, r, k)
        kredi = {"yuzde": k, "tutar": 100.0, "neden": "tam_oran"} if k else None
        c = KararCiktisi.model_validate(hesapla(
            oncelik=p, risk=r, kredi=kredi, onay_gerekli=gerekli,
            onay_nedenleri=nedenler, durum="BEKLEMEDE" if gerekli else "TAMAMLANDI"))
        assert c.onay_gerekli == gerekli


# --- BILMIYORUM ---
def bilmiyorum(**ek):
    d = {"davranis": "BILMIYORUM", "neden": "kapsam_disi", "mesaj": BILMIYORUM_YANITI,
         "durum": "TAMAMLANDI"}
    d.update(ek)
    return d


def test_bilmiyorum_gecerli_ve_sabit_yanit():
    assert BILMIYORUM_YANITI == "Dokümanda bilgi bulunmamaktadır."
    for n in ("kapsam_disi", "dokumanda_yok", "musteri_kayitsiz", "ozel_anlasma"):
        KararCiktisi.model_validate(bilmiyorum(neden=n))


def test_bilmiyorum_ozel_anlasma_musteri_adi_olabilir():
    KararCiktisi.model_validate(bilmiyorum(neden="ozel_anlasma", musteri="Akdeniz Enerji A.Ş."))


def test_bilmiyorum_hesap_alani_icermez():
    hata(bilmiyorum(oncelik="P2"))
    hata(bilmiyorum(paket="gelismis"))                                   # paket varsayılmaz
    hata(bilmiyorum(son_tarih="2026-11-20T14:00:00"))
    hata(bilmiyorum(risk="NORMAL"))
    hata(bilmiyorum(kredi={"yuzde": 1, "tutar": 1.0, "neden": "tam_oran"}))
    hata(bilmiyorum(kaynaklar=KAYNAK))                                   # kaynak gösterilmez
    hata(bilmiyorum(onay_gerekli=True, onay_nedenleri=["p1_kritik"]))


def test_bilmiyorum_mesaj_ve_neden_sabit():
    hata(bilmiyorum(mesaj="Muhtemelen P2 olur."))
    hata(bilmiyorum(neden="talimat_iceriyor"))
    hata(bilmiyorum(neden=None))


# --- SORU_SOR ---
def soru_sor(**ek):
    d = {"davranis": "SORU_SOR", "neden": "musteri_belirsiz",
         "mesaj": "Hangi müşteri için talep açıyorsunuz?", "durum": "TAMAMLANDI"}
    d.update(ek)
    return d


def test_soru_sor_gecerli():
    for n in ("musteri_adi_eksik", "musteri_belirsiz", "oncelik_belirsiz"):
        KararCiktisi.model_validate(soru_sor(neden=n))


def test_soru_sor_hesap_veya_kaynak_icermez():
    hata(soru_sor(oncelik="P1"))
    hata(soru_sor(kaynaklar=KAYNAK))
    hata(soru_sor(neden="ozel_anlasma"))                                 # o BILMIYORUM nedeni
    hata(soru_sor(mesaj=""))                                             # soru metni zorunlu


# --- ENGELLE ---
def test_engelle():
    d = {"davranis": "ENGELLE", "neden": "talimat_iceriyor",
         "mesaj": "Talep metninde komut benzeri ifade var; manuel inceleme gerekir.",
         "durum": "TAMAMLANDI"}
    KararCiktisi.model_validate(d)
    hata({**d, "oncelik": "P1"})
    hata({**d, "kredi": {"yuzde": 5, "tutar": 1.0, "neden": "tam_oran"}})
    hata({**d, "neden": "kapsam_disi"})


# --- ONCELIK_BELIRLENEMEDI ---
def belirlenemedi(**ek):
    d = {"davranis": "ONCELIK_BELIRLENEMEDI", "neden": "oncelik_belirlenemedi",
         "musteri": "Karadeniz Tekstil A.Ş.", "paket": "standart",
         "kaynaklar": [{"dokuman": "02_oncelik_rehberi", "madde": "8.3"}],
         "mesaj": "Öncelik belirlenemedi; talep yöneticiye iletildi.", "durum": "TAMAMLANDI"}
    d.update(ek)
    return d


def test_oncelik_belirlenemedi_gecerli():
    KararCiktisi.model_validate(belirlenemedi())


def test_oncelik_belirlenemedi_sure_araci_atlanmis_olmali():
    hata(belirlenemedi(son_tarih="2026-11-20T14:00:00"))                 # süre aracı çalışmamalı
    hata(belirlenemedi(risk="NORMAL"))
    hata(belirlenemedi(oncelik="P3"))
    hata(belirlenemedi(kredi={"yuzde": 1, "tutar": 1.0, "neden": "tam_oran"}))
    hata(belirlenemedi(kaynaklar=[]))                                    # 02 Madde 8.3 gösterilmeli
    hata(belirlenemedi(musteri=None))


# --- ISLENEMEDI (hata yolu) ---
def test_islenemedi_yolu():
    d = {"davranis": None, "neden": "sema_hatasi", "durum": "ISLENEMEDI",
         "mesaj": "Model çıktısı doğrulanamadı; talep yöneticiye iletildi."}
    c = KararCiktisi.model_validate(d)
    assert c.davranis is None
    hata({**d, "durum": "TAMAMLANDI"})                                   # davranışsız çıktı tamamlanamaz
    hata({**d, "davranis": "HESAPLA"})
    hata({**d, "oncelik": "P1"})
    hata(soru_sor(durum="ISLENEMEDI"))


def test_json_gidis_donus():
    c = KararCiktisi.model_validate(hesapla())
    c2 = KararCiktisi.model_validate_json(c.model_dump_json())
    assert c2 == c
