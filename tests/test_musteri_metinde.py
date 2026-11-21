"""1a: talep metninde müşteri arama (müşteri adları data/musteriler.json'dan; test_seti.json kullanılmaz)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sla_araclari as s  # noqa: E402

M = json.loads((Path(__file__).resolve().parents[1] / "data" / "musteriler.json").read_text(encoding="utf-8"))["musteriler"]


def ara(metin):
    d, k = s.musteri_metinde_ara(metin, M)
    return d, (k["ad"] if k else None)


@pytest.mark.parametrize("metin,ad", [
    ("Toros Yapı Malzemeleri A.Ş. adına yazıyorum.", "Toros Yapı Malzemeleri A.Ş."),
    ("Toros Yapı'dan yazıyoruz, panel açılmıyor.", "Toros Yapı Malzemeleri A.Ş."),   # ek almış yazım
    ("TOROS YAPI için destek", "Toros Yapı Malzemeleri A.Ş."),                        # büyük harf
    ("Boğaziçi Medikal olarak yazıyoruz", "Boğaziçi Medikal Ltd. Şti."),
    ("bogazici medikal'in sistemi yavaş", "Boğaziçi Medikal Ltd. Şti."),              # ASCII yazım
    ("Marmara Perakende'nin kasa ekranı çalışmıyor", "Marmara Perakende A.Ş."),
    ("Kapadokya Seramik Ltd. Şti. adına", "Kapadokya Seramik Ltd. Şti."),
    ("Anadolu Lojistik'ten yazıyorum", "Anadolu Lojistik A.Ş."),                      # en uzun eşleşme ayırır
    ("Anadolu Gıda Tarım adına talep", "Anadolu Gıda Tarım A.Ş."),
    ("Merhaba, ben Ege Turizm'den Ayşe.", "Ege Turizm Hizmetleri A.Ş."),
    ("Bu bir ege turizm talebi", "Ege Turizm Hizmetleri A.Ş."),
])
def test_tek(metin, ad):
    assert ara(metin) == ("TEK", ad)


@pytest.mark.parametrize("metin", [
    "Anadolu olarak yazıyoruz, giriş açılmıyor.",     # iki müşteri yalnızca "Anadolu" ile eşleşir
    "Anadolu'dan yazıyorum",
])
def test_belirsiz(metin):
    assert ara(metin) == ("BELIRSIZ", None)


@pytest.mark.parametrize("metin", [
    "Sistem çalışmıyor, yardım edin.",
    "Uludağ Enerji adına yazıyorum.",                  # kayıtlı olmayan firma
])
def test_bulunamadi(metin):
    assert ara(metin) == ("BULUNAMADI", None)


def test_kisa_ad_ve_bilinen_sinir():
    # tek kelimelik kısa ad tek müşteriye uyuyorsa kabul edilir (karar_sirasi.md §3.1 "Bilinen sınırlar")
    assert ara("Toros")[0] == "TEK"
    assert ara("Ege Gıda adına yazıyorum")[0] == "TEK"       # "Ege" kısa adı Ege Turizm'e uyar (bilinen sınır)
    assert ara("Marmara Per. adına yazıyorum")[0] == "TEK"   # kısaltma değil, "Marmara" kısa adı eşleşir


def test_kelime_siniri_alt_dize_eslesmez():
    assert ara("Egemen Turizmcilik hakkında soru")[0] == "BULUNAMADI"   # "ege"/"turizm" alt dizisi sayılmaz


def test_mevcut_musteri_ara_bozulmadi():
    assert s.musteri_ara("Marmara Perakende A.Ş.", M)[0] == "TEK"
    assert s.musteri_ara("Anadolu", M)[0] == "BELIRSIZ"
    assert s.musteri_ara("Yok A.Ş.", M)[0] == "YOK"


def test_bos_metin():
    assert ara("") == ("BULUNAMADI", None)
