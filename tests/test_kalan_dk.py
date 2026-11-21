"""KararCiktisi.kalan_dk: isteğe bağlı, yalnızca HESAPLA'da, negatif olamaz."""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schemas.onay_paketi import KararCiktisi  # noqa: E402

HESAPLA = dict(davranis="HESAPLA", musteri="Karadeniz Tekstil A.Ş.", paket="standart", oncelik="P3",
               son_tarih="2026-11-18T18:00:00", risk="NORMAL", durum="TAMAMLANDI", mesaj="x",
               kaynaklar=[{"dokuman": "02_oncelik_rehberi", "madde": "5.1"}])


def test_kalan_dk_opsiyonel_varsayilan_none():
    assert KararCiktisi(**HESAPLA).kalan_dk is None


def test_kalan_dk_hesaplada_kabul():
    assert KararCiktisi(**HESAPLA, kalan_dk=480).kalan_dk == 480
    assert KararCiktisi(**{**HESAPLA, "risk": "IHLAL", "onay_gerekli": True, "onay_nedenleri": ["ihlal"],
                           "durum": "BEKLEMEDE"}, kalan_dk=0).kalan_dk == 0


def test_kalan_dk_negatif_reddedilir():
    with pytest.raises(ValidationError):
        KararCiktisi(**HESAPLA, kalan_dk=-1)


@pytest.mark.parametrize("ek", [dict(davranis="ENGELLE", neden="talimat_iceriyor"),
                                dict(davranis="SORU_SOR", neden="musteri_adi_eksik")])
def test_kalan_dk_hesap_disinda_yasak(ek):
    with pytest.raises(ValidationError):
        KararCiktisi(**ek, durum="TAMAMLANDI", mesaj="x", kalan_dk=5)
