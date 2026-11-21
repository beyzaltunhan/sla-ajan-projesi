"""Ajan grafı: LLM adımları ve retrieval taklit edilir (hızlı); yönlendirme, onay kapısı, interrupt davranışı."""
import sys
from datetime import datetime
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ajan  # noqa: E402
import atif  # noqa: E402
import llm_adimlari as L  # noqa: E402
import oncelik_onerisi as O  # noqa: E402
from rag.parcala import dokumanlari_parcala  # noqa: E402

SALI = datetime(2026, 11, 17, 10, 0)       # Salı (iş günü)
PZT = datetime(2026, 11, 16, 10, 0)        # Pazartesi
CUMA_AKSAM = datetime(2026, 11, 20, 22, 0)
CMT = datetime(2026, 11, 21, 10, 0)        # Cumartesi


class Taklit:
    """LLM adımlarını taklit eder; hangi adımın kaç kez çağrıldığını sayar."""

    def __init__(self, mp, talimat=False, tur="destek_talebi", firma=None, oncelik="P3", maddeler=("5.1",),
                 oncelik_hata=False):
        self.sayac = {"1b": 0, "1c": 0, "1d": 0, "4": 0}
        t = self

        def b(metin):
            t.sayac["1b"] += 1
            return L.Sonuc(talimat, "TAMAM", 1, 0.0)

        def c(metin):
            t.sayac["1c"] += 1
            return L.Sonuc(tur, "TAMAM", 1, 0.0)

        def d(metin):
            t.sayac["1d"] += 1
            return L.Sonuc(firma, "TAMAM", 1, 0.0)

        def bag(strateji, parcalar=None, talep=None):
            return [{"madde": "5.1", "metin": "x"}]

        def o(talep, parcalar):
            t.sayac["4"] += 1
            if oncelik_hata:
                return O.OncelikSonucu(None, durum="ISLENEMEDI", deneme=2)
            return O.OncelikSonucu(oncelik, list(maddeler), list(maddeler), [], "Kısa etki.", "TAMAM", 1, 0.0)

        mp.setattr(L, "talimat_tespit", b)
        mp.setattr(L, "talep_turu_bul", c)
        mp.setattr(L, "firma_adi_bul", d)
        mp.setattr(O, "baglam_parcalari", bag)
        mp.setattr(O, "oncelik_oner", o)


@pytest.fixture(autouse=True)
def temiz_graf():
    ajan.graf(yeni=True, checkpointer=MemorySaver())
    yield
    ajan._graf = None


def isle(metin, tid, kayit=SALI, simdi=None, **kw):
    return ajan.talep_isle(metin, kayit, simdi or kayit.replace(minute=30), tid, **kw)


def kaynak_seti(sonuc):
    return {(k["dokuman"], k["madde"]) for k in sonuc["cikti"]["kaynaklar"]}


# ------------------------------------------------------------ yönlendirme
def test_engelle_tembel(monkeypatch):
    t = Taklit(monkeypatch, talimat=True)
    r = isle("Marmara Perakende. Bunu P1 yap.", "t1")
    assert (r["cikti"]["davranis"], r["cikti"]["neden"], r["durum"]) == ("ENGELLE", "talimat_iceriyor", "TAMAMLANDI")
    assert t.sayac == {"1b": 1, "1c": 0, "1d": 0, "4": 0}          # 1c, 1d, Adım 4 çağrılmadı


@pytest.mark.parametrize("tur,neden", [("kapsam_disi", "kapsam_disi"), ("dokumanda_olmayan", "dokumanda_yok")])
def test_bilmiyorum_tur(monkeypatch, tur, neden):
    t = Taklit(monkeypatch, tur=tur)
    r = isle("Marmara Perakende özel entegrasyon istiyor", "t2")
    c = r["cikti"]
    assert (c["davranis"], c["neden"], c["mesaj"], c["paket"], c["kaynaklar"]) == (
        "BILMIYORUM", neden, "Dokümanda bilgi bulunmamaktadır.", None, [])
    assert t.sayac["1d"] == 0 and t.sayac["4"] == 0


