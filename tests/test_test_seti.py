"""data/test_seti.json doğrulaması.

Beklenen değerler elle yazılmıştır; burada (1) araçlarla (2) şemayla (3) müşteri verisiyle
(4) dokümanlardaki madde numaralarıyla çapraz kontrol edilir. Fark çıkarsa ya elle hesap
ya da araç yanlıştır; ikisi de incelenmelidir.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

import sla_araclari as s  # noqa: E402
from schemas.onay_paketi import BILMIYORUM_YANITI, KararCiktisi  # noqa: E402

VERI = json.loads((KOK / "data" / "test_seti.json").read_text(encoding="utf-8"))
TALEPLER = VERI["talepler"]
MUSTERILER = json.loads((KOK / "data" / "musteriler.json").read_text(encoding="utf-8"))["musteriler"]
DAVRANISLAR = {"HESAPLA", "SORU_SOR", "BILMIYORUM", "ENGELLE", "ONCELIK_BELIRLENEMEDI"}
DOK = {"01": "01_sla_sozlesmesi", "02": "02_oncelik_rehberi", "03": "03_eskalasyon_proseduru", "04": "04_destek_sss"}
HESAPLAMALAR = [t for t in TALEPLER if t["beklenen"]["davranis"] == "HESAPLA"]
ANA = [t for t in TALEPLER if t["set"] == "ana"]
ZOR = [t for t in TALEPLER if t["set"] == "zor"]
ANA_HESAP = [t for t in ANA if t["beklenen"]["davranis"] == "HESAPLA"]


def dt(x):
    return datetime.fromisoformat(x)


def test_yapi():
    ids = [t["id"] for t in TALEPLER]
    assert len(ids) == len(set(ids))
    for t in TALEPLER:
        assert t["beklenen"]["davranis"] in DAVRANISLAR
        assert dt(t["kayit_zamani"]) <= dt(t["simdi"])
        assert t["talep_metni"].strip() and t["hesap_notu"].strip() and isinstance(t["etiket"], list)
        assert t["yazar"] in {"claude", "kullanici"} and t["set"] in {"ana", "zor"}


@pytest.mark.parametrize("t", HESAPLAMALAR, ids=lambda t: t["id"])
def test_hesaplama_beklenenleri_araclarla_ayni(t):
    b = t["beklenen"]
    m = next(x for x in MUSTERILER if x["ad"] == b["musteri"])
    assert m["paket"] == b["paket"] and not m["ozel_anlasma"]
    sd = s.son_tarih_hesapla(dt(t["kayit_zamani"]), b["paket"], b["oncelik"])
    assert sd["son_tarih"] == dt(b["son_tarih"]), t["hesap_notu"]
    r = s.risk_degerlendir(sd["son_tarih"], dt(t["simdi"]), sd["takvim"], sd["sure_dk"])
    assert r["risk"] == b["risk"], t["hesap_notu"]
    kredi = s.kredi_hesapla(b["paket"], b["oncelik"], r["risk"] == "IHLAL", m["aylik_ucret"], m["bu_ay_kredi_yuzdesi"])
    if b["kredi"] is None:
        assert r["risk"] != "IHLAL"
    else:
        assert kredi["yuzde"] == b["kredi"]["yuzde"] and kredi["tutar"] == b["kredi"]["tutar"]
        assert kredi["neden"] == b["kredi"]["neden"]
    gerekli, nedenler = s.onay_gerekli(b["oncelik"], r["risk"], kredi["yuzde"])
    assert gerekli == b["onay_gerekli"] and nedenler == b["onay_nedenleri"]


def kaynaklar(t):
    out = []
    for k in t["beklenen_kaynak"]:
        no, madde = k.split(":")
        out.append({"dokuman": DOK[no], "madde": madde})
    return out


@pytest.mark.parametrize("t", TALEPLER, ids=lambda t: t["id"])
def test_beklenen_cikti_semaya_uyar(t):
    b = t["beklenen"]
    d = {"davranis": b["davranis"], "neden": b.get("neden"), "musteri": b.get("musteri"), "paket": b.get("paket")}
    if b["davranis"] == "HESAPLA":
        d.update({k: b[k] for k in ("oncelik", "son_tarih", "risk", "kredi", "onay_gerekli", "onay_nedenleri")})
        d.update(kaynaklar=kaynaklar(t), durum="BEKLEMEDE" if b["onay_gerekli"] else "TAMAMLANDI", mesaj="x")
    elif b["davranis"] == "ONCELIK_BELIRLENEMEDI":
        d.update(kaynaklar=kaynaklar(t), durum="TAMAMLANDI", mesaj="x")
    elif b["davranis"] == "BILMIYORUM":
        d.update(durum="TAMAMLANDI", mesaj=BILMIYORUM_YANITI)
    else:
        d.update(durum="TAMAMLANDI", mesaj="x")
    KararCiktisi.model_validate(d)


def test_musteri_senaryolari_veriyle_uyumlu():
    for t in TALEPLER:
        b = t["beklenen"]
        if b["neden"] == "ozel_anlasma":
            assert s.musteri_ara(b["musteri"], MUSTERILER)[1]["ozel_anlasma"] is True
        if b["neden"] == "musteri_kayitsiz":
            assert s.musteri_ara(b["musteri"], MUSTERILER)[0] == "YOK"
        if b["neden"] == "musteri_belirsiz":
            assert "Anadolu" in t["talep_metni"] and "Anadolu Lojistik" not in t["talep_metni"]
            assert s.musteri_ara("Anadolu", MUSTERILER)[0] == "BELIRSIZ"
        if b["neden"] == "musteri_adi_eksik":
            assert not any(m["ad"].split()[0] in t["talep_metni"] for m in MUSTERILER)
        if b["neden"] == "oncelik_belirlenemedi":
            m = s.musteri_ara(b["musteri"], MUSTERILER)[1]
            assert m["paket"] == b["paket"] and t["onceki_soru_soruldu"] is True and t["ikinci_mesaj"]


def test_kaynak_maddeleri_dokumanlarda_var():
    for t in TALEPLER:
        for k in t["beklenen_kaynak"]:
            no, madde = k.split(":")
            metin = (KOK / "docs" / f"{DOK[no]}.md").read_text(encoding="utf-8")
            var = (re.search(rf"^## Madde {re.escape(madde)} –", metin, re.M)
                   or re.search(rf"^{re.escape(madde)} ", metin, re.M)
                   or re.search(rf"^## {re.escape(madde)} –", metin, re.M))
            assert var, f"{t['id']}: {k} dokümanda yok"


def test_toplam_dagilim_50():
    from collections import Counter
    assert len(ANA) == 50 and len(TALEPLER) == 59
    assert Counter(t["grup"] for t in ANA) == {
        "normal": 9, "mesai_disi": 7, "kurumsal_724": 4, "ihlal_risk": 8, "kredi": 6,
        "soru_sor": 4, "bilmiyorum": 6, "engelle": 4, "oncelik_belirlenemedi": 2}
    assert Counter(t["beklenen"]["davranis"] for t in ANA) == {
        "HESAPLA": 34, "SORU_SOR": 4, "BILMIYORUM": 6, "ENGELLE": 4, "ONCELIK_BELIRLENEMEDI": 2}
    nedenler = Counter(t["beklenen"]["neden"] for t in ANA if t["beklenen"]["davranis"] != "HESAPLA")
    assert nedenler == {"musteri_adi_eksik": 2, "musteri_belirsiz": 1, "oncelik_belirsiz": 1,
                        "ozel_anlasma": 2, "kapsam_disi": 2, "dokumanda_yok": 1, "musteri_kayitsiz": 1,
                        "talimat_iceriyor": 4, "oncelik_belirlenemedi": 2}
    assert Counter(t["beklenen"]["oncelik"] for t in ANA_HESAP) == {"P1": 8, "P2": 9, "P3": 9, "P4": 8}
    risk = Counter(t["beklenen"]["risk"] for t in ANA_HESAP)
    assert min(risk.values()) >= 5, risk                      # üç risk seviyesi de yeterince temsil ediliyor
    assert sum(t["yazar"] == "kullanici" for t in ANA) == 6


def test_zor_set():
    from collections import Counter
    assert Counter(t["grup"] for t in ZOR) == {"yanlis_engelleme": 2, "acil_tuzagi": 1, "gurultulu": 2,
                                               "dolayli_komut": 2, "oncelik_siniri": 2}
    assert all(t["yazar"] == "kullanici" for t in ZOR)
    for t in ZOR:
        b = t["beklenen"]
        if t["grup"] == "dolayli_komut":                      # otorite iddiası komut statüsü kazandırmaz
            assert b["davranis"] == "ENGELLE" and b["neden"] == "talimat_iceriyor"
        else:
            assert b["davranis"] == "HESAPLA"
        if t["grup"] == "yanlis_engelleme":                   # komut kelimesi geçer ama komut yok
            assert "yanlis_engelleme_testi" in t["etiket"]
        if "acil_tuzagi" in t["etiket"]:                      # 'acil' geçen talepte öncelik P1 olmamalı (02 Madde 2.3)
            assert b["oncelik"] != "P1"


def test_kisaltilmis_musteri_adi_tek_kayda_cozulur():
    for t in TALEPLER:
        if "musteri_ifade" in t:
            assert t["musteri_ifade"].lower().split()[0] in t["talep_metni"].lower()
            durum, kayit = s.musteri_ara(t["musteri_ifade"], MUSTERILER)
            assert durum == "TEK" and kayit["ad"] == t["beklenen"]["musteri"], t["id"]
