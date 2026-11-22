"""Arayüz yardımcıları (arayuz/bicimle.py, olcum.py, model.py) — Streamlit gerektirmez."""
import json
from datetime import datetime
from types import SimpleNamespace

import config
from arayuz import bicimle as B
from arayuz import model, olcum


def test_sure_ve_kalan_sure():
    assert B.sure_yaz(None) == "—" and B.sure_yaz(0.0002) == "<0,1 sn" and B.sure_yaz(12.34) == "12,3 sn"
    assert B.kalan_sure_yaz(None) == "—" and B.kalan_sure_yaz(45) == "45 dk"
    assert B.kalan_sure_yaz(120) == "2 sa" and B.kalan_sure_yaz(135) == "2 sa 15 dk" and B.kalan_sure_yaz(0) == "0 dk"
    assert B.tarih_yaz("2026-11-23T11:00:00") == "23.11.2026 11:00" and B.tarih_yaz(None) == "—"


def test_adim_satirlari_tur_etiketi():
    kayit = [{"adim": "1a_musteri_arama", "tur": "kod", "sure_sn": 0.001}, {"adim": "1b_talimat", "tur": "llm", "sure_sn": 10.0}]
    s = B.adim_satirlari(kayit, ["talep_turu"])
    assert [x["tur"] for x in s] == ["kod", "model", "model"]
    assert [x["durum"] for x in s] == ["bitti", "bitti", "çalışıyor"]
    assert "1c Talep türü" in B.adim_metni(s) and B.adim_metni([]) == "⏳ Başlıyor…"


def _cikti(davranis, **ek):
    return {"davranis": davranis, "mesaj": "m", "neden": None, "musteri": None, **ek}


def test_durum_karti():
    assert B.durum_karti(_cikti("HESAPLA")) is None
    k = B.durum_karti(_cikti("BILMIYORUM", neden="dokumanda_yok"))
    assert k[0] == "bilgi" and "Dokümanda bilgi bulunmamaktadır." in k[1]
    k = B.durum_karti(_cikti("ENGELLE", neden="talimat_iceriyor", mesaj="insan incelemesine iletildi"))
    assert k[0] == "bilgi" and k[1].startswith("**Bu talep işlenmedi:**")
    assert B.durum_karti(_cikti("SORU_SOR", mesaj="Firma adınız?"))[0] == "bilgi"
    assert B.durum_karti(_cikti("ONCELIK_BELIRLENEMEDI"))[1].startswith("**Bu talep işlenmedi:**")
    assert B.durum_karti(None, {"adim": "1b", "mesaj": "x"})[0] == "hata"
    assert B.durum_karti({"davranis": None, "mesaj": "Talep işlenemedi", "neden": "sema_hatasi"})[0] == "hata"


def test_hata_mesajlari():
    assert "Ollama" in B.hata_mesaji({"mesaj": "ConnectError: connection refused"})
    m = B.hata_mesaji({"adim": "1b", "mesaj": "LLM çıktısı şemaya uymadı (tek yeniden deneme sonrası)"})
    assert "ayırt etmiyor" in m
    assert "başlatıp" in B.hata_mesaji({"mesaj": "LLM çıktısı şemaya uymadı"}, None, True)
    assert "ISLENEMEDI" in B.hata_mesaji({"mesaj": "KeyError: x"}) and "ISLENEMEDI" in B.hata_mesaji(None)


def test_kaynak_listesi_metni_dokumandan_gelir():
    r = B.kaynak_listesi([{"dokuman": "02_oncelik_rehberi", "madde": "4.1"}, {"dokuman": "01_sla_sozlesmesi", "madde": "3.1"}])
    assert r[0]["dokuman"].startswith("Doküman 02") and r[0]["madde"] == "4.1" and r[0]["satirlar"]
    assert B.kaynak_listesi([]) == []


def test_onay_sonucu_okuma():
    assert B.uygulanan_islemler(None) == [] and B.onay_sonucu_ozet(None) is None
    o = {"karar": "ONAYLA", "gerekce": None, "uygulanan_islemler": ["a", "b"], "uygulandi": True}
    assert B.uygulanan_islemler(o) == ["a", "b"] and B.onay_sonucu_ozet(o) == "Onaylandı"
    r = {"karar": "REDDET", "gerekce": "çelişki", "uygulanan_islemler": [], "uygulandi": False}
    assert B.uygulanan_islemler(r) == [] and "çelişki" in B.onay_sonucu_ozet(r)
    assert B.onay_nedenleri_yaz(["ihlal", "kredi_onerisi"]) == "SLA ihlali, Hizmet kredisi önerisi"