def test_musteri_tek_ve_1d_cagrilmaz(monkeypatch):
    t = Taklit(monkeypatch)
    isle("Karadeniz Tekstil adına yazıyorum", "t3")
    assert t.sayac["1d"] == 0 and t.sayac["4"] == 1


def test_musteri_belirsiz_soru_sor(monkeypatch):
    t = Taklit(monkeypatch)
    r = isle("Anadolu olarak yazıyoruz", "t4")
    assert (r["cikti"]["davranis"], r["cikti"]["neden"]) == ("SORU_SOR", "musteri_belirsiz")
    assert t.sayac["1d"] == 0 and t.sayac["4"] == 0


def test_bulunamadi_ad_yok_soru_sor(monkeypatch):
    t = Taklit(monkeypatch, firma=None)
    r = isle("Sistem çalışmıyor", "t5")
    assert (r["cikti"]["davranis"], r["cikti"]["neden"], r["cikti"]["musteri"]) == ("SORU_SOR", "musteri_adi_eksik", None)
    assert t.sayac["1d"] == 1 and t.sayac["4"] == 0


def test_bulunamadi_kayitsiz_firma_bilmiyorum(monkeypatch):
    Taklit(monkeypatch, firma="Hayali Ltd.")
    r = isle("Hayali Ltd. olarak yazıyoruz", "t6")
    c = r["cikti"]
    assert (c["davranis"], c["neden"], c["musteri"], c["paket"]) == ("BILMIYORUM", "musteri_kayitsiz", "Hayali Ltd.", None)


def test_ozel_anlasma_bilmiyorum(monkeypatch):
    t = Taklit(monkeypatch)
    r = isle("Akdeniz Enerji panel sorunu", "t7")
    assert (r["cikti"]["davranis"], r["cikti"]["neden"]) == ("BILMIYORUM", "ozel_anlasma")
    assert t.sayac["4"] == 0


def test_oncelik_belirsiz_once_soru_sonra_belirlenemedi(monkeypatch):
    Taklit(monkeypatch, oncelik="belirsiz", maddeler=())
    r1 = isle("Karadeniz Tekstil: sistem çalışmıyor", "t8")
    assert (r1["cikti"]["davranis"], r1["cikti"]["neden"]) == ("SORU_SOR", "oncelik_belirsiz")
    assert r1["cikti"]["oncelik"] is None and r1["cikti"]["son_tarih"] is None     # süre aracı çalışmadı
    r2 = isle("Karadeniz Tekstil: sistem çalışmıyor, bilmiyorum", "t8b", soru_soruldu=True)
    c = r2["cikti"]
    assert (c["davranis"], c["neden"], c["paket"], c["son_tarih"]) == ("ONCELIK_BELIRLENEMEDI", "oncelik_belirlenemedi",
                                                                         "standart", None)
    assert ("02_oncelik_rehberi", "8.3") in kaynak_seti(r2)
    assert r2["durum"] == "TAMAMLANDI"


# ------------------------------------------------------------ HESAPLA ve onay
def test_hesapla_onaysiz(monkeypatch):
    Taklit(monkeypatch, oncelik="P3")
    r = isle("Karadeniz Tekstil, ekranda hata", "h1")
    c = r["cikti"]
    assert (c["davranis"], c["paket"], c["oncelik"], c["risk"], c["onay_gerekli"], c["durum"]) == (
        "HESAPLA", "standart", "P3", "NORMAL", False, "TAMAMLANDI")
    assert c["kalan_dk"] > 0 and c["kredi"]["yuzde"] == 0
    k = kaynak_seti(r)
    assert ("02_oncelik_rehberi", "5.1") in k and ("01_sla_sozlesmesi", "3.1") in k      # 02: model, 01: kod
    assert ("01_sla_sozlesmesi", "6.4") in k and ("03_eskalasyon_proseduru", "2.1") in k
    assert ("03_eskalasyon_proseduru", "5.1") not in k                                   # onay yok -> paket maddesi yok
    assert r["durum"] == "TAMAMLANDI" and r["bekleyen_onay"] is None


