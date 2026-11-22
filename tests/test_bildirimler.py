"""Adım D: Bildirimler sekmesi (Streamlit AppTest, taklit servis), yardımcılar, ölçüm kartları ve dış katman şeması."""
import json

import pytest
from streamlit.testing.v1 import AppTest

from arayuz import bildirimler as BL
from arayuz import bilesenler, model, olcum

ONAY = {"zaman": "2026-11-22T20:51:53", "kanal": "onay-kuyrugu", "baslik": "Onay gerekli: Marmara Perakende A.Ş. / P2 / IHLAL",
        "mesaj": "Müşteri: Marmara Perakende A.Ş. (kurumsal); öncelik: P2; risk: IHLAL.", "oncelik": "yuksek", "talep_id": "t-abc123"}
ENGEL = {"zaman": "2026-11-22T20:49:59", "kanal": "guvenlik-insan-inceleme", "baslik": "Komut içerikli talep işlenmedi",
         "mesaj": "Komut içerikli talep işlenmedi (destek talebi DS-0001)", "oncelik": "orta", "talep_id": "DS-0001"}
ISLER = ["hizmet kredisi %2 (1800 TL) kaydedildi", "üst seviyeye çıkarma (eskalasyon) kaydedildi"]


def _uygulama():
    from arayuz import bilesenler as b
    from arayuz import stil
    stil.uygula()
    b.bildirimler_sekmesi()


class SahteServis:
    """BL._istek yerine geçer: GET /bekleyen, GET /durum/{id}, POST /onay/{id}."""

    def __init__(self, durum="ONAY_BEKLIYOR", kapali=False):
        self.durum, self.kapali, self.cagrilar = durum, kapali, []

    def __call__(self, yontem, yol, govde=None, zaman_asimi=5.0):
        self.cagrilar.append((yontem, yol, govde))
        if self.kapali:
            raise BL.ServisKapali("http://127.0.0.1:8000")
        if yol == "/bekleyen":
            return {"servis": "calisiyor"}
        if yontem == "GET" and yol.startswith("/durum/"):
            d = {"talep_id": yol.rsplit("/", 1)[-1], "durum": self.durum}
            if self.durum == "TAMAMLANDI":
                d["onay_sonucu"] = {"karar": "ONAYLA", "gerekce": None, "uygulanan_islemler": ISLER, "uygulandi": True}
            return d
        if yontem == "POST" and yol.startswith("/onay/"):
            if self.durum != "ONAY_BEKLIYOR":
                raise BL.ServisHatasi(409, "Talep onay beklemiyor")
            ok = govde["karar"] == "onayla"
            self.durum = "TAMAMLANDI"
            return {"talep_id": yol.rsplit("/", 1)[-1], "durum": "TAMAMLANDI",
                    "onay_sonucu": {"karar": govde["karar"].upper(), "gerekce": govde["gerekce"] or None,
                                    "uygulanan_islemler": ISLER if ok else [], "uygulandi": ok}}
        raise AssertionError((yontem, yol))


@pytest.fixture()
def ortam(tmp_path, monkeypatch):
    dosya = tmp_path / "bildirimler.jsonl"
    monkeypatch.setenv("SLA_BILDIRIM_DOSYASI", str(dosya))

    def yaz(*kayitlar):
        dosya.write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar), encoding="utf-8")

    def kur(servis):
        monkeypatch.setattr(BL, "_istek", servis)
        return servis
    return type("O", (), {"yaz": staticmethod(yaz), "kur": staticmethod(kur)})


def calistir():
    at = AppTest.from_function(_uygulama, default_timeout=20)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def etiketler(at):
    return [b.label for b in at.button]


def metin(at):
    return " ".join(m.value for m in at.markdown)


def test_bildirim_yok(ortam):
    at = calistir()
    assert any("Henüz bildirim yok" in i.value for i in at.info)
    assert "Yenile" in etiketler(at)


def test_bildirimler_kart_ve_siralama(ortam):
    ortam.yaz(ENGEL, ONAY)                       # dosyada eskiden yeniye; panel yeniden eskiye göstermeli
    ortam.kur(SahteServis())
    m = metin(calistir())
    assert m.index("Onay gerekli: Marmara") < m.index("Komut içerikli talep işlenmedi")
    assert "Onay kuyruğu" in m and "Güvenlik / insan inceleme" in m and "Öncelik: Yüksek" in m and "talep_id: t-abc123" in m
    assert "22.11.2026 20:51:53" in m


