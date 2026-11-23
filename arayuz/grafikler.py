"""Ölçüm grafikleri (Altair; Streamlit ile gelir, yeni paket yok). Sayılar olcum.karsilastir() çıktısından gelir.

Palet: ilk koşu #8A94A6 · düzeltme sonrası #0072B2 · vurgu/kötüleşme #D55E00 · metin #4B5563 · ızgara #CBD5E1 · beyaz zemin.
"""
from __future__ import annotations

import math

import altair as alt
import pandas as pd

ILK, SONRA, VURGU, METIN, IZGARA = "#8A94A6", "#0072B2", "#D55E00", "#4B5563", "#CBD5E1"


# ------------------------------------------------------------------ istatistik
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """%95 Wilson güven aralığı (oran olarak 0–1)."""
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    payda = 1 + z * z / n
    merkez = (p + z * z / (2 * n)) / payda
    yari = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / payda
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


def mcnemar_tam(b: int, c: int) -> float:
    """Exact McNemar (iki yönlü binom, p0=0,5): b = düzeldi, c = bozuldu."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, p)


def virgul(x: float, basamak: int = 1) -> str:
    return f"{x:.{basamak}f}".replace(".", ",")


# ------------------------------------------------------------------ ortak stil
def _stil(grafik: alt.TopLevelMixin, yukseklik: int) -> alt.TopLevelMixin:
    return (grafik.properties(height=yukseklik, background="white")
            .configure_view(stroke=None)
            .configure_axis(gridColor=IZGARA, gridWidth=0.6, domainColor=IZGARA, tickColor=IZGARA,
                            labelColor=METIN, titleColor=METIN, labelFontSize=12, titleFontSize=12)
            .configure_legend(disable=True))


# ------------------------------------------------------------------ 3) tam doğru: halter grafik
def tam_dogru_satirlari(r: dict) -> list[dict]:
    """Toplam (59), Ana set, Zor set, Bağımsız 15 (alt küme). Sayılar r (olcum.karsilastir) içinden."""
    def al(kosu, ad):
        return kosu["tam"][ad]
    satirlar = []
    ilk, sonra = r["ilk"], r["sonra"]
    toplam_ilk = (al(ilk, "Ana set")[0] + al(ilk, "Zor set")[0], al(ilk, "Ana set")[1] + al(ilk, "Zor set")[1])
    toplam_sonra = (al(sonra, "Ana set")[0] + al(sonra, "Zor set")[0], al(sonra, "Ana set")[1] + al(sonra, "Zor set")[1])
    for ad, i, s, alt_kume in (("Toplam", toplam_ilk, toplam_sonra, False), ("Ana set", al(ilk, "Ana set"), al(sonra, "Ana set"), False),
                               ("Zor set", al(ilk, "Zor set"), al(sonra, "Zor set"), False),
                               ("Bağımsız 15", al(ilk, "Bağımsız 15"), al(sonra, "Bağımsız 15"), True)):
        satirlar.append({"ad": ad, "n": i[1], "ilk": i[0], "sonra": s[0], "alt_kume": alt_kume,
                         "etiket": f"{ad}{'' if alt_kume else f' ({i[1]})'} · {i[0]}/{i[1]} → {s[0]}/{s[1]}" + ("  (Ana+Zor'un alt kümesi)" if alt_kume else "")})
    return satirlar


def tam_dogru_grafigi(r: dict):
    satirlar = tam_dogru_satirlari(r)
    veri = []
    for s in satirlar:
        for kosu, k in (("İlk ölçüm", s["ilk"]), ("Düzeltme sonrası", s["sonra"])):
            lo, hi = wilson(k, s["n"])
            veri.append({"etiket": s["etiket"], "kosu": kosu, "oran": 100 * k / s["n"], "alt": 100 * lo, "ust": 100 * hi,
                         "alt_kume": s["alt_kume"], "yazi": f"%{virgul(100 * k / s['n'], 0)}", "sayi": f"{k}/{s['n']}"})
    df = pd.DataFrame(veri)
    sira = [s["etiket"] for s in satirlar]
    y = alt.Y("etiket:N", sort=sira, title=None, axis=alt.Axis(labelLimit=420, grid=True))
    x = alt.X("oran:Q", title="Tam doğru oran (%) · çizgi: %95 Wilson güven aralığı", scale=alt.Scale(domain=[0, 100]),
              axis=alt.Axis(values=[0, 20, 40, 60, 80, 100]))
    renk = alt.Color("kosu:N", scale=alt.Scale(domain=["İlk ölçüm", "Düzeltme sonrası"], range=[ILK, SONRA]))
    baglanti = (alt.Chart(df).transform_pivot("kosu", value="oran", groupby=["etiket"])
                .mark_rule(color=METIN, strokeWidth=2, opacity=.55)
                .encode(y=y, x=alt.X("İlk ölçüm:Q", scale=alt.Scale(domain=[0, 100])), x2="Düzeltme sonrası:Q"))
    ci_ilk = (alt.Chart(df[df.kosu == "İlk ölçüm"]).mark_rule(strokeWidth=4, opacity=.35, yOffset=-7)
              .encode(y=y, x="alt:Q", x2="ust:Q", color=renk))
    ci_sonra = (alt.Chart(df[df.kosu == "Düzeltme sonrası"]).mark_rule(strokeWidth=4, opacity=.35, yOffset=7)
                .encode(y=y, x="alt:Q", x2="ust:Q", color=renk))
    nokta_dolu = (alt.Chart(df[~df.alt_kume]).mark_point(filled=True, size=130, opacity=1)
                  .encode(y=y, x=x, color=renk, tooltip=["etiket", "kosu", "sayi"]))
    nokta_bos = (alt.Chart(df[df.alt_kume]).mark_point(filled=False, size=130, strokeWidth=2.5)
                 .encode(y=y, x=x, color=renk, tooltip=["etiket", "kosu", "sayi"]))
    yazi_ilk = (alt.Chart(df[df.kosu == "İlk ölçüm"]).mark_text(dy=-17, fontSize=12, color=ILK, fontWeight="bold")
                .encode(y=y, x=x, text="yazi:N"))
    yazi_sonra = (alt.Chart(df[df.kosu == "Düzeltme sonrası"]).mark_text(dy=-17, fontSize=12, color=SONRA, fontWeight="bold")
                  .encode(y=y, x=x, text="yazi:N"))
    return _stil(alt.layer(baglanti, ci_ilk, ci_sonra, nokta_dolu, nokta_bos, yazi_ilk, yazi_sonra), 60 + 62 * len(satirlar))


# ------------------------------------------------------------------ 4) hata türleri
def hata_turu_satirlari(r: dict, etiket) -> list[dict]:
    """Adım bazında hatalı talep sayısı (Ana+Zor toplamı): [{ad, ilk, sonra}], rapordan gelen sayılarla."""
    adimlar = sorted({a for k in ("Ana set", "Zor set") for a in set(r["ilk"]["hata_turleri"][k]) | set(r["sonra"]["hata_turleri"][k])})
    return [{"ad": etiket(a), "ilk": sum(r["ilk"]["hata_turleri"][k].get(a, 0) for k in ("Ana set", "Zor set")),
             "sonra": sum(r["sonra"]["hata_turleri"][k].get(a, 0) for k in ("Ana set", "Zor set"))} for a in adimlar]


def hata_turu_grafigi(satirlar: list[dict]):
    veri = []
    for s in satirlar:
        etiket = f"{s['ad']} · {s['ilk']} → {s['sonra']}"
        veri += [{"etiket": etiket, "kosu": "İlk ölçüm", "adet": s["ilk"], "yazi": str(s["ilk"])},
                 {"etiket": etiket, "kosu": "Düzeltme sonrası", "adet": s["sonra"], "yazi": str(s["sonra"])}]
    df = pd.DataFrame(veri)
    sira = list(dict.fromkeys(df.etiket))
    en_cok = max(1, int(df.adet.max()))
    y = alt.Y("etiket:N", sort=sira, title=None, axis=alt.Axis(labelLimit=380))
    x = alt.X("adet:Q", title="Hatalı talep sayısı (adım bazında)", scale=alt.Scale(domain=[0, en_cok + 1], nice=False, zero=True),
              axis=alt.Axis(tickMinStep=1, format="d"))
    renk = alt.Color("kosu:N", scale=alt.Scale(domain=["İlk ölçüm", "Düzeltme sonrası"], range=[ILK, SONRA]))
    baglanti = (alt.Chart(df).transform_pivot("kosu", value="adet", groupby=["etiket"]).mark_rule(color=METIN, strokeWidth=2, opacity=.55)
                .encode(y=y, x=alt.X("İlk ölçüm:Q", scale=alt.Scale(domain=[0, en_cok + 1])), x2="Düzeltme sonrası:Q"))
    nokta = alt.Chart(df).mark_point(filled=True, size=150, opacity=1).encode(y=y, x=x, color=renk, tooltip=["etiket", "kosu", "adet"])
    yazi = alt.Chart(df).mark_text(dy=-16, fontSize=13, fontWeight="bold").encode(y=y, x=x, text="yazi:N", color=renk)
    return _stil(alt.layer(baglanti, nokta, yazi), 70 + 70 * len(sira))


# ------------------------------------------------------------------ 5) 59 kareli birim grafik
DEGISIM_GRUPLARI = [("Düzeldi", SONRA), ("Bozuldu", VURGU), ("Hâlâ hatalı", METIN), ("İki ölçümde de doğru", IZGARA)]


def degisim_gruplari(r: dict) -> dict[str, list[str]]:
    """Talep numaralarını (T..) dört gruba ayırır. Tüm talepler: T01..T{n}; sayılar rapor dosyalarından."""
    n = r["ilk"]["n"]
    tumu = [f"T{i:02d}" for i in range(1, n + 1)]
    duz, boz, hala = list(r["duzeldi"]), list(r["bozuldu"]), list(r["hala_hatali"])
    ayri = set(duz) | set(boz) | set(hala)
    return {"Düzeldi": duz, "Bozuldu": boz, "Hâlâ hatalı": hala, "İki ölçümde de doğru": [t for t in tumu if t not in ayri]}


def birim_grafik(r: dict, sutun: int = 10):
    """Her talep bir kare; satır satır gruplar (Düzeldi, Bozuldu, Hâlâ hatalı, İki ölçümde de doğru). Üzerine gelince T numarası."""
    gruplar = degisim_gruplari(r)
    renkler = dict(DEGISIM_GRUPLARI)
    veri, etiket_js, satir = [], {}, 0
    for ad, idler in gruplar.items():
        satir_sayisi = max(1, math.ceil(len(idler) / sutun))
        for j in range(satir_sayisi):
            etiket_js[f"r{satir + j}"] = f"{ad} · {len(idler)}" if j == 0 else ""
        for k, t in enumerate(idler):
            veri.append({"talep": t, "grup": ad, "sutun": k % sutun, "satir": f"r{satir + k // sutun}", "renk": renkler[ad],
                         "yazi_renk": METIN if renkler[ad] == IZGARA else "white"})
        satir += satir_sayisi
    df = pd.DataFrame(veri)
    sira = [f"r{i}" for i in range(satir)]
    ifade = "{" + ",".join(f"'{k}':'{v}'" for k, v in etiket_js.items()) + "}[datum.value] || ''"
    y = alt.Y("satir:N", sort=sira, title=None, axis=alt.Axis(labelExpr=ifade, labelLimit=260, ticks=False, domain=False, grid=False))
    x = alt.X("sutun:O", title=None, axis=None)
    kare = (alt.Chart(df).mark_square(size=720, stroke="white", strokeWidth=1.5)
            .encode(y=y, x=x, color=alt.Color("renk:N", scale=None), tooltip=[alt.Tooltip("talep:N", title="Talep"), alt.Tooltip("grup:N", title="Durum")]))
    yazi = (alt.Chart(df).mark_text(fontSize=9).encode(y=y, x=x, text="talep:N", color=alt.Color("yazi_renk:N", scale=None)))
    return (alt.layer(kare, yazi).properties(height=60 + 46 * satir, background="white")
            .configure_view(stroke=None).configure_axis(labelColor=METIN, labelFontSize=12))