def test_thread_id_benzersiz():
    t = datetime(2026, 11, 22, 10, 0, 0)
    assert B.yeni_thread_id(1, t) != B.yeni_thread_id(2, t) and B.yeni_thread_id(1, t).startswith("arayuz-20261122")


def test_ornekler_ozgun_ve_tutarli():
    simdi = datetime(2026, 11, 23, 10, 0)
    o = B.ornekler(simdi)
    assert len(o) == 8 and all(v["kayit_zamani"] < simdi for v in o.values())
    test = json.loads((config.DATA_DIR / "test_seti.json").read_text(encoding="utf-8"))["talepler"]
    metinler = {t["metin"] if "metin" in t else t.get("talep_metni", "") for t in test}
    assert not any(v["metin"] in metinler for v in o.values())
    musteriler = json.loads((config.DATA_DIR / "musteriler.json").read_text(encoding="utf-8"))["musteriler"]
    kayitsiz = o["Kayıtsız firma (BILMIYORUM)"]["metin"]
    assert not any(m["ad"].split()[0].lower() in kayitsiz.lower() for m in musteriler)


def test_bekleyen_onaylar_checkpointer_uzerinden():
    durumlar = {
        "t1": SimpleNamespace(next=("insan_onayi",), values={"talep_metni": "x", "cikti": {"musteri": "A"}, "adim_sureleri": []}),
        "t2": SimpleNamespace(next=(), values={"talep_metni": "y"}),
    }
    ck = [SimpleNamespace(config={"configurable": {"thread_id": t}}) for t in ("t1", "t1", "t2")]   # t1'in iki checkpoint'i

    class Graf:
        checkpointer = SimpleNamespace(list=lambda _c: iter(ck))

        def get_state(self, cfg):
            return durumlar[cfg["configurable"]["thread_id"]]

    r = B.bekleyen_onaylar(Graf())
    assert [x["thread_id"] for x in r] == ["t1"] and r[0]["paket"]["musteri"] == "A"


def test_olcum_dosyalardan_okunur_ve_rapora_uyar():
    r = olcum.karsilastir()
    ilk, sonra = r["ilk"], r["sonra"]
    assert ilk["n"] == 59 and sonra["n"] == 59
    rapor = olcum.rapor_oku(olcum.SONRA_RAPOR)
    for ad, satir in (("Ana set", "Tam doğru — Ana set (T01–T50)"), ("Zor set", "Tam doğru — Zor set (T51–T59)")):
        beklenen = f"| {satir} | {olcum.kn(*ilk['tam'][ad])} | {olcum.kn(*sonra['tam'][ad])} |"
        assert beklenen in rapor
    assert f"| Tam doğru — bağımsız 15 | {olcum.kn(*ilk['tam']['Bağımsız 15'])} | {olcum.kn(*sonra['tam']['Bağımsız 15'])} |" in rapor
    assert sorted(r["bozuldu"]) == ["T44", "T59"] and "T54" in r["hala_hatali"]
    assert olcum.NOT.startswith("Düzeltme sonrası sayılar") and "temiz sayım ilk koşudur" in olcum.NOT
    assert olcum.rapor_oku(olcum.SONUCLAR / "yok.md") is None


def test_isinma_hatada_cokmez(monkeypatch):
    import llm_adimlari

    def patla(*a, **k):
        raise ConnectionError("kapalı")
    monkeypatch.setattr(llm_adimlari, "_sohbet", patla)
    r = model.isit()
    assert r["durum"] == "hata" and "Ollama" in r["ayrinti"]
    monkeypatch.setattr(llm_adimlari, "_sohbet", lambda *a, **k: "{}")
    import ollama
    monkeypatch.setattr(ollama, "Client", lambda host=None: SimpleNamespace(embed=lambda **k: {}))
    assert model.isit()["durum"] == "hazir"
