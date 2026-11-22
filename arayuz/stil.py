"""Görsel stil: küçük CSS + HTML parçaları (özel JavaScript, animasyon ve harici kütüphane yok).
Renk tek başına anlam taşımaz: her rozet ve kartta metin de vardır."""
from __future__ import annotations

from html import escape

import streamlit as st

VURGU = "#0e7490"     # tek vurgu rengi (teal)
LACIVERT = "#0f1f3d"

CSS = f"""
<style>
.stAppDeployButton, [data-testid="stToast"], [data-testid="stDecoration"] {{ display: none !important; }}
.block-container {{ padding-top: 2rem; max-width: 1180px; }}
h1, h2, h3, h4 {{ color: {LACIVERT}; letter-spacing: -0.01em; }}
section[data-testid="stSidebar"] {{ min-width: 330px; max-width: 330px; }}
section[data-testid="stSidebar"] * {{ white-space: normal; overflow-wrap: anywhere; }}
.panel-baslik {{ font-size: 1.45rem; font-weight: 700; line-height: 1.25; color: #fff; margin: 0 0 .15rem 0; }}
.panel-alt {{ font-size: .85rem; color: #9fb3d9; margin-bottom: 1rem; }}
.yan-kutu {{ background: #1b2f57; border-radius: 10px; padding: .7rem .9rem; margin: .5rem 0; font-size: .92rem; color: #e8eefb; }}
.yan-kutu b {{ color: #fff; }}
.yan-sayi {{ font-size: 1.6rem; font-weight: 700; color: #5eead4; }}
.pill {{ display: inline-block; padding: .18rem .7rem; border-radius: 999px; font-weight: 700; font-size: .92rem;
        border: 1px solid transparent; white-space: nowrap; }}
.pill-p1 {{ background: #fee4e2; color: #912018; border-color: #f4a7a0; }}
.pill-p2 {{ background: #ffead5; color: #93370d; border-color: #f7b27a; }}
.pill-p3 {{ background: #fef0c7; color: #7a4a05; border-color: #f0d078; }}
.pill-p4 {{ background: #d1fadf; color: #05603a; border-color: #8fd9ac; }}
.pill-yok {{ background: #e5e9f0; color: #344054; border-color: #c5cdd9; }}
.pill-hesapla {{ background: #d9f0f5; color: #0b5164; border-color: #8bc9d8; }}
.pill-bilmiyorum {{ background: #e5e9f0; color: #344054; border-color: #c5cdd9; }}
.pill-engelle {{ background: #e3e8fb; color: #2b3a8c; border-color: #aab6ee; }}
.pill-soru {{ background: #d9f0f5; color: #0b5164; border-color: #8bc9d8; }}
.pill-belirsiz {{ background: #efe3fb; color: #5b2a86; border-color: #cfb0ee; }}
.pill-hata {{ background: #fee4e2; color: #912018; border-color: #f4a7a0; }}
.kartlar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: .6rem 0 1rem 0; }}
.kart {{ background: #fff; border: 1px solid #dbe2ec; border-radius: 12px; padding: .8rem 1rem; }}
.kart.genis {{ grid-column: span 2; }}
.kart .et {{ font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; color: #5b6b86; margin-bottom: .25rem; }}
.kart .de {{ font-size: 1.4rem; font-weight: 700; color: {LACIVERT}; line-height: 1.25; overflow-wrap: anywhere; }}
.kart .al {{ font-size: .85rem; color: #5b6b86; margin-top: .2rem; }}
.sakin {{ background: #eaf1fb; border: 1px solid #c4d6f0; border-left: 6px solid #5b7fc7; border-radius: 12px;
         padding: .9rem 1.1rem; margin: .6rem 0; color: #1d2c4d; }}
.sakin .ba {{ font-weight: 700; font-size: 1.1rem; margin-bottom: .25rem; }}
.hatakart {{ background: #fff4f2; border: 1px solid #f4b8b0; border-left: 6px solid #d92d20; border-radius: 12px;
            padding: .9rem 1.1rem; margin: .6rem 0; color: #3b1511; }}
.kayitli {{ background: #fff7e0; border: 1px solid #f0d078; border-left: 6px solid #d99a00; border-radius: 10px;
           padding: .55rem .9rem; margin: .4rem 0 .8rem 0; font-weight: 600; color: #6b4a00; }}
.sonuc-baslik {{ display: flex; flex-wrap: wrap; align-items: center; gap: .6rem; margin: .8rem 0 .2rem 0; }}
.sonuc-baslik .ba {{ font-size: 1.25rem; font-weight: 700; color: {LACIVERT}; }}
.teknik {{ font-size: .8rem; color: #6b7a93; }}
.zaman {{ margin: .3rem 0 .6rem 0; }}
.adim {{ display: flex; align-items: center; gap: .7rem; padding: .35rem .7rem; border-radius: 8px; margin: 2px 0; }}
.adim .ik {{ width: 1.5rem; text-align: center; font-weight: 700; }}
.adim .ad {{ flex: 1; }}
.adim .su {{ font-variant-numeric: tabular-nums; color: #44546f; min-width: 5rem; text-align: right; }}
.adim.bitti .ik {{ color: #067647; }}
.adim.calisiyor {{ background: #fff3cd; border: 1px solid #f0d078; font-weight: 700; }}
.etiket {{ font-size: .75rem; font-weight: 700; padding: .08rem .5rem; border-radius: 6px; }}
.etiket.model {{ background: {VURGU}; color: #fff; }}
.etiket.kod {{ background: #dbe2ec; color: #344054; }}
.st-key-onay_karti {{ border: 2px solid #d97706; border-radius: 14px; padding: 1rem 1.2rem; background: #fffaf0; margin: 1rem 0; }}
.karar-karti {{ background: #eaf7ee; border: 1px solid #a6dcb8; border-left: 6px solid #12a150; border-radius: 12px;
              padding: .9rem 1.1rem; margin: .8rem 0; color: #14301f; }}
.karar-karti.red {{ background: #f6f1f1; border-color: #d9c3c3; border-left-color: #8c5a5a; color: #2d2222; }}
.karar-karti .ba {{ font-size: 1.2rem; font-weight: 700; margin-bottom: .3rem; }}
.kaynak {{ border-left: 3px solid {VURGU}; padding: .15rem 0 .15rem .8rem; margin: .5rem 0; }}
.kaynak .kb {{ font-weight: 700; color: {LACIVERT}; }}
.kaynak .kd {{ font-size: .8rem; color: #5b6b86; }}
.akis {{ display: flex; flex-wrap: wrap; align-items: stretch; gap: .5rem .3rem; margin: .5rem 0 1rem 0; }}
.akis .dugum {{ border-radius: 10px; padding: .55rem .8rem; min-width: 150px; max-width: 220px; font-size: .9rem; border: 1px solid; }}
.akis .dugum.model {{ background: #d9f0f5; border-color: {VURGU}; color: #0b4254; }}
.akis .dugum.kod {{ background: #eef1f6; border-color: #9aa8bd; color: #2a3750; }}
.akis .dugum b {{ display: block; margin-bottom: .1rem; }}
.akis .ok {{ align-self: center; color: #5b6b86; font-size: 1.3rem; padding: 0 .1rem; }}
.lejant span {{ margin-right: 1rem; }}
</style>
"""


