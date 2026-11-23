"""Adım 7B: görsel bileşenler, kaynak temizleme/gruplama, kayıtlı sonuçlar, demo araçları."""
import json
from datetime import datetime
from pathlib import Path

from arayuz import bicimle as B
from arayuz import olcum


def test_madde_temizle_tablo_ve_baslik():
    from rag.parcala import dokumanlari_parcala
    p = {(x["dokuman"], x["madde"]): x for x in dokumanlari_parcala()}
    for anahtar in p:
        satirlar = B.madde_temizle(p[anahtar]["metin"], p[anahtar]["baslik"])
        govde = "\n".join(satirlar)
        assert satirlar and "|---" not in govde and not govde.lstrip().startswith("Madde "), anahtar
        assert not any(x.lstrip().startswith("|") for x in satirlar), anahtar
    s = B.madde_temizle(p[("01_sla_sozlesmesi", "3.1")]["metin"], p[("01_sla_sozlesmesi", "3.1")]["baslik"])
    assert s[0].startswith("İlk yanıt süresi") and any(x.startswith("**Standart**") and "P1 Kritik 4 saat" in x for x in s)


def test_cumlede_kesme():
    uzun = "Birinci cümle burada biter. İkinci cümle de oldukça uzun devam eder ve sınırı aşar " * 3
    k = B._cumlede_kes(uzun, 120)
    assert k.endswith(".") and len(k) <= 120
    assert B._cumlede_kes("kısa metin", 120) == "kısa metin"
    assert B._cumlede_kes("a" * 50 + " " + "b" * 200, 100).endswith("…")


def test_kaynak_gruplama():
    assert B.kaynak_grubu("02_oncelik_rehberi", "4.1") == "Öncelik kuralı"
    assert B.kaynak_grubu("01_sla_sozlesmesi", "3.1") == "Süre ve mesai" and B.kaynak_grubu("01_sla_sozlesmesi", "6.2") == "Risk ve ihlal"
    assert B.kaynak_grubu("01_sla_sozlesmesi", "7.5") == "Hizmet kredisi"
    assert B.kaynak_grubu("03_eskalasyon_proseduru", "2.1") == "Onay ve eskalasyon"
    kay = [{"dokuman": "02_oncelik_rehberi", "madde": "4.1"}, {"dokuman": "01_sla_sozlesmesi", "madde": "3.1"},
           {"dokuman": "01_sla_sozlesmesi", "madde": "4.1"}, {"dokuman": "01_sla_sozlesmesi", "madde": "7.5"},
           {"dokuman": "03_eskalasyon_proseduru", "madde": "6.4"}]
    ana, diger = B.kaynaklari_grupla(B.kaynak_listesi(kay))
    assert [(k["dokuman"][:10], k["madde"]) for k in ana] == [("Doküman 02", "4.1"), ("Doküman 01", "3.1")]
    assert list(diger) == ["Süre ve mesai", "Hizmet kredisi", "Onay ve eskalasyon"]


def test_davranis_basligi_teknik_durum_degil():
    assert B.davranis_basligi({"davranis": "ENGELLE"}, "TAMAMLANDI") == "Engellendi: insan incelemesine iletildi"
    assert B.davranis_basligi({"davranis": "BILMIYORUM"}, "TAMAMLANDI") == "Dokümanda bilgi yok"
    assert "TAMAMLANDI" not in B.davranis_basligi({"davranis": "SORU_SOR"}, "TAMAMLANDI")
    assert B.davranis_basligi({"davranis": "HESAPLA"}, "BEKLEMEDE") == "Yönetici onayı bekleniyor"
    assert B.davranis_basligi(None, "ISLENEMEDI") == "Talep işlenemedi"


def test_ornek_sirasi_ve_demo_adlari():
    o = B.ornekler(datetime(2026, 11, 23, 10, 0))
    adlar = list(o)
    assert adlar[0] == "Güvenlik: komut içeren talep" and adlar[1] == "SLA ihlali: onay gerektiren talep"
    assert o[B.DEMO1]["beklenen"] == "ENGELLE" and o[B.DEMO2]["beklenen"] == "HESAPLA"
    assert all(v["beklenen"] in ("ENGELLE", "HESAPLA", "BILMIYORUM", "SORU_SOR", "ONCELIK_BELIRLENEMEDI") for v in o.values())


def test_rozetler_metin_tasir_renk_tek_basina_degil():
    from arayuz import stil
    for o, ad in (("P1", "Kritik"), ("P2", "Yüksek"), ("P3", "Normal"), ("P4", "Düşük")):
        h = stil.oncelik_rozeti(o)
        assert o in h and ad in h and f"pill-{o.lower()}" in h
    assert "İhlal" in stil.risk_rozeti("IHLAL") and "Yüksek risk" in stil.risk_rozeti("YUKSEK")
    assert "Normal" in stil.risk_rozeti("NORMAL")
    for d in ("HESAPLA", "BILMIYORUM", "ENGELLE", "SORU_SOR", "ONCELIK_BELIRLENEMEDI"):
        assert d in stil.davranis_rozeti(d)
    assert "ISLENEMEDI" in stil.davranis_rozeti(None)


def test_kart_uzun_isim_kesilmez_ve_kacis():
    from arayuz import stil
    h = stil.kart("Müşteri", stil.kac("Trakya Otomotiv Yan Sanayi A.Ş. <b>"), genis=True)
    assert "Trakya Otomotiv Yan Sanayi A.Ş." in h and "&lt;b&gt;" in h and "genis" in h
    assert "text-overflow" not in stil.CSS and "ellipsis" not in stil.CSS


