"""Ajan servisi: FastAPI TestClient + taklit ajan (Ollama gerekmez)."""
import threading
import time

import pytest
from fastapi.testclient import TestClient

import servis


def _cikti(davranis="HESAPLA", durum="TAMAMLANDI", **ek):
    d = {"davranis": davranis, "neden": None, "musteri": None, "paket": None, "oncelik": None, "son_tarih": None, "risk": None,
         "kalan_dk": None, "kredi": None, "onay_gerekli": False, "onay_nedenleri": [], "kaynaklar": [], "durum": durum, "mesaj": "m"}
    d.update(ek)
    return d


ENGELLE = _cikti("ENGELLE", neden="talimat_iceriyor", mesaj="engellendi")
ONAYLI = _cikti("HESAPLA", durum="BEKLEMEDE", musteri="Marmara Perakende A.Ş.", paket="kurumsal", oncelik="P2",
                son_tarih="2026-11-19T12:00:00", risk="IHLAL", kalan_dk=0,
                kredi={"yuzde": 2.0, "tutar": 1800.0, "neden": "tam_oran"}, onay_gerekli=True,
                onay_nedenleri=["ihlal", "kredi_onerisi"], kaynaklar=[{"dokuman": "02_oncelik_rehberi", "madde": "4.1"}])
NORMAL = _cikti("HESAPLA", musteri="Ege", paket="gelismis", oncelik="P3", son_tarih="2026-11-19T12:00:00", risk="NORMAL",
                kalan_dk=60, kredi={"yuzde": 0, "tutar": 0, "neden": "ihlal_yok"},
                kaynaklar=[{"dokuman": "02_oncelik_rehberi", "madde": "5.1"}])
ADIM = [{"adim": "1a_musteri_arama", "tur": "kod", "sure_sn": 0.001, "degisen": []}]


class SahteAjan:
    """talep_isle: metne göre sonuç; 'YAVAS' içeren talep serbest bırakılana kadar bekler."""

    def __init__(self):
        self.cagrilar, self.onaylar, self.biten = [], [], []
        self.serbest = threading.Event()
        self.basladi = threading.Event()

    def hazirla(self):
        return self

    def graf(self):
        raise RuntimeError("graf yok")           # canlı adım okuma hatası servisi bozmamalı

    def talep_isle(self, metin, kayit, simdi, thread_id, soru_soruldu=False):
        self.cagrilar.append((metin, kayit, simdi, thread_id, soru_soruldu))
        if "YAVAS" in metin:
            self.basladi.set()
            self.serbest.wait(10)
        if "HATA" in metin:
            raise RuntimeError("model kapalı")
        self.biten.append(metin)
        s = {"thread_id": thread_id, "durum": "TAMAMLANDI", "cikti": NORMAL, "onay_sonucu": None, "bekleyen_onay": None,
             "adim_sureleri": ADIM, "hata": None}
        if "komut" in metin:
            s["cikti"] = ENGELLE
        elif "onay" in metin:
            s.update(durum="BEKLEMEDE", cikti=ONAYLI, bekleyen_onay={"paket": ONAYLI})
        return s

    def onay_ver(self, thread_id, karar, gerekce=None, karar_zamani=None):
        self.onaylar.append((thread_id, karar, gerekce))
        return {"thread_id": thread_id, "durum": "TAMAMLANDI", "cikti": ONAYLI,
                "onay_sonucu": {"karar": karar, "gerekce": gerekce,
                                "uygulanan_islemler": ["kredi kaydı"] if karar == "ONAYLA" else [], "uygulandi": karar == "ONAYLA"},
                "bekleyen_onay": None, "adim_sureleri": ADIM, "hata": None}


@pytest.fixture()
def istemci(monkeypatch):
    sahte = SahteAjan()
    monkeypatch.setattr(servis, "AJAN", sahte)
    monkeypatch.setattr(servis, "_isler", {})
    monkeypatch.setattr(servis, "_hazir", False)
    with TestClient(servis.app) as c:
        c.sahte = sahte
        yield c
    sahte.serbest.set()


def bekle(c, tid, hedef, sure=5):
    t0, r = time.time(), None
    while time.time() - t0 < sure:
        r = c.get(f"/durum/{tid}").json()
        if r["durum"] in hedef:
            return r
        time.sleep(0.02)
    raise AssertionError(f"{tid} {hedef} durumuna gelmedi: {r}")