def uygula():
    st.markdown(CSS, unsafe_allow_html=True)


def html(x: str):
    st.markdown(x, unsafe_allow_html=True)


# ------------------------------------------------------------------ HTML parçaları
def kac(x) -> str:
    return escape(str(x))


def rozet(metin: str, sinif: str) -> str:
    return f'<span class="pill pill-{sinif}">{kac(metin)}</span>'


ONCELIK_SINIF = {"P1": "p1", "P2": "p2", "P3": "p3", "P4": "p4"}
ONCELIK_AD = {"P1": "P1 · Kritik", "P2": "P2 · Yüksek", "P3": "P3 · Normal", "P4": "P4 · Düşük"}
RISK_SINIF = {"IHLAL": "p1", "YUKSEK": "p2", "NORMAL": "p4"}
RISK_AD = {"IHLAL": "İhlal", "YUKSEK": "Yüksek risk", "NORMAL": "Normal"}
DAVRANIS_SINIF = {"HESAPLA": "hesapla", "BILMIYORUM": "bilmiyorum", "ENGELLE": "engelle", "SORU_SOR": "soru",
                  "ONCELIK_BELIRLENEMEDI": "belirsiz"}


def oncelik_rozeti(o: str | None) -> str:
    return rozet(ONCELIK_AD.get(o, o or "—"), ONCELIK_SINIF.get(o, "yok"))


def risk_rozeti(r: str | None) -> str:
    return rozet(RISK_AD.get(r, r or "—"), RISK_SINIF.get(r, "yok"))


def davranis_rozeti(d: str | None) -> str:
    return rozet(d or "ISLENEMEDI", DAVRANIS_SINIF.get(d, "hata"))


def kart(etiket: str, deger_html: str, alt: str = "", genis: bool = False) -> str:
    """deger_html güvenilir (kod üretimi) HTML'dir; düz metin için kac() kullanın."""
    return (f'<div class="kart{" genis" if genis else ""}"><div class="et">{kac(etiket)}</div>'
            f'<div class="de">{deger_html}</div>' + (f'<div class="al">{kac(alt)}</div>' if alt else "") + "</div>")


def kartlar(kartlar_html: list[str]) -> str:
    return '<div class="kartlar">' + "".join(kartlar_html) + "</div>"


def zaman_cizgisi(satirlar: list[dict]) -> str:
    """bicimle.adim_satirlari çıktısından tik / süre / Model-Kod etiketli adım listesi."""
    if not satirlar:
        return '<div class="zaman"><div class="adim calisiyor"><span class="ik">●</span><span class="ad">Başlıyor…</span></div></div>'
    parcalar = []
    for s in satirlar:
        calisan = s["durum"] == "çalışıyor"
        etiket = "Model" if s["tur"] == "model" else "Kod"
        parcalar.append(
            f'<div class="adim {"calisiyor" if calisan else "bitti"}"><span class="ik">{"●" if calisan else "✓"}</span>'
            f'<span class="ad">{kac(s["etiket"])}{" — çalışıyor" if calisan else ""}</span>'
            f'<span class="etiket {s["tur"]}">{etiket}</span><span class="su">{kac(s["sure"])}</span></div>')
    return '<div class="zaman">' + "".join(parcalar) + "</div>"