def test_onay_butonlari_yalniz_onay_kartinda(ortam):
    ortam.yaz(ENGEL)
    ortam.kur(SahteServis())
    assert {"Onayla", "Reddet"}.isdisjoint(etiketler(calistir()))
    ortam.yaz(ENGEL, ONAY)
    at = calistir()
    assert {"Onayla", "Reddet"} <= set(etiketler(at)) and not any(b.disabled for b in at.button if b.label in ("Onayla", "Reddet"))
    assert any("Karar yalnızca yöneticidedir; n8n onay vermez." in c.value for c in at.caption)


def test_onayla_servise_gider_ve_karar_karti(ortam):
    ortam.yaz(ONAY)
    s = ortam.kur(SahteServis())
    at = calistir()
    [b for b in at.button if b.label == "Onayla"][0].click()
    at.run()
    assert not at.exception
    yontemler = [(c[0], c[1]) for c in s.cagrilar]
    assert yontemler.index(("GET", "/durum/t-abc123")) < yontemler.index(("POST", "/onay/t-abc123"))      # önce durum doğrulanır
    assert [c for c in s.cagrilar if c[0] == "POST"][0][2] == {"karar": "onayla", "gerekce": ""}
    m = metin(at)
    assert "Karar: Onaylandı" in m and ISLER[0] in m and ISLER[1] in m
    assert not {"Onayla", "Reddet"} & set(etiketler(at))                      # karara bağlandı: düğmeler yok


def test_reddet_bos_gerekce_gonderilmez(ortam):
    ortam.yaz(ONAY)
    s = ortam.kur(SahteServis())
    at = calistir()
    [b for b in at.button if b.label == "Reddet"][0].click()
    at.run()
    assert any("gerekçe zorunludur" in e.value for e in at.error)
    assert not [c for c in s.cagrilar if c[0] == "POST"]                       # hiçbir şey gönderilmedi
    assert s.durum == "ONAY_BEKLIYOR"


def test_reddet_gerekceli(ortam):
    ortam.yaz(ONAY)
    s = ortam.kur(SahteServis())
    at = calistir()
    at.text_input[0].set_value("Kredi çelişkili").run()
    [b for b in at.button if b.label == "Reddet"][0].click()
    at.run()
    post = [c for c in s.cagrilar if c[0] == "POST"][0]
    assert post[2] == {"karar": "reddet", "gerekce": "Kredi çelişkili"}
    m = metin(at)
    assert "Karar: Reddedildi" in m and "Kredi çelişkili" in m and "Ajan hiçbir işlem uygulamadı" in m


def test_servis_kapali_mesaj_ve_pasif_dugmeler(ortam):
    ortam.yaz(ONAY)
    ortam.kur(SahteServis(kapali=True))
    at = calistir()                               # çökmez
    assert any("Onay için ajan servisi gerekir." in c.value for c in at.caption)
    assert not list(at.warning)                   # sarı uyarı yok: sakin gri not
    assert not [b for b in at.button if b.label in ("Onayla", "Reddet")]          # pasif düğme de yok
    assert not [t for t in at.text_input if "Gerekçe" in t.label]                  # gerekçe kutusu da yok


def test_servis_kapaliyken_tiklama_cokmez(ortam, monkeypatch):
    ortam.yaz(ONAY)
    s = ortam.kur(SahteServis())
    at = calistir()
    s.kapali = True                               # servis sayfa açıldıktan sonra kapandı
    [b for b in at.button if b.label == "Onayla"][0].click()
    at.run()
    assert not at.exception and any("ajan servisi gerekir" in c.value for c in at.caption)
    assert not [b for b in at.button if b.label in ("Onayla", "Reddet")]


def test_zaten_karara_baglanmis_pasif_ve_durum(ortam):
    ortam.yaz(ONAY)
    ortam.kur(SahteServis(durum="TAMAMLANDI"))
    at = calistir()
    m = metin(at)
    assert "Karar: Onaylandı" in m and ISLER[0] in m
    assert not {"Onayla", "Reddet"} & set(etiketler(at))


def test_onay_beklemeyen_durum_pasif(ortam):
    ortam.yaz(ONAY)
    ortam.kur(SahteServis(durum="ISLENIYOR"))
    at = calistir()
    assert any("onay beklemiyor" in i.value and "ISLENIYOR" in i.value for i in at.info)
    assert all(b.disabled for b in at.button if b.label in ("Onayla", "Reddet"))


def test_yenile_yeni_bildirimi_gosterir(ortam):
    ortam.yaz(ENGEL)
    ortam.kur(SahteServis())
    at = calistir()
    assert "Onay gerekli" not in metin(at)
    ortam.yaz(ENGEL, ONAY)
    [b for b in at.button if b.label == "Yenile"][0].click()
    at.run()
    assert "Onay gerekli: Marmara" in metin(at)