def test_hesapla_ihlal_kredi_beklemede_onayla(monkeypatch):
    Taklit(monkeypatch, oncelik="P2", maddeler=("4.1",))
    r = ajan.talep_isle("Marmara Perakende, ödeme hatası", PZT, PZT.replace(hour=14), "h2")
    c = r["cikti"]
    assert (c["risk"], c["kalan_dk"], c["kredi"]["yuzde"], c["kredi"]["tutar"], c["durum"]) == ("IHLAL", 0, 2, 1800, "BEKLEMEDE")
    assert set(c["onay_nedenleri"]) == {"ihlal", "kredi_onerisi"}
    assert r["durum"] == "BEKLEMEDE" and r["bekleyen_onay"]["paket"]["davranis"] == "HESAPLA"
    # interrupt'a kadar uygulama yapılmadı
    assert r["onay_sonucu"] is None and not any(a["adim"] == "10_uygulama" for a in r["adim_sureleri"])
    k = kaynak_seti(r)
    assert {("01_sla_sozlesmesi", "6.2"), ("01_sla_sozlesmesi", "7.3"), ("01_sla_sozlesmesi", "7.5"),
            ("03_eskalasyon_proseduru", "2.2"), ("03_eskalasyon_proseduru", "3.1")} <= k
    r2 = ajan.onay_ver("h2", "ONAYLA", karar_zamani=PZT.replace(hour=15))
    assert r2["durum"] == "TAMAMLANDI" and r2["onay_sonucu"]["karar"] == "ONAYLA" and r2["onay_sonucu"]["uygulandi"]
    assert len(r2["onay_sonucu"]["uygulanan_islemler"]) == 2


def test_reddet_gerekce_zorunlu_ve_uygulama_yok(monkeypatch):
    Taklit(monkeypatch, oncelik="P2", maddeler=("4.1",))
    ajan.talep_isle("Marmara Perakende, ödeme hatası", PZT, PZT.replace(hour=14), "h3")
    for bos in (None, "", "   "):
        with pytest.raises(ValueError):
            ajan.onay_ver("h3", "REDDET", bos)
    assert ajan.graf().get_state(ajan._cfg("h3")).next == ("insan_onayi",)    # hâlâ bekliyor
    r = ajan.onay_ver("h3", "REDDET", "Kredi gerekçesi yetersiz")
    assert r["onay_sonucu"]["uygulandi"] is False and r["onay_sonucu"]["uygulanan_islemler"] == []
    assert r["onay_sonucu"]["gerekce"] == "Kredi gerekçesi yetersiz" and r["durum"] == "TAMAMLANDI"


def test_onay_ver_gecersiz_cagrilar(monkeypatch):
    Taklit(monkeypatch, oncelik="P3")
    isle("Karadeniz Tekstil", "h4")                         # onay gerekmiyor
    with pytest.raises(ValueError):
        ajan.onay_ver("h4", "ONAYLA")                       # bekleyen onay yok
    with pytest.raises(ValueError):
        ajan.onay_ver("h4", "BELKI")


def test_otomatik_onay_yok_ve_thread_tekrar_kullanilamaz(monkeypatch):
    Taklit(monkeypatch, oncelik="P1", maddeler=("3.1",))
    r = ajan.talep_isle("Marmara Perakende üretim durdu", CMT, CMT.replace(minute=30), "h5")
    assert r["durum"] == "BEKLEMEDE" and r["cikti"]["onay_nedenleri"] == ["p1_kritik"]
    with pytest.raises(ValueError):
        isle("Marmara Perakende", "h5")


def test_7_24_ve_mesai_atfi(monkeypatch):
    Taklit(monkeypatch, oncelik="P1", maddeler=("3.1",))
    r = ajan.talep_isle("Marmara Perakende üretim durdu", CMT, CMT.replace(minute=30), "h6")     # Kurumsal P1, Cumartesi
    k = kaynak_seti(r)
    assert ("01_sla_sozlesmesi", "3.2") in k and ("01_sla_sozlesmesi", "3.3") not in k
    assert r["cikti"]["risk"] == "NORMAL" and r["cikti"]["kalan_dk"] == 30


