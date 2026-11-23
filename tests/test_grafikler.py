"""FAZ 2: ölçüm grafikleri (Wilson, McNemar, grafik verisi). Sayılar rapor dosyalarından okunur."""
from __future__ import annotations

import json

import pytest
from streamlit.testing.v1 import AppTest

from arayuz import grafikler as G
from arayuz import olcum


def test_wilson_bilinen_degerler():
    lo, hi = G.wilson(44, 50)
    assert lo == pytest.approx(0.7619, abs=2e-3) and hi == pytest.approx(0.9438, abs=2e-3)
    lo, hi = G.wilson(49, 50)
    assert lo == pytest.approx(0.8950, abs=2e-3) and hi == pytest.approx(0.9964, abs=2e-3)
    lo, hi = G.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=2e-3)
    lo, hi = G.wilson(10, 10)
    assert hi == 1.0 and lo == pytest.approx(0.7225, abs=2e-3)
    assert G.wilson(0, 0) == (0.0, 0.0)


def test_mcnemar_9_2():
    assert G.mcnemar_tam(9, 2) == pytest.approx(0.0654, abs=5e-4)       # 2*(1+11+55)/2048
    assert G.mcnemar_tam(9, 2) == pytest.approx(134 / 2048)
    assert G.mcnemar_tam(5, 5) == 1.0 and G.mcnemar_tam(0, 0) == 1.0


def test_sayilar_rapordan_toplam_ve_gruplar():
    r = olcum.karsilastir()
    s = {x["ad"]: x for x in G.tam_dogru_satirlari(r)}
    assert (s["Toplam"]["ilk"], s["Toplam"]["sonra"], s["Toplam"]["n"]) == (49, 56, 59)
    assert (s["Ana set"]["ilk"], s["Ana set"]["sonra"], s["Ana set"]["n"]) == (44, 49, 50)
    assert (s["Zor set"]["ilk"], s["Zor set"]["sonra"], s["Zor set"]["n"]) == (5, 7, 9)
    assert s["Bağımsız 15"]["alt_kume"] and s["Bağımsız 15"]["etiket"].endswith("(Ana+Zor'un alt kümesi)")
    assert "44/50 → 49/50" in s["Ana set"]["etiket"]
    rapor = olcum.rapor_oku(olcum.SONRA_RAPOR)
    assert "| Tam doğru — Ana set (T01–T50) | 44/50 | 49/50 |" in rapor and "| Tam doğru — Zor set (T51–T59) | 5/9 | 7/9 |" in rapor


def test_hata_turu_ve_degisim_sayilari():
    r = olcum.karsilastir()
    h = {x["ad"]: (x["ilk"], x["sonra"]) for x in G.hata_turu_satirlari(r, olcum.hata_adi)}
    assert h == {"1c Talep türü": (5, 1), "Öncelik önerisi": (5, 2)}
    g = G.degisim_gruplari(r)
    assert [len(g[k]) for k in ("Düzeldi", "Bozuldu", "Hâlâ hatalı", "İki ölçümde de doğru")] == [9, 2, 1, 47]
    assert sum(len(v) for v in g.values()) == 59 and len({t for v in g.values() for t in v}) == 59


def test_grafikler_olusur_ve_palet_ve_eksen():
    r = olcum.karsilastir()
    for ch in (G.tam_dogru_grafigi(r), G.hata_turu_grafigi(G.hata_turu_satirlari(r, olcum.hata_adi)), G.birim_grafik(r)):
        d = ch.to_dict()
        assert d["background"] == "white" if "background" in d else True
    j = json.dumps(G.tam_dogru_grafigi(r).to_dict())
    assert G.ILK in j and G.SONRA in j and "[0, 100]" in j.replace('"', "").replace("\n", "") or '"domain": [0, 100]' in j
    hj = json.dumps(G.hata_turu_grafigi(G.hata_turu_satirlari(r, olcum.hata_adi)).to_dict())
    assert '"zero": true' in hj
    bj = json.dumps(G.birim_grafik(r).to_dict())
    assert '"title": "Talep"' in bj and bj.count("talep") > 0


def test_olcum_sekmesi_baslik_ve_ayrinti():
    def uyg():
        from arayuz import bilesenler as b, stil
        stil.uygula()
        b.olcum_sekmesi()
    at = AppTest.from_function(uyg, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("Toplam 59 talepte tam doğru: 49/59 → 56/59" in x.value for x in at.subheader)
    cap = " ".join(c.value for c in at.caption)
    assert "p = 0,065" in cap and "bağımsız kanıt değildir" in cap and "9 düzeldi / 2 bozuldu" in cap
    assert "52,2 → 65,9 sn" in " ".join(m.value for m in at.markdown)
    assert any(e.label == "Ölçüm bilgisi" for e in at.expander)
    assert len(at.get("vega_lite_chart")) == 3


# ---------------- FAZ 2.1
def test_faz21_etiketler_ve_baglanti_cumlesi():
    r = olcum.karsilastir()
    et = [s["etiket"] for s in G.tam_dogru_satirlari(r)]
    assert any(e.startswith("Bağımsız 15 · ") for e in et) and "(15)" not in " ".join(et)
    assert any(e.startswith("Ana set (50)") for e in et)
    def uyg():
        from arayuz import bilesenler as b, stil
        stil.uygula()
        b.olcum_sekmesi()
    at = AppTest.from_function(uyg, default_timeout=60).run()
    assert not at.exception
    metin = " ".join(c.value for c in at.caption) + " ".join(m.value for m in at.markdown)
    d = len(G.degisim_gruplari(r)["İki ölçümde de doğru"])
    assert f"İlk ölçümde doğru: {d} + {len(r['bozuldu'])} = {d + len(r['bozuldu'])}; düzeltme sonrası doğru: {d} + {len(r['duzeldi'])} = {d + len(r['duzeldi'])}." in metin
    assert "İlk ölçümde doğru: 47 + 2 = 49" in metin and "47 + 9 = 56" in metin
    assert "koşu" not in " ".join(c.value for c in at.caption)


def test_faz21_karar_sonrasi_cumle_gizlenir():
    from arayuz import bicimle as B
    m = "Öncelik P2. Yönetici onayı bekleniyor."
    assert B.onay_cumlesi_gizle(m, False) == m
    assert B.onay_cumlesi_gizle(m, True) == "Öncelik P2."


def test_faz21_ornek_adlari():
    from arayuz import bicimle as B
    assert B.gorunen_ad("Demo 1: Komutlu talep") == "Güvenlik: komut içeren talep"
    assert B.gorunen_ad("Demo 2: İhlalli P2 talep") == "SLA ihlali: onay gerektiren talep"
    assert not any(a.startswith("Demo") for a in B.ornekler(__import__("datetime").datetime.now()))