# ------------------------------------------------------------------ yardımcılar
def test_oku_siralar_ve_bozuk_satiri_atlar(tmp_path):
    d = tmp_path / "b.jsonl"
    d.write_text(json.dumps(ENGEL) + "\nbozuk{\n\n[1]\n" + json.dumps(ONAY) + "\n", encoding="utf-8")
    assert [b["talep_id"] for b in BL.oku(d)] == ["t-abc123", "DS-0001"]
    assert BL.oku(tmp_path / "yok.jsonl") == []


def test_onay_karti_mi():
    assert BL.onay_karti_mi(ONAY) and not BL.onay_karti_mi(ENGEL)
    assert not BL.onay_karti_mi({**ONAY, "talep_id": "DS-0002"}) and not BL.onay_karti_mi({**ONAY, "talep_id": None})


def test_onay_gonder_once_durum_sonra_onay(monkeypatch):
    s = SahteServis()
    monkeypatch.setattr(BL, "_istek", s)
    BL.onay_gonder("t-1", "Onayla")
    assert [(c[0], c[1]) for c in s.cagrilar] == [("GET", "/durum/t-1"), ("POST", "/onay/t-1")]
    with pytest.raises(BL.ServisHatasi) as e:                                  # artık karara bağlandı
        BL.onay_gonder("t-1", "onayla")
    assert e.value.kod == 409 and [c for c in s.cagrilar if c[0] == "POST"] == [("POST", "/onay/t-1", {"karar": "onayla", "gerekce": ""})]
    with pytest.raises(ValueError):
        BL.onay_gonder("t-2", "reddet", "   ")
    with pytest.raises(ValueError):
        BL.onay_gonder("t-2", "belki")


def test_hata_metinleri():
    assert "Ajan servisi çalışmıyor" in BL.hata_metni(BL.ServisKapali("http://x"))
    assert "409" in BL.hata_metni(BL.ServisHatasi(409, "onay beklemiyor")) and "404" in BL.hata_metni(BL.ServisHatasi(404, ""))


def test_servis_adresi_ortamdan(monkeypatch):
    assert BL.servis_adresi() == "http://127.0.0.1:8000"
    monkeypatch.setenv("SLA_SERVIS_URL", "http://servis:9000/")
    assert BL.servis_adresi() == "http://servis:9000"


def test_gercek_jsonl_alanlari_kanal_adlariyla_uyumlu():
    """dis_sistem/bildirimler.jsonl gerçek kayıtları (varsa) bilinen alanları ve kanalları taşır."""
    for b in BL.oku(BL.KOK / "dis_sistem" / "bildirimler.jsonl"):
        assert {"zaman", "kanal", "baslik", "mesaj", "oncelik", "talep_id"} <= set(b)
        assert b["kanal"] in BL.KANALLAR
        assert b["oncelik"] in BL.ONCELIK


# ------------------------------------------------------------------ ölçüm, mimari, sınırlamalar
def test_kaynak_bulma_rapordan_okunur():
    satirlar = olcum.kaynak_bulma(olcum.rapor_oku(olcum.SONRA_RAPOR))
    assert len(satirlar) == 4
    ana02 = next(r for r in satirlar if r["kume"].startswith("Ana") and r["grup"].startswith("02"))
    ham = olcum.rapor_oku(olcum.SONRA_RAPOR)
    assert f"| {olcum.kn(*ana02['ilk']['tumu'])} / {olcum.kn(*ana02['ilk']['en_az_biri'])} / {olcum.kn(*ana02['ilk']['madde'])} " in ham
    assert ana02["ilk"]["tumu"][1] == ana02["talep"] == ana02["sonra"]["tumu"][1]
    assert olcum.kaynak_bulma(None) == [] and olcum.kaynak_bulma("## 8. Doğru kaynak maddeyi bulma\n\nyok") == []


def test_hata_adlari_okunur():
    assert olcum.hata_adi("1c") == "1c Talep türü" and olcum.hata_adi("4 öncelik önerisi") == "Öncelik önerisi"
    assert olcum.hata_adi("bilinmeyen") == "bilinmeyen"