def test_zaman_cizgisi():
    from arayuz import stil
    satirlar = B.adim_satirlari([{"adim": "1b_talimat", "tur": "llm", "sure_sn": 10.0},
                                 {"adim": "1a_musteri_arama", "tur": "kod", "sure_sn": 0.0}], ["talep_turu"])
    h = stil.zaman_cizgisi(satirlar)
    assert "✓" in h and "çalışıyor" in h and "Model" in h and "Kod" in h and "calisiyor" in h
    assert "Başlıyor" in stil.zaman_cizgisi([])


def test_css_gizlemeler_ve_config():
    from arayuz import stil
    assert "stAppDeployButton" in stil.CSS and "<script" not in stil.CSS.lower()
    cfg = (olcum.KOK / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'toolbarMode = "minimal"' in cfg and "gatherUsageStats = false" in cfg


def test_akis_html_model_kod_renkleri():
    from arayuz import bilesenler
    h = bilesenler.akis_html()
    assert h.count('class="dugum model"') == 4 and h.count('class="dugum kod"') == len(bilesenler.ADIMLAR) - 4
    assert "MODEL" in h and "KOD" in h


def test_md_sade_guvenli():
    from arayuz import bilesenler
    assert bilesenler.md_sade("**kalın** <script>") == "<b>kalın</b> &lt;script&gt;"


def test_kayitli_yukleme(tmp_path):
    from arayuz import kayitli
    assert kayitli.yukle(tmp_path / "yok.json") == []
    d = tmp_path / "k.json"
    d.write_text(json.dumps({"kayitlar": [{"ad": "a", "metin": "m", "kayit_tarihi": "22.11.2026 10:00",
                                           "sonuc": {"durum": "TAMAMLANDI"}}]}), encoding="utf-8")
    assert kayitli.yukle(d)[0]["ad"] == "a"


def test_kayitli_dosya_gercek_kayitlar():
    from arayuz import kayitli
    kayitlar = kayitli.yukle()
    if not kayitlar:                      # demo/kayit_al.py henüz çalıştırılmadıysa
        return
    for k in kayitlar:
        assert k["kayit_tarihi"] and k["sonuc"]["durum"] and k["metin"]
    assert {"ENGELLE", "BILMIYORUM", "SORU_SOR", "HESAPLA"} <= {(k["sonuc"]["cikti"] or {}).get("davranis") for k in kayitlar}


def test_on_kontrol_tutarlilik_ozeti():
    from demo import on_kontrol as ok

    def r(dav, onc, sn):
        return {"beklenen": "HESAPLA", "sonuc": {"durum": "TAMAMLANDI", "toplam_sn": sn, "cikti": {
            "davranis": dav, "neden": None, "oncelik": onc, "risk": "NORMAL", "onay_gerekli": False}}}
    o = ok.tutarlilik_ozeti({"a": [r("HESAPLA", "P2", 10), r("HESAPLA", "P2", 20)],
                             "b": [r("HESAPLA", "P2", 5), r("HESAPLA", "P3", 7)]})
    assert o[0]["tutarli"] and o[0]["sure_ort"] == 15.0 and o[0]["sure_maks"] == 20
    assert not o[1]["tutarli"] and o[1]["farkli"] == 2
    assert "HAYIR" in ok.tablo_yaz(o) and "EVET" in ok.tablo_yaz(o)
    assert ok.model_var_mi("embeddinggemma", ["embeddinggemma:latest"]) and ok.model_var_mi("qwen3.5:4b", ["qwen3.5:4b"])
    assert not ok.model_var_mi("qwen3.5:4b", ["qwen3.5:9b"])


def test_sifirla_yedek_onay_ve_guvenlik(tmp_path):
    from demo import sifirla as sf
    (tmp_path / "checkpoints.sqlite").write_text("veri")
    (tmp_path / "checkpoints.db").write_text("takipli")
    (tmp_path / "baska.txt").write_text("dokunma")

    def yok_sayilan(p, k):
        return p.name.startswith("checkpoints.sqlite")
    sil, atla = sf.temizlenecekler(tmp_path, yok_sayilan)
    assert [p.name for p in sil] == ["checkpoints.sqlite"] and [p.name for p in atla] == ["checkpoints.db"]
    r = sf.sifirla(tmp_path, onay=lambda: False, kontrol=yok_sayilan)          # onay yok -> hiçbir şey olmaz
    assert not r["silindi"] and (tmp_path / "checkpoints.sqlite").exists() and not (tmp_path / "demo").exists()
    cagri = []
    r = sf.sifirla(tmp_path, onay=lambda: True, kontrol=yok_sayilan, baslat=lambda: cagri.append(1))
    assert r["silindi"] and cagri == [1] and not (tmp_path / "checkpoints.sqlite").exists()
    assert (Path(r["yedek"]) / "checkpoints.sqlite").read_text() == "veri"      # önce yedek
    assert (tmp_path / "checkpoints.db").exists() and (tmp_path / "baska.txt").exists()   # takipli/ilgisiz dosyaya dokunulmadı


def test_sifirla_git_kontrolu_gercek():
    from demo import sifirla as sf
    assert sf.git_yok_sayiyor_mu(sf.KOK / "checkpoints.sqlite") is True        # .gitignore: *.sqlite
    assert sf.git_yok_sayiyor_mu(sf.KOK / "ajan.py") is False                   # takipli kod dosyası asla silinmez


def test_ihlalli_ornek_saatten_bagimsiz():
    for saat in (0, 9, 14, 17, 23):
        for gun in range(16, 30):               # tüm hafta günleri
            simdi = datetime(2026, 11, gun, saat, 30)
            k = B.gecmis_is_gunu(simdi)
            assert k.weekday() <= 3 and k.hour == 10 and (simdi - k).days >= 3
            assert B.ornekler(simdi)[B.DEMO2]["kayit_zamani"] == k