def test_talep_202_ve_tamamlanir(istemci):
    r = istemci.post("/talep", json={"talep_metni": "Demo komut talebi"})
    assert r.status_code == 202
    g = r.json()
    assert g["durum"] == "ISLENIYOR" and g["talep_id"].startswith("t-")
    d = bekle(istemci, g["talep_id"], {"TAMAMLANDI"})
    assert d["cikti"]["davranis"] == "ENGELLE" and d["sure_sn"] is not None and d["adim_sureleri"][0]["adim"] == "1a_musteri_arama"


def test_durum_isleniyor_sonra_tamamlandi(istemci):
    tid = istemci.post("/talep", json={"talep_metni": "YAVAS komut"}).json()["talep_id"]
    assert istemci.sahte.basladi.wait(5)
    d = istemci.get(f"/durum/{tid}").json()
    assert d["durum"] == "ISLENIYOR" and d["sirada"] is False and d["cikti"] is None
    istemci.sahte.serbest.set()
    assert bekle(istemci, tid, {"TAMAMLANDI"})["cikti"]["davranis"] == "ENGELLE"


def test_varsayilan_zamanlar_ve_verilenler(istemci):
    t1 = istemci.post("/talep", json={"talep_metni": "komut a"}).json()["talep_id"]
    bekle(istemci, t1, {"TAMAMLANDI"})
    metin, kayit, simdi, tid, soru = istemci.sahte.cagrilar[0]
    assert kayit == simdi and tid == t1 and soru is False                # kayıt zamanı yoksa şimdi
    t2 = istemci.post("/talep", json={"talep_metni": "komut b", "kayit_zamani": "2026-11-19T10:00:00",
                                      "simdi": "2026-11-19T11:00:00", "soru_soruldu": True}).json()["talep_id"]
    bekle(istemci, t2, {"TAMAMLANDI"})
    metin, kayit, simdi, tid, soru = istemci.sahte.cagrilar[1]
    assert kayit.isoformat() == "2026-11-19T10:00:00" and simdi.isoformat() == "2026-11-19T11:00:00" and soru is True


def test_onay_bekleyen_akis(istemci):
    tid = istemci.post("/talep", json={"talep_metni": "ihlalli onay talebi"}).json()["talep_id"]
    d = bekle(istemci, tid, {"ONAY_BEKLIYOR"})
    assert d["cikti"]["durum"] == "BEKLEMEDE" and d["cikti"]["onay_gerekli"] is True
    b = istemci.get("/bekleyen").json()
    assert b["adet"] == 1 and b["talepler"][0]["talep_id"] == tid and b["talepler"][0]["oncelik"] == "P2"
    r = istemci.post(f"/onay/{tid}", json={"karar": "Onayla"})
    assert r.status_code == 200 and r.json()["durum"] == "TAMAMLANDI"
    assert r.json()["onay_sonucu"]["karar"] == "ONAYLA" and r.json()["onay_sonucu"]["uygulanan_islemler"] == ["kredi kaydı"]
    assert istemci.get(f"/durum/{tid}").json()["durum"] == "TAMAMLANDI"
    assert istemci.get("/bekleyen").json()["adet"] == 0
    assert istemci.sahte.onaylar == [(tid, "ONAYLA", None)]


def test_reddet_gerekce_zorunlu_422(istemci):
    tid = istemci.post("/talep", json={"talep_metni": "ihlalli onay talebi"}).json()["talep_id"]
    bekle(istemci, tid, {"ONAY_BEKLIYOR"})
    for g in ({"karar": "reddet"}, {"karar": "reddet", "gerekce": "   "}):
        r = istemci.post(f"/onay/{tid}", json=g)
        assert r.status_code == 422 and "gerekce" in r.text
    assert istemci.sahte.onaylar == [] and istemci.get(f"/durum/{tid}").json()["durum"] == "ONAY_BEKLIYOR"
    r = istemci.post(f"/onay/{tid}", json={"karar": "reddet", "gerekce": "kredi çelişkili"})
    assert r.status_code == 200 and r.json()["onay_sonucu"]["karar"] == "REDDET" and r.json()["onay_sonucu"]["uygulandi"] is False


def test_yanlis_durumda_onay_409(istemci):
    tid = istemci.post("/talep", json={"talep_metni": "komut talebi"}).json()["talep_id"]
    bekle(istemci, tid, {"TAMAMLANDI"})
    r = istemci.post(f"/onay/{tid}", json={"karar": "onayla"})
    assert r.status_code == 409 and "onay beklemiyor" in r.json()["detail"]
    t2 = istemci.post("/talep", json={"talep_metni": "ihlalli onay talebi"}).json()["talep_id"]
    bekle(istemci, t2, {"ONAY_BEKLIYOR"})
    assert istemci.post(f"/onay/{t2}", json={"karar": "onayla"}).status_code == 200
    assert istemci.post(f"/onay/{t2}", json={"karar": "onayla"}).status_code == 409      # ikinci onay


