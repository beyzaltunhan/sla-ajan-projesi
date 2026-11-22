"""Arayüz FAZ 1: KPI şeridi, Ayrıntı kutuları, kayıtlı çalıştırma onay notu (model/Ollama gerekmez)."""
from __future__ import annotations

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

KAYIT = Path(__file__).resolve().parents[1] / "demo" / "kayitli_sonuclar.json"


def _calistir(ad_baslangic: str) -> AppTest:
    ad = next(k["ad"] for k in json.loads(KAYIT.read_text(encoding="utf-8"))["kayitlar"] if k["ad"].startswith(ad_baslangic))

    def uyg():
        import streamlit as st
        from arayuz import bilesenler as b, stil
        stil.uygula()
        st.session_state["kayit_sec"] = __import__("os").environ["KAYIT_AD"]
        b.kayitli_sekmesi()
    import os
    os.environ["KAYIT_AD"] = ad
    at = AppTest.from_function(uyg, default_timeout=30)
    at.run()
    return at


def _md(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_demo2_kpi_seridi_bes_kart_ve_onay_bekliyor():
    at = _calistir("Demo 2")
    assert not at.exception
    m = _md(at)
    assert m.count('class="kpi"') == 1
    for et in ("Öncelik", "Kalan süre", "Risk", "Kredi", "Onay durumu"):
        assert f'<div class="et">{et}</div>' in m
    assert "Onay bekliyor" in m and "İhlal" in m and "P2" in m
    assert "teknik durum" not in m.split("Ayrıntı")[0]            # başlıkta yok (Ayrıntı içinde)


def test_demo2_kayit_onay_dugmeleri_pasif_ve_notlu():
    at = _calistir("Demo 2")
    d = [b for b in at.button if b.label in ("Onayla", "Reddet")]
    assert len(d) == 2 and all(b.disabled for b in d)
    assert any("Kayıt, onay verilemez" in c.value for c in at.caption)
    assert any("Önceden çalıştırılmış kayıt, canlı değil" in x.value for x in at.markdown)


def test_demo1_engelle_hesap_karti_yok_karar_karti_var():
    at = _calistir("Demo 1")
    assert not at.exception
    m = _md(at)
    assert 'class="kpi"' not in m and '<div class="et">Karar</div>' in m
    assert "Onay durumu" not in m and "Kalan süre" not in m
    assert "Bu talep işlenmedi:" in m
    assert not [b for b in at.button if b.label in ("Onayla", "Reddet")]      # ENGELLE'de onay yok


def test_adim_zaman_cizgisi_acik_ve_ayrinti_kapali():
    at = _calistir("Demo 2")
    ex = {e.label: e for e in at.expander}
    assert ex["Adım zaman çizgisi"].proto.expanded is True
    assert ex["Ayrıntı"].proto.expanded is False