def test_dis_katman_semasi_her_bilesen_bir_kez():
    dot = bilesenler.dis_katman_dot()
    for _k, etiket, _t, _r in bilesenler.DIS_BILESENLER:
        assert dot.count(f'label="{etiket}"') == 1, etiket                       # her bileşen yalnız bir kez
    for ad in ("Destek sistemi", "n8n", "Ajan servisi (FastAPI)", "Ajan (LangGraph)", "Streamlit arayüzü", "MCP sunucusu",
               "Hesap araçları", "Bildirim (simülatör)", "İnsan onayı"):
        assert ad in dot, ad
    assert dot.count("LangGraph") == 1 and dot.count('label="n8n"') == 1
    assert dot.count("dashed") >= 2 and "n8n onay vermez" in dot                  # sentetikler kesikli, onay notu
    assert dot.count("->") == len(bilesenler.DIS_BAGLANTILAR) == 9
    ids = [k for k, *_ in bilesenler.DIS_BILESENLER]
    assert len(ids) == len(set(ids))


def test_dis_katman_sekmede_graphviz_ve_ayrinti(ortam):
    def uyg():
        from arayuz import bilesenler as b
        b.mimari_sekmesi()
    at = AppTest.from_function(uyg, default_timeout=30)
    at.run()
    assert not at.exception and len(at.get("graphviz_chart")) == 1
    assert any(e.label.startswith("Ayrıntı") for e in at.expander)


def test_sinirlamalar_guncel():
    assert len(bilesenler.SINIRLAMALAR) == 6
    m = " ".join(bilesenler.SINIRLAMALAR)
    assert "simülasyondur" in m and "tek model üzerinde sırayla" in m and "yön göstericidir" in m and "bilmiyorum" in m
    assert "gelecek çalışma" not in m
    assert "diğer dallar yapısal testlerle doğrulandı, canlı çalıştırılmadı" in " ".join(bilesenler.SINIRLAMA_AYRINTI)
    assert "ONAY_BEKLIYOR" in " ".join(bilesenler.SINIRLAMA_AYRINTI)
    # 0/7 ve 6/7 değerleri rapor dosyasından doğrulanır (zor set, 02 maddeleri)
    z = [x for x in olcum.kaynak_bulma(olcum.rapor_oku(olcum.SONRA_RAPOR)) if x["kume"].startswith("Zor") and x["grup"].startswith("02")][0]
    assert olcum.kn(*z["sonra"]["tumu"]) == "0/7" and olcum.kn(*z["sonra"]["en_az_biri"]) == "6/7"
    assert "0/7" in m and "6/7" in m


def test_css_ust_serit_cilasi():
    from arayuz import stil
    assert 'header[data-testid="stHeader"]' in stil.CSS and "box-shadow: none" in stil.CSS and "padding-top: 3.2rem" in stil.CSS


def test_tam_sayfa_acilir_bes_sekme_ve_talep_ise_bozulmadi(monkeypatch, tmp_path):
    monkeypatch.setattr(model, "isit", lambda: {"durum": "hazir", "sure_sn": 0.1, "ayrinti": "test"})
    monkeypatch.setenv("SLA_BILDIRIM_DOSYASI", str(tmp_path / "yok.jsonl"))
    at = AppTest.from_file(str(olcum.KOK / "arayuz" / "uygulama.py"), default_timeout=30)
    at.run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Talep İşle", "Ölçüm Sonuçları", "Mimari ve Sınırlamalar", "Bildirimler", "Kayıtlı Çalıştırmalar"]
    o = at.selectbox(key="ornek_ad")
    assert o.options[1] == "Demo 1: Komutlu talep" and o.options[2] == "Demo 2: İhlalli P2 talep"
    o.select(o.options[2]).run()
    assert "iki gündür" in at.text_area(key="talep_metni").value
    assert any(b.label == "İşle" for b in at.button)


def test_dugme_etiketleri_tam_ve_yakin_css():
    from arayuz import stil
    assert 'st-key-dugme_' in stil.CSS and "white-space: nowrap" in stil.CSS and "min-width: 6.5rem" in stil.CSS
    assert "flex: 0 0 auto" in stil.CSS                                           # sütunlar içerik kadar: düğmeler yan yana, yakın


def test_etiketler_tam_onay_ve_bildirim(ortam):
    ortam.yaz(ONAY)
    ortam.kur(SahteServis())
    at = calistir()
    assert [b.label for b in at.button if b.label in ("Onayla", "Reddet")] == ["Onayla", "Reddet"]


def test_yan_cubuk_ve_sinirlama_sure_ifadesi():
    import inspect
    assert "~10 sn–2 dk" in inspect.getsource(bilesenler.yan_cubuk) and "15–100" not in inspect.getsource(bilesenler)
    assert any("10 sn–2 dk" in x for x in bilesenler.SINIRLAMALAR)


def test_karar_sirasi_3_ajan_davranisiyla_uyumlu():
    import inspect
    k = inspect.getsource(bilesenler.mimari_sekmesi)
    assert "belirsizse önce müşteriye sorulur, yine belirsizse yöneticiye iletilir" in k
