"""tutarlilik_kontrolu.py testleri: doküman <-> config <-> kod uyumu."""
import copy
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

import tutarlilik_kontrolu as tk  # noqa: E402


@pytest.fixture
def cfg_docs():
    cfg, docs = tk.yukle(KOK)
    return copy.deepcopy(cfg), dict(docs)


def test_gercek_dosyalar_tutarli():
    cfg, docs = tk.yukle(KOK)
    assert tk.kontrol_et(cfg, docs) == []


def degistir(docs, ad, eski, yeni):
    assert eski in docs[ad], f"test hazırlığı: {eski!r} {ad} içinde yok"
    docs[ad] = docs[ad].replace(eski, yeni, 1)


def hatalar(cfg, docs):
    return " | ".join(tk.kontrol_et(cfg, docs))


def test_sure_tablosu_bozulursa_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    degistir(docs, "01_sla_sozlesmesi", "| Standart | 4 saat | 8 saat |", "| Standart | 4 saat | 9 saat |")
    assert "süre" in hatalar(cfg, docs).lower()


def test_config_suresi_degisirse_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    cfg["ilk_yanit_dk"]["gelismis"]["P2"] = 300
    assert "süre" in hatalar(cfg, docs).lower()


def test_kredi_tablosu_bozulursa_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    degistir(docs, "01_sla_sozlesmesi", "| Kurumsal | %5 | %2 | %20 |", "| Kurumsal | %5 | %2 | %25 |")
    assert "kredi" in hatalar(cfg, docs).lower()


def test_tatil_listesi_bozulursa_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    degistir(docs, "01_sla_sozlesmesi", "23 Nisan 2027 ve ", "")
    assert "tatil" in hatalar(cfg, docs).lower()


def test_mesai_ve_esik_bozulursa_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    degistir(docs, "01_sla_sozlesmesi", "09:00–18:00", "08:30–18:00")
    assert "mesai" in hatalar(cfg, docs).lower()
    cfg, docs = tk.yukle(KOK)
    degistir(docs, "01_sla_sozlesmesi", "%25'inin altına", "%30'unun altına")
    assert "eşiği" in hatalar(cfg, docs).lower()


def test_yedi_yirmi_dort_yildizi_kaydirilirsa_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    degistir(docs, "01_sla_sozlesmesi", "1 saat*", "1 saat")
    degistir(docs, "01_sla_sozlesmesi", "| Gelişmiş | 2 saat |", "| Gelişmiş | 2 saat* |")
    assert "7/24" in hatalar(cfg, docs)


def test_risk_etiketi_eksikse_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    docs["03_eskalasyon_proseduru"] = docs["03_eskalasyon_proseduru"].replace("YUKSEK", "YUKSEKTIR_X").replace("YUKSEKTIR_X", "ORTA")
    assert "etiket" in hatalar(cfg, docs).lower()


def test_onay_neden_kodu_eksikse_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    docs["03_eskalasyon_proseduru"] = docs["03_eskalasyon_proseduru"].replace("kredi_onerisi", "kredi_x")
    assert "onay neden" in hatalar(cfg, docs).lower()


def test_madde_basligi_silinirse_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    degistir(docs, "01_sla_sozlesmesi", "## Madde 6 – ", "## Bölüm 6 – ")
    assert "başlık" in hatalar(cfg, docs).lower()


def test_kirik_atif_yakalanir(cfg_docs):
    cfg, docs = cfg_docs
    degistir(docs, "04_destek_sss", "Doküman 02 Madde 2.3", "Doküman 02 Madde 2.9")
    assert "atıf" in hatalar(cfg, docs).lower()
    cfg, docs = tk.yukle(KOK)
    degistir(docs, "04_destek_sss", "SLA Madde 7,", "SLA Madde 12,")
    assert "atıf" in hatalar(cfg, docs).lower()


def test_atif_ayni_satirdaki_onceki_dokumani_miras_alir(cfg_docs):
    # 03'teki "(Doküman 01) Madde 6.3 ve Madde 7.5" ikinci atfı da 01'e aittir
    cfg, docs = cfg_docs
    degistir(docs, "03_eskalasyon_proseduru", "Madde 6.3 ve Madde 7.5", "Madde 6.3 ve Madde 7.9")
    assert "atıf" in hatalar(cfg, docs).lower()


def test_firma_adi_ve_eski_ad(cfg_docs):
    cfg, docs = cfg_docs
    docs["02_oncelik_rehberi"] = docs["02_oncelik_rehberi"].replace("Poyraz Bulut Yazılım A.Ş.", "Lodos Yazılım A.Ş.")
    h = hatalar(cfg, docs).lower()
    assert "firma" in h