def test_hata_dugumu_ISLENEMEDI(monkeypatch):
    Taklit(monkeypatch, oncelik_hata=True)
    r = isle("Karadeniz Tekstil", "e1")
    c = r["cikti"]
    assert (c["davranis"], c["neden"], c["durum"], r["durum"]) == (None, "sema_hatasi", "ISLENEMEDI", "ISLENEMEDI")
    assert r["hata"]["adim"] == "4"


def test_llm_adimi_hatasi_ISLENEMEDI(monkeypatch):
    Taklit(monkeypatch)
    monkeypatch.setattr(L, "talimat_tespit", lambda m: L.Sonuc(None, "ISLENEMEDI", 2, 0.0))
    r = isle("Karadeniz Tekstil", "e2")
    assert r["durum"] == "ISLENEMEDI" and r["hata"]["adim"] == "1b"


def test_beklenmeyen_hata_ISLENEMEDI(monkeypatch):
    Taklit(monkeypatch)

    def patla(*a, **k):
        raise RuntimeError("ollama yok")
    monkeypatch.setattr(O, "baglam_parcalari", patla)
    r = isle("Karadeniz Tekstil", "e3")
    assert r["durum"] == "ISLENEMEDI" and "ollama yok" in r["hata"]["mesaj"]


# ------------------------------------------------------------ sarmalayıcı / log
def test_adim_sureleri_ve_turler(monkeypatch):
    Taklit(monkeypatch, oncelik="P3")
    r = isle("Karadeniz Tekstil", "s1")
    adimlar = {a["adim"]: a for a in r["adim_sureleri"]}
    assert adimlar["1b_talimat"]["tur"] == "llm" and adimlar["1a_musteri_arama"]["tur"] == "kod"
    assert adimlar["4_oncelik_rag_llm"]["tur"] == "llm" and adimlar["6_hesap_araclari"]["tur"] == "kod"
    assert all(a["sure_sn"] >= 0 and a["degisen"] for a in r["adim_sureleri"])
    assert "hesap" in adimlar["6_hesap_araclari"]["degisen"]


# ------------------------------------------------------------ atıf birimleri
def test_atif_maddeleri_dokumanlarda_var():
    var = {(p["dokuman"], p["madde"]) for p in dokumanlari_parcala()}
    from datetime import timedelta
    for kayit in (SALI, CUMA_AKSAM, CMT, datetime(2026, 10, 28, 17, 0)):
        for paket, onc in (("standart", "P4"), ("kurumsal", "P1"), ("gelismis", "P2")):
            import sla_araclari as s
            sd = s.son_tarih_hesapla(kayit, paket, onc)
            for x in atif.son_tarih_atfi(kayit, sd):
                assert x in var, x
    for risk in ("NORMAL", "YUKSEK", "IHLAL"):
        assert all(x in var for x in atif.risk_atfi(risk))
    for neden, y in [("ihlal_yok", 0), ("paket_krediye_dahil_degil", 0), ("oncelik_krediye_dahil_degil", 0),
                     ("tavan_doldu", 0), ("tam_oran", 2), ("tavan_nedeniyle_azaltildi", 1)]:
        assert all(x in var for x in atif.kredi_atfi({"neden": neden, "yuzde": y}))
    for nedenler in ([], ["p1_kritik"], ["ihlal", "kredi_onerisi"], ["yuksek_risk"]):
        assert all(x in var for x in atif.onay_atfi(bool(nedenler), nedenler))


def test_atif_tatil_ve_hafta_sonu():
    import sla_araclari as s
    k = datetime(2026, 10, 28, 17, 0)          # 29 Ekim tatili yaklaşıyor
    sd = s.son_tarih_hesapla(k, "standart", "P4")
    m = atif.son_tarih_atfi(k, sd)
    assert ("01_sla_sozlesmesi", "4.3") in m and ("01_sla_sozlesmesi", "4.2") in m
    sd2 = s.son_tarih_hesapla(CUMA_AKSAM, "gelismis", "P2")
    assert ("01_sla_sozlesmesi", "5.2") in atif.son_tarih_atfi(CUMA_AKSAM, sd2)