def test_islenirken_onay_409(istemci):
    tid = istemci.post("/talep", json={"talep_metni": "YAVAS onay"}).json()["talep_id"]
    assert istemci.sahte.basladi.wait(5)
    assert istemci.post(f"/onay/{tid}", json={"karar": "onayla"}).status_code == 409
    istemci.sahte.serbest.set()


def test_bilinmeyen_talep_id_404(istemci):
    assert istemci.get("/durum/t-yok").status_code == 404
    assert istemci.post("/onay/t-yok", json={"karar": "onayla"}).status_code == 404


def test_hatali_govde_422(istemci):
    for g in ({}, {"talep_metni": ""}, {"talep_metni": "   "}, {"talep_metni": "x", "kayit_zamani": "dün"},
              {"talep_metni": "x", "simdi": "2026-11-19T10:00:00+03:00"}, {"talep_metni": "x", "fazla": 1}, {"talep_metni": 5}):
        r = istemci.post("/talep", json=g)
        assert r.status_code == 422, g
    assert istemci.post("/onay/t-x", json={"karar": "belki"}).status_code == 422
    assert istemci.sahte.cagrilar == []


def test_ajan_hatasi_islenemedi_servis_ayakta(istemci):
    tid = istemci.post("/talep", json={"talep_metni": "HATA talebi"}).json()["talep_id"]
    d = bekle(istemci, tid, {"ISLENEMEDI"})
    assert d["cikti"] is None and "model kapalı" in d["hata"]["mesaj"]
    t2 = istemci.post("/talep", json={"talep_metni": "komut sonrası"}).json()["talep_id"]      # işçi hâlâ çalışıyor
    assert bekle(istemci, t2, {"TAMAMLANDI"})["cikti"]["davranis"] == "ENGELLE"


def test_ikinci_talep_siralanir(istemci):
    t1 = istemci.post("/talep", json={"talep_metni": "YAVAS komut birinci"}).json()["talep_id"]
    assert istemci.sahte.basladi.wait(5)
    t2 = istemci.post("/talep", json={"talep_metni": "komut ikinci"}).json()["talep_id"]
    time.sleep(0.3)
    d2 = istemci.get(f"/durum/{t2}").json()
    assert d2["durum"] == "ISLENIYOR" and d2["sirada"] is True                   # ilk bitmeden başlamadı
    assert [c[0] for c in istemci.sahte.cagrilar] == ["YAVAS komut birinci"]
    istemci.sahte.serbest.set()
    bekle(istemci, t1, {"TAMAMLANDI"})
    bekle(istemci, t2, {"TAMAMLANDI"})
    assert istemci.sahte.biten == ["YAVAS komut birinci", "komut ikinci"]          # sırayla


def test_saglik_ollama_kapali(istemci, monkeypatch):
    import ollama

    def patla(**k):
        raise ConnectionError("kapalı")
    monkeypatch.setattr(ollama, "Client", patla)
    r = istemci.get("/saglik").json()
    assert r["servis"] == "calisiyor" and r["ollama"] == "kapali" and r["checkpoint_dosyasi"] == "servis_checkpoints.sqlite"


def test_ayri_checkpoint_dosyasi():
    assert servis.CHECKPOINT.name == "servis_checkpoints.sqlite" and servis.CHECKPOINT != servis.config.CHECKPOINT_DB


def test_graf_hazirlanmadan_ajan_graf_cagrilmaz(monkeypatch):
    """Yarış koşulu: ilk talep sırasında /durum, servis checkpoint'i kurulmadan ajan.graf() çağırmamalı."""
    olaylar = []

    class A(SahteAjan):
        def hazirla(self):
            olaylar.append("hazirla")
            return self

        def graf(self):
            olaylar.append("graf")
            raise RuntimeError("x")
    monkeypatch.setattr(servis, "AJAN", A())
    monkeypatch.setattr(servis, "_isler", {"t-1": {"durum": "ISLENIYOR", "sirada": False, "sonuc": None}})
    monkeypatch.setattr(servis, "_hazir", False)
    assert servis._canli_adimlar("t-1") == []
    assert olaylar[0] == "hazirla"
