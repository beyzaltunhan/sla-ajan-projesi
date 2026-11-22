"""Streamlit bileşenleri (Adım 7B: görsel tasarım). İşlevler 7A ile aynıdır; görünüm arayuz/stil.py'den gelir."""
from __future__ import annotations

import re
import subprocess
import threading
import time
from datetime import datetime
from html import escape

import streamlit as st

import ajan
import config
from arayuz import bicimle as B
from arayuz import bildirimler as BL
from arayuz import kayitli, model, olcum
from arayuz import stil as S

# ------------------------------------------------------------------ yardımcılar
SEKMELER = ["Talep İşle", "Ölçüm Sonuçları", "Mimari ve Sınırlamalar", "Bildirimler", "Kayıtlı Çalıştırmalar"]


def _durum_baslat():
    ss = st.session_state
    ss.setdefault("sayac", 0)
    ss.setdefault("son", None)             # son işlenen talebin sonuç sözlüğü (+ talep metni)
    ss.setdefault("onay_hatasi", {})       # thread_id -> ajanın verdiği hata/engel mesajı
    ss.setdefault("onaylananlar", {})      # thread_id -> onay_ver sonucu
    ss.setdefault("isinma", None)


def _birlestir(d, t) -> datetime:
    return datetime.combine(d, t)


def md_sade(metin: str) -> str:
    """Kaçışlı güvenli HTML: **kalın** ve satır sonları."""
    x = escape(metin)
    x = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", x)
    return x.replace("\n\n", "<br><br>").replace("\n", "<br>")


@st.cache_data(show_spinner=False)
def _surum() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5,
                              cwd=str(config.ROOT)).stdout.strip() or "—"
    except Exception:  # noqa: BLE001
        return "—"


# ------------------------------------------------------------------ yan çubuk
def yan_cubuk():
    ss = st.session_state
    sb = st.sidebar
    with sb:
        S.html('<div class="panel-baslik">SLA Operasyon Paneli</div>'
               '<div class="panel-alt">Poyraz Bulut Yazılım A.Ş. · kurgusal prototip</div>')
        if ss.isinma is None:
            with st.spinner("Modeller ısıtılıyor…"):
                ss.isinma = model.isit()
        i = ss.isinma
        if i["durum"] == "hazir":
            S.html(f'<div class="yan-kutu"><b>Model durumu: hazır</b><br>{S.kac(i["ayrinti"])} ({B.sure_yaz(i["sure_sn"])})</div>')
        else:
            S.html(f'<div class="yan-kutu"><b>Model durumu: hazır değil</b><br>{S.kac(i["ayrinti"])}</div>')
        if st.button("Modeli ısıt", use_container_width=True):
            with st.spinner("Modeller ısıtılıyor…"):
                ss.isinma = model.isit()
            st.rerun()
        ss.bekleyen_yer = st.empty()
        with st.expander("Teknik bilgi"):
            st.caption(f"Model: {config.CHAT_MODEL} (think kapalı) · Embedding: {config.EMBED_MODEL} · Sürüm: {_surum()}")
        st.caption("CPU'da çalışır · talep başı ~10 sn–2 dk")


def bekleyen_sayisi_yaz():
    """Yan çubuktaki bekleyen onay sayısı (sayfa sonunda, güncel durumla)."""
    try:
        n = len(B.bekleyen_onaylar(ajan.graf()))
    except Exception:  # noqa: BLE001
        n = "?"
    st.session_state.bekleyen_yer.markdown(
        f'<div class="yan-kutu"><b>Bekleyen onay</b><br><span class="yan-sayi">{n}</span></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ Talep İşle: form
def _ornek_sec():
    ss = st.session_state
    ad = ss.get("ornek_ad")
    if ad and ad != "—":
        o = B.ornekler(_birlestir(ss.simdi_d, ss.simdi_t))[ad]
        ss.talep_metni = o["metin"]
        ss.soru_soruldu = o["soru_soruldu"]
        ss.kayit_d, ss.kayit_t = o["kayit_zamani"].date(), o["kayit_zamani"].time().replace(microsecond=0, second=0)


def _simdiyi_guncelle():
    n = datetime.now().replace(microsecond=0, second=0)
    st.session_state.simdi_d, st.session_state.simdi_t = n.date(), n.time()


def talep_formu() -> tuple[str, datetime, datetime, bool] | None:
    ss = st.session_state
    if "simdi_d" not in ss:
        _simdiyi_guncelle()
        ss.kayit_d, ss.kayit_t = ss.simdi_d, ss.simdi_t
    ss.setdefault("talep_metni", "")
    ss.setdefault("soru_soruldu", False)
    st.selectbox("Hazır örnek", ["—"] + list(B.ornekler(datetime.now())), key="ornek_ad", on_change=_ornek_sec)
    st.text_area("Talep metni", key="talep_metni", height=110)
    basildi = st.button("İşle", type="primary")
    with st.expander("Gelişmiş ayarlar"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Kayıt zamanı** (talebin açıldığı an)")
            st.date_input("Kayıt tarihi", key="kayit_d")
            st.time_input("Kayıt saati", key="kayit_t")
        with c2:
            st.markdown("**Şimdi** (değerlendirme anı)")
            st.date_input("Şimdi tarihi", key="simdi_d")
            st.time_input("Şimdi saati", key="simdi_t")
            st.button("Şimdi'yi sistem saatine ayarla", on_click=_simdiyi_guncelle)
        st.checkbox("Bu talepte müşteriye daha önce soru soruldu (ikinci tur)", key="soru_soruldu")
    if basildi:
        if not ss.talep_metni.strip():
            st.warning("Lütfen bir talep metni yazın.")
            return None
        return ss.talep_metni, _birlestir(ss.kayit_d, ss.kayit_t), _birlestir(ss.simdi_d, ss.simdi_t), bool(ss.soru_soruldu)
    return None


def isle_canli(metin: str, kayit: datetime, simdi: datetime, soru_soruldu: bool = False):
    """Ajanı ayrı thread'de çalıştırır; ana thread checkpointer'dan adım durumunu okuyup canlı gösterir."""
    ss = st.session_state
    ss.sayac += 1
    tid = B.yeni_thread_id(ss.sayac)
    g = ajan.graf()                                    # ana thread'de oluştur (thread'de yarış olmasın)
    cfg = {"configurable": {"thread_id": tid}}
    kutu: dict = {}

    def hedef():
        try:
            kutu["sonuc"] = ajan.talep_isle(metin, kayit, simdi, tid, soru_soruldu=soru_soruldu)
        except Exception as e:  # noqa: BLE001  (arayüz çökmesin)
            kutu["istisna"] = e

    th = threading.Thread(target=hedef, daemon=True)
    t0 = time.perf_counter()
    th.start()
    yer = st.empty()
    while th.is_alive():
        try:
            v = g.get_state(cfg)
            satirlar = B.adim_satirlari(v.values.get("adim_sureleri", []), list(v.next))
        except Exception:  # noqa: BLE001
            satirlar = []
        with yer.container():
            S.html(f'<div class="sonuc-baslik"><span class="ba">İşleniyor…</span>'
                   f'<span class="teknik">geçen süre {B.sure_yaz(time.perf_counter() - t0)}</span></div>'
                   + S.zaman_cizgisi(satirlar))
        time.sleep(0.5)
    th.join()
    yer.empty()
    toplam = time.perf_counter() - t0
    if "istisna" in kutu:
        e = kutu["istisna"]
        ss.son = {"thread_id": tid, "talep": metin, "toplam_sn": toplam, "durum": "ISLENEMEDI", "cikti": None,
                  "onay_sonucu": None, "bekleyen_onay": None, "adim_sureleri": [],
                  "hata": {"adim": "?", "mesaj": f"{type(e).__name__}: {e}"}}
    else:
        ss.son = {**kutu["sonuc"], "talep": metin, "toplam_sn": toplam}


# ------------------------------------------------------------------ sonuç kartı (canlı ve kayıtlı ortak)
def sonuc_goster(s: dict, kayit: dict | None = None, onay=None):
    """Bir talebin sonucu. `kayit` verilirse 'önceden çalıştırılmış kayıt' etiketi gösterilir (asla canlı gibi görünmez).
    Sıra: başlık → KPI şeridi → müşteri/paket → gerekçe → onay kartı (`onay` çağrısı) → adım çizgisi → kaynaklar → Ayrıntı → Ham JSON."""
    c = s.get("cikti")
    d = (c or {}).get("davranis")
    if kayit:
        S.html(f'<div class="kayitli">Önceden çalıştırılmış kayıt, canlı değil · kayıt tarihi: {S.kac(kayit["kayit_tarihi"])}</div>')
    S.html('<div class="sonuc-baslik">' + S.davranis_rozeti(d) + f'<span class="ba">{S.kac(B.davranis_basligi(c, s["durum"]))}</span>'
           f'<span class="teknik">toplam {S.kac(B.sure_yaz(s.get("toplam_sn")))}</span></div>')
    kart = B.durum_karti(c, s.get("hata"), (st.session_state.get("isinma") or {}).get("durum") == "hata")
    if kart:
        if c and c.get("davranis"):
            S.html(S.kpi_seridi([S.kart("Karar", S.davranis_rozeti(c["davranis"])),
                                 S.kart("Müşteri", S.kac(c.get("musteri") or "—"))]))
        if kart[0] == "hata":
            S.html(f'<div class="hatakart">{md_sade(kart[1])}</div>')
        else:
            S.html(f'<div class="sakin">{md_sade(kart[1])}</div>')
    else:
        _hesapla_goster(c, s)
    if onay:
        onay()
    if s.get("onay_sonucu"):
        _karar_karti(s["onay_sonucu"])
    with st.expander("Adım zaman çizgisi", expanded=True):
        S.html(S.zaman_cizgisi(B.adim_satirlari(s.get("adim_sureleri", []))))
    if c and not kart:
        _kaynaklar_goster(c["kaynaklar"])
    with st.expander("Ayrıntı"):
        teknik = [f"teknik durum: {s['durum']}"]
        if s.get("thread_id"):
            teknik.append(f"talep_id: {s['thread_id']}")
        if c and c.get("neden"):
            teknik.append(f"neden: {B.NEDEN_ACIKLAMA.get(c['neden'], c['neden'])}")
        if c and c.get("onay_nedenleri"):
            teknik.append("onay nedenleri: " + B.onay_nedenleri_yaz(c["onay_nedenleri"]))
        st.caption(" · ".join(teknik))
    if c:
        with st.expander("Ham JSON (KararCiktisi)"):
            st.json(c)


def _onay_durumu(c: dict, s: dict) -> tuple[str, str]:
    """(metin, rozet sınıfı): Onay bekliyor (turuncu) / Onaylandı (yeşil) / Reddedildi / Gerekmiyor."""
    o = s.get("onay_sonucu")
    if o:
        return ("Onaylandı", "p4") if o.get("karar") == "ONAYLA" else ("Reddedildi", "hata")
    if c.get("onay_gerekli"):
        return "Onay bekliyor", "p2"
    return "Gerekmiyor", "yok"


def _hesapla_goster(c: dict, s: dict | None = None):
    k = c.get("kredi") or {}
    kredi_de = f"%{k.get('yuzde', 0):g} · {k.get('tutar', 0):,.0f} TL".replace(",", ".")
    ad, sinif = _onay_durumu(c, s or {})
    S.html(S.kpi_seridi([
        S.kart("Öncelik", S.oncelik_rozeti(c["oncelik"])),
        S.kart("Kalan süre", S.kac(B.kalan_sure_yaz(c.get("kalan_dk"))), alt=f"Son tarih {B.tarih_yaz(c['son_tarih'])}"),
        S.kart("Risk", S.risk_rozeti(c["risk"])),
        S.kart("Kredi", S.kac(kredi_de), alt=B.KREDI_NEDEN.get(k.get("neden"), k.get("neden", ""))),
        S.kart("Onay durumu", S.rozet(ad, sinif))]))
    S.html(f'<div class="silik">{S.kac(c["musteri"])} · Paket: {S.kac(str(c["paket"]).capitalize())}</div>')
    S.html(f'<p style="margin:.6rem 0"><b>Gerekçe / özet:</b> {S.kac(c["mesaj"])}</p>')


def _kaynak_html(k: dict) -> str:
    satirlar = "<br>".join(md_sade(x) for x in k["satirlar"])
    baslik = f" — {S.kac(k['baslik'])}" if k["baslik"] else ""
    return (f'<div class="kaynak"><div class="kb">Madde {S.kac(k["madde"])}{baslik}</div>'
            f'<div class="kd">{S.kac(k["dokuman"])}</div><div>{satirlar}</div></div>')


def _kaynaklar_goster(kaynaklar: list[dict]):
    ana, diger = B.kaynaklari_grupla(B.kaynak_listesi(kaynaklar))
    st.markdown("#### Kaynak maddeler")
    for k in ana:
        baslik = f" — {k['baslik']}" if k["baslik"] else ""
        with st.expander(f"Madde {k['madde']}{baslik} · {k['dokuman']}"):
            S.html("<br>".join(md_sade(x) for x in k["satirlar"]))
    if diger:
        S.html('<div class="silik" style="margin:.6rem 0 .2rem 0">Diğer ilgili maddeler</div>')
    for grup, liste in diger.items():
        with st.expander(f"{grup} ({len(liste)} madde)"):
            S.html("".join(_kaynak_html(k) for k in liste))


def _karar_karti(o: dict):
    red = o.get("karar") != "ONAYLA"
    islemler = B.uygulanan_islemler(o)
    liste = ("<ul>" + "".join(f"<li>{S.kac(i)}</li>" for i in islemler) + "</ul>") if islemler else \
        "<div>Ajan hiçbir işlem uygulamadı.</div>"
    gerekce = f'<div>Gerekçe: {S.kac(o["gerekce"])}</div>' if o.get("gerekce") else ""
    S.html(f'<div class="karar-karti{" red" if red else ""}"><div class="ba">Karar: {"Reddedildi" if red else "Onaylandı"}</div>'
           f'{gerekce}<div style="margin-top:.5rem"><b>Onaydan sonra yapılan işler</b></div>{liste}</div>')
    with st.expander("Ayrıntı"):
        st.caption("Onay paketinin durum alanı BEKLEMEDE kalır; sonuç `onay_sonucu` alanındadır (karar, gerekçe, uygulanan işlemler).")
        st.json(o)


# ------------------------------------------------------------------ Onay
def dugme_cifti(anahtar: str):
    """Onayla/Reddet için solda, yan yana, etiketi kesilmeyen iki sütun (CSS: st-key-dugme_*)."""
    with st.container(key=f"dugme_{anahtar}"):
        return st.columns(2)


def onay_paneli(tid: str, paket: dict, anahtar: str):
    """Sade onay kartı + Onayla/Reddet. Reddet için gerekçe zorunludur (kuralı ajan uygular; boşsa ajanın hatası gösterilir)."""
    ss = st.session_state
    with st.container(key="onay_karti" if anahtar == "son" else f"onay_karti_{anahtar}"):
        st.markdown("### Yönetici onayı gerekiyor")
        st.markdown(f"**Onay nedenleri:** {B.onay_nedenleri_yaz(paket['onay_nedenleri'])}")
        gerekce = st.text_input("Gerekçe (Reddet için zorunlu)", key=f"gerekce_{anahtar}")
        c1, c2 = dugme_cifti(f"onay_{anahtar}")
        karar = "ONAYLA" if c1.button("Onayla", key=f"onayla_{anahtar}", type="primary") else \
            ("REDDET" if c2.button("Reddet", key=f"reddet_{anahtar}") else None)
        if karar:
            try:
                r = ajan.onay_ver(tid, karar, gerekce)
            except ValueError as e:                    # ajanın kendi engeli (ör. gerekçesiz red) olduğu gibi gösterilir
                ss.onay_hatasi[tid] = str(e)
            except Exception as e:  # noqa: BLE001
                ss.onay_hatasi[tid] = B.hata_mesaji({"mesaj": f"{type(e).__name__}: {e}"})
            else:
                ss.onay_hatasi.pop(tid, None)
                ss.onaylananlar[tid] = r
                if ss.son and ss.son["thread_id"] == tid:
                    ss.son = {**r, "talep": ss.son["talep"], "toplam_sn": ss.son.get("toplam_sn")}
                st.rerun()
        if tid in ss.onay_hatasi:
            st.error(ss.onay_hatasi[tid])
        if anahtar == "son":
            with st.expander("Ayrıntı"):
                st.caption(f"talep: {tid}")
        else:                                           # liste zaten bir açılır kutu içinde (iç içe açılır kutu olmaz)
            st.caption(f"talep: {tid}")


def bekleyen_onaylar_paneli(haric: str | None = None):
    st.subheader("Bekleyen onaylar")
    st.caption("Kalıcı kayıttan (SqliteSaver) okunur; uygulama yeniden başlasa da listelenir ve devam ettirilebilir.")
    try:
        liste = [b for b in B.bekleyen_onaylar(ajan.graf()) if b["thread_id"] != haric]   # yukarıda zaten gösterilen hariç
    except Exception as e:  # noqa: BLE001
        st.error(f"Bekleyen onaylar okunamadı: {type(e).__name__}: {e}")
        return
    if not liste:
        st.info("Bekleyen onay yok.")
        return
    for b in liste:
        with st.expander(f"{b['thread_id']} — {b['paket'].get('musteri', '?')} / {b['paket'].get('oncelik', '?')}"):
            st.write(b["talep"])
            onay_paneli(b["thread_id"], b["paket"], f"liste_{b['thread_id']}")


def talep_sekmesi():
    ss = st.session_state
    girdi = talep_formu()
    if girdi:
        isle_canli(*girdi)
    if ss.son:
        st.markdown(f"**Talep:** {ss.son['talep']}")
        bekliyor = ss.son["durum"] == "BEKLEMEDE" and ss.son.get("cikti")
        sonuc_goster(ss.son, onay=(lambda: onay_paneli(ss.son["thread_id"], ss.son["cikti"], "son")) if bekliyor else None)
    st.divider()
    bekleyen_onaylar_paneli(haric=ss.son["thread_id"] if ss.son and ss.son["durum"] == "BEKLEMEDE" else None)


# ------------------------------------------------------------------ Ölçüm Sonuçları
def olcum_sekmesi():
    st.info("Temiz sayım ilk koşudur; düzeltme sonrası sayılar tam bağımsız değildir.")
    try:
        r = olcum.karsilastir()
    except Exception as e:  # noqa: BLE001
        st.error(f"Ölçüm dosyaları okunamadı: {type(e).__name__}: {e}")
        return
    ilk, sonra = r["ilk"], r["sonra"]
    with st.expander("Ölçüm bilgisi"):
        st.caption(olcum.NOT)
        st.caption(f"İlk koşu: commit {ilk['meta']['commit'][:8]}, {ilk['meta']['tarih']} · Düzeltme sonrası: commit "
                   f"{sonra['meta']['commit'][:8]}, {sonra['meta']['tarih']} · model {sonra['meta']['chat_model']}")
        st.caption(f"Kesinti şüpheli talepler hariç ortalama: {ilk['gecikme_ort_supheli_haric']} → {sonra['gecikme_ort_supheli_haric']} sn "
                   f"(işaretlenenler: ilk {', '.join(ilk['supheli']) or '—'}; sonra {', '.join(sonra['supheli']) or '—'}). "
                   "Süre, CPU'da çalışan küçük modelin ve o anki makine yükünün ürünüdür.")
    st.subheader("Tam doğru: ilk koşu → düzeltme sonrası (kaç/N)")
    kartlar = [S.kart(ad, S.kac(f"{olcum.kn(*ilk['tam'][ad])} → {olcum.kn(*sonra['tam'][ad])}"),
                      alt=f"Davranış doğru: {olcum.kn(*ilk['dav'][ad])} → {olcum.kn(*sonra['dav'][ad])}")
               for ad in ("Ana set", "Zor set", "Bağımsız 15")]
    S.html(S.kartlar(kartlar))
    S.html(S.kartlar([
        S.kart("Onay yakalama", S.kac(f"{olcum.kn(*ilk['onay_yakalama'])} → {olcum.kn(*sonra['onay_yakalama'])}"),
               alt="onay gerekenlerde onay istendi"),
        S.kart("Yanlış alarm", S.kac(f"{olcum.kn(*ilk['yanlis_alarm'])} → {olcum.kn(*sonra['yanlis_alarm'])}"),
               alt="onay gerekmezken onay istendi"),
        S.kart("Ortalama gecikme", S.kac(f"{ilk['gecikme_ort']} → {sonra['gecikme_ort']} sn"), alt="talep başına")]))
    import pandas as pd
    kume = ("Ana set", "Zor set", "Bağımsız 15")
    st.markdown("**Tam doğru talep sayısı** (küme büyüklükleri: " + ", ".join(f"{k}: {ilk['tam'][k][1]}" for k in kume) + ")")
    st.bar_chart(pd.DataFrame({"İlk koşu": [ilk["tam"][k][0] for k in kume], "Düzeltme sonrası": [sonra["tam"][k][0] for k in kume]},
                              index=list(kume)), color=["#9aa8bd", S.VURGU], stack=False)
    _kaynak_bulma_kartlari()
    st.subheader("Hata türleri (hatalı talep sayısı, adım bazında)")
    adimlar = sorted({a for k in ("Ana set", "Zor set") for a in set(ilk["hata_turleri"][k]) | set(sonra["hata_turleri"][k])})
    if adimlar:
        etiket = [olcum.hata_adi(a) for a in adimlar]
        st.bar_chart(pd.DataFrame(
            {"İlk koşu": [sum(ilk["hata_turleri"][k].get(a, 0) for k in ("Ana set", "Zor set")) for a in adimlar],
             "Düzeltme sonrası": [sum(sonra["hata_turleri"][k].get(a, 0) for k in ("Ana set", "Zor set")) for a in adimlar]},
            index=etiket), color=["#9aa8bd", S.VURGU], stack=False, horizontal=True, height=60 + 90 * len(adimlar))
    st.subheader("Talep bazında değişim")
    st.markdown(f"- **Düzeldi ({len(r['duzeldi'])}):** {', '.join(r['duzeldi']) or '—'}\n"
                f"- **Bozuldu — yeni regresyon ({len(r['bozuldu'])}):** {', '.join(r['bozuldu']) or '—'}\n"
                f"- **Hâlâ hatalı ({len(r['hala_hatali'])}):** {', '.join(r['hala_hatali']) or '—'}\n"
                f"- **İki koşuda da doğru:** {r['degismedi_dogru']}")
    for baslik, yol in (("İlk koşu raporu (dondurulmuş)", olcum.ILK_RAPOR), ("Düzeltme sonrası rapor", olcum.SONRA_RAPOR)):
        with st.expander(baslik):
            md = olcum.rapor_oku(yol)
            st.markdown(md) if md else st.warning(f"{yol.name} bulunamadı.")


def _kaynak_bulma_kartlari():
    """Doğru kaynak maddeyi bulma: sonuclar/duzeltme_sonrasi_rapor.md içindeki tablodan OKUNUR (sayı kodda yazılı değildir)."""
    satirlar = olcum.kaynak_bulma(olcum.rapor_oku(olcum.SONRA_RAPOR))
    st.subheader("Doğru kaynak maddeyi bulma (kaç/N)")
    if not satirlar:
        st.caption("Doğru kaynak bulma tablosu raporda bulunamadı.")
        return
    kartlar = []
    for r in satirlar:
        kume = r["kume"].split(" (")[0]
        grup = "Öncelik kuralı (Doküman 02)" if r["grup"].startswith("02") else "Hesap kaynakları (Doküman 01/03/04)"
        i, y = r["ilk"], r["sonra"]
        kartlar.append(S.kart(f"{grup} — {kume}", S.kac(f"tümü {olcum.kn(*i['tumu'])} → {olcum.kn(*y['tumu'])}"),
                              alt=f"en az biri {olcum.kn(*i['en_az_biri'])} → {olcum.kn(*y['en_az_biri'])} · madde {olcum.kn(*i['madde'])} → {olcum.kn(*y['madde'])}"))
    S.html(S.kartlar(kartlar))
    st.caption("Tümü: talebin beklenen kaynak maddelerinin hepsi bulundu; en az biri: en az biri bulundu. BILMIYORUM/SORU_SOR/ENGELLE "
               "kaynak taşımadığı için bu tabloya girmez. Sayılar düzeltme sonrası raporun 8. bölümünden okunur.")


# ------------------------------------------------------------------ Mimari ve Sınırlamalar
ADIMLAR = [
    ("1a Müşteri bulma", "kod", "Metinde kayıtlı firma adı aranır (TEK / BELİRSİZ / BULUNAMADI)."),
    ("1b Komut tespiti", "model", "Metin sistemi yönlendirmeye çalışan bir komut içeriyor mu? İçeriyorsa ENGELLE."),
    ("1c Talep türü", "model", "destek talebi / kapsam dışı / dokümanda olmayan."),
    ("1d Firma adı yedeği", "model", "Yalnızca 1a bulamazsa; model yalnızca metinde birebir geçen adı verebilir."),
    ("Ön yönlendirme", "kod", "Sabit sıra: BILMIYORUM / SORU_SOR / devam."),
    ("Öncelik önerisi", "model + doküman", "Doküman 02 parçaları + sabit çekirdek maddeler; P1–P4 veya belirsiz; madde numaraları kodla süzülür."),
    ("Öncelik yönlendirme", "kod", "Belirsizse SORU_SOR; zaten soruldu ise ONCELIK_BELIRLENEMEDI."),
    ("Hesaplar", "kod", "Son tarih (takvim/tatil), kalan süre, risk, kredi."),
    ("Onay kararı", "kod", "P1, ihlal, yüksek risk veya kredi önerisi varsa onay gerekir."),
    ("Paket doğrulama", "kod", "Pydantic şeması; geçersiz paket yöneticiye gitmez."),
    ("İnsan onayı", "kod", "Onay bekler (otomatik onay yok); onaydan sonra uygulama kaydı tutulur."),
]
SINIRLAMALAR = [
    "Veri sentetiktir (kurgusal firma ve sözleşme); gerçek müşteri verisi yoktur.",
    "Küçük yerel model (qwen3.5:4b) CPU'da çalışır: talep başına yaklaşık 10 sn ile 2 dk arası sürer (komut engelleme hızlı, hesaplama yapan talepler en yavaş).",
    "Küçük model talep türü ve öncelik önerisinde hata yapabilir; bu yüzden kritik kararları insan verir. Zor sette öncelik kuralı maddesi hiç tam bulunamadı (0/7).",
    "Yalnızca verilen SLA dokümanlarındaki kurallar kullanılır; dokümanda olmayan konuda \"bilmiyorum\" der.",
    "Talepler tek model üzerinde sırayla işlenir; eşzamanlı yük test edilmedi.",
    "Test seti küçüktür (59 talep, bağımsız alt küme 15): oranlar belirsizlik içerir, kaba bir göstergedir; düzeltme sonrası sayılar tam bağımsız değildir.",
    "Onaydan sonraki işlemler (kredi, eskalasyon) prototipte yalnızca kayıt olarak tutulur; dış sistem ve bildirimler sentetik simülatördür (gerçek Zendesk/Jira/e-posta/Slack yok).",
]
SINIRLAMA_AYRINTI = [
    "MCP sunucusu hesap araçlarını standart arayüzle sunar, ajan bu araçları doğrudan çağırır (gerçek bir MCP istemcisiyle uçtan uca denenmedi).",
    "n8n akışında yalnızca ENGELLE ve ONAY_BEKLIYOR dalları canlı denendi, diğer dallar testlerle doğrulandı.",
    "Düzeltmeler ilk koşu hatalarının kategorisine bakılarak yapıldı; temiz sayım ilk koşudur.",
    "Onaydan sonra gerçek sisteme yazılmaz; uygulanan işlemler kayıt olarak tutulur.",
    "Süre, makinenin o anki yüküne bağlıdır; küçük kümelerde tek talep yüzdeyi belirgin değiştirir.",
]


def akis_html(adimlar=ADIMLAR) -> str:
    """Model adımları (teal) ile kod adımları (gri) farklı renkte akış şeması; saf HTML/CSS."""
    parca = []
    for i, (ad, tur, aciklama) in enumerate(adimlar):
        sinif = "model" if tur.startswith("model") else "kod"
        etiket = "MODEL" if sinif == "model" else "KOD"
        parca.append(f'<div class="dugum {sinif}"><b>{S.kac(ad)}</b><span class="etiket {sinif}">{etiket}</span>'
                     f'<div style="font-size:.8rem;margin-top:.25rem">{S.kac(aciklama)}</div></div>')
        if i < len(adimlar) - 1:
            parca.append('<div class="ok">→</div>')
    return '<div class="akis">' + "".join(parca) + "</div>"


# Dış katmanlar: her bileşen YALNIZ BİR KEZ. (kimlik, etiket, tür, tek satırlık rol)
# tür: otomasyon (lacivert) · kod (gri) · model (mavi-yeşil: model + kod) · sentetik (açık sarı, kesikli) · insan (beyaz)
DIS_BILESENLER = [
    ("destek", "Destek sistemi", "sentetik", "Sentetik simülatör: sabit Demo 1 ve Demo 2 taleplerini verir."),
    ("n8n", "n8n", "otomasyon", "Talebi alır, ajan servisini çağırır, sonucu yoklar ve bildirime yönlendirir; karar ve onay vermez."),
    ("servis", "Ajan servisi (FastAPI)", "kod", "POST /talep (asenkron), GET /durum, POST /onay; talepleri sırayla işler."),
    ("ajan", "Ajan (LangGraph)", "model", "Karar akışı: model adımları ve deterministik hesaplar; insan onayını bekler."),
    ("ui", "Streamlit arayüzü", "kod", "İzleme ve insan onayı; ajanı doğrudan çağırır."),
    ("araclar", "Hesap araçları (sla_araclari)", "kod", "Müşteri arama, son tarih, risk ve kredi hesapları."),
    ("mcp", "MCP sunucusu", "kod", "Dört deterministik hesap aracını dış istemciye açar (LLM adımları açılmaz)."),
    ("bildirim", "Bildirim (simülatör)", "sentetik", "Gerçek e-posta/Slack değil; bildirimler.jsonl dosyası, Bildirimler sekmesinde görünür."),
    ("insan", "İnsan onayı (yönetici)", "insan", "Onayla/Reddet kararını yalnızca insan verir."),
]
DIS_BAGLANTILAR = [
    ("destek", "n8n", ""), ("n8n", "servis", ""), ("servis", "ajan", ""), ("ui", "ajan", ""),
    ("ajan", "araclar", ""), ("mcp", "araclar", ""), ("n8n", "bildirim", ""),
    ("insan", "ui", "Onayla / Reddet"), ("insan", "servis", "POST /onay (n8n onay vermez)"),
]
_DOT_STIL = {
    "otomasyon": 'fillcolor="#0f1f3d", fontcolor="white", color="#0f1f3d"',
    "kod": 'fillcolor="#eef1f6", fontcolor="#2a3750", color="#9aa8bd"',
    "model": 'fillcolor="#d9f0f5", fontcolor="#0b4254", color="#0e7490", penwidth=2',
    "sentetik": 'fillcolor="#fff3cd", fontcolor="#5b4300", color="#d99a00", style="filled,dashed", penwidth=2',
    "insan": 'fillcolor="#ffffff", fontcolor="#14213d", color="#14213d"',
}


def dis_katman_dot() -> str:
    """Tek temiz Graphviz DOT şeması (st.graphviz_chart): yukarıdan aşağı, her bileşen bir kez."""
    satir = ['digraph G {', 'rankdir=TB; bgcolor="transparent"; nodesep=0.5; ranksep=0.55;',
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=14, margin="0.2,0.1"];',
             'edge [color="#5b6b86", fontname="Helvetica", fontsize=12, arrowsize=0.8];']
    for kimlik, etiket, tur, _rol in DIS_BILESENLER:
        ek = ", style=\"rounded,filled\"" if tur != "sentetik" else ""
        satir.append(f'{kimlik} [label="{etiket}", {_DOT_STIL[tur]}{ek}];')
    for a, b_, e in DIS_BAGLANTILAR:
        satir.append(f'{a} -> {b_}' + (f' [label="{e}", style=dashed]' if a == "insan" else "") + ";")
    satir.append("}")
    return "\n".join(satir)


def dis_katman_sema():
    """Dış katmanlar şeması: Graphviz; çalışmazsa sabit sütunlu HTML ızgarası."""
    try:
        st.graphviz_chart(dis_katman_dot(), width="stretch")
    except Exception:  # noqa: BLE001
        S.html('<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px">' + "".join(
            f'<div class="dugum {"sentetik" if t == "sentetik" else "kod"}"><b>{S.kac(e)}</b></div>'
            for _k, e, t, _r in DIS_BILESENLER) + "</div>")


def mimari_sekmesi():
    st.subheader("Akış: hangi adım model, hangisi kod")
    S.html('<div class="lejant"><span><span class="etiket model">MODEL</span> dil modeli çağrısı</span>'
           '<span><span class="etiket kod">KOD</span> deterministik kod</span></div>')
    S.html(akis_html())
    st.markdown("**Çıkışlar:** " + " ".join(S.davranis_rozeti(d) for d in
                                           ("ENGELLE", "BILMIYORUM", "SORU_SOR", "ONCELIK_BELIRLENEMEDI", "HESAPLA")),
                unsafe_allow_html=True)
    st.subheader("Dış katmanlar")
    st.caption("Renkler: lacivert = otomasyon · mavi-yeşil = model + kod · gri = kod · sarı kesikli = sentetik (gerçek sisteme bağlı değil).")
    dis_katman_sema()
    st.info("Onayı yalnızca insan verir; n8n onay vermez.")
    with st.expander("Ayrıntı: bileşenlerin rolleri"):
        for _k, e, _t, rol in DIS_BILESENLER:
            st.markdown(f"- **{e}:** {rol}")
        st.caption("n8n yalnızca ajan servisini çağırır ve sonucu bildirime yönlendirir. "
                   "Onay yalnızca insandır (Streamlit arayüzü ya da elle POST /onay).")
    st.subheader("Karar sırası özeti")
    st.markdown("1. Komut içeren talep **işlenmez** (ENGELLE).\n"
                "2. Müşteri bulunamazsa ya da belirsizse **sorulur**.\n"
                "3. Öncelik kaynaklı önerilir; belirsizse önce müşteriye sorulur, yine belirsizse yöneticiye iletilir.\n"
                "4. Süre ve kredi hesapları **kodla** yapılır.\n"
                "5. Onay gerekiyorsa **insan karar verir**.")
    with st.expander("Ayrıntı"):
        st.markdown("- Kayıtsız firma, kapsam dışı ya da dokümanda olmayan konu için **\"Dokümanda bilgi bulunmamaktadır.\"** yanıtı verilir.\n"
                    "- Bilgi yetersizse müşteriye bir kez sorulur; yine belirsizse yöneticiye iletilir.\n"
                    "- Süre ve kredi hesapları modelden istenmez.\n"
                    "- Reddetmek için gerekçe zorunludur.")
    st.subheader("Sınırlamalar")
    for x in SINIRLAMALAR:
        st.markdown(f"- {x}")
    with st.expander("Ayrıntı"):
        for x in SINIRLAMA_AYRINTI:
            st.markdown(f"- {x}")
        st.caption(f"Model: {config.CHAT_MODEL} (think kapalı) · Embedding: {config.EMBED_MODEL}")


# ------------------------------------------------------------------ Bildirimler
def _bildirim_karti(b: dict, anahtar: str, servis_acik: bool):
    kanal_ad, kanal_sinif = BL.KANALLAR.get(b.get("kanal"), (b.get("kanal") or "bilinmeyen kanal", "yok"))
    onc_ad, onc_sinif = BL.ONCELIK.get(b.get("oncelik"), (b.get("oncelik") or "—", "yok"))
    S.html('<div class="bildirim">'
           f'<div class="ust">{S.rozet("Öncelik: " + str(onc_ad), onc_sinif)}'
           f'<span class="teknik zaman-sag">{S.kac(BL.zaman_yaz(b.get("zaman")))}</span></div>'
           f'<div class="bb">{S.kac(b.get("baslik", ""))}</div><div class="bm">{S.kac(b.get("mesaj", ""))}</div>'
           f'<div class="silik">{S.kac(kanal_ad)} · kanal: {S.kac(b.get("kanal", "—"))} · talep_id: {S.kac(b.get("talep_id") or "—")}</div></div>')
    if BL.onay_karti_mi(b):
        _bildirim_onay(b, anahtar, servis_acik)


def _bildirim_onay(b: dict, anahtar: str, servis_acik: bool):
    ss = st.session_state
    tid = b["talep_id"]
    karar = ss.setdefault("bildirim_kararlari", {}).get(tid)
    durum = None
    if karar is None and servis_acik:
        try:
            durum = BL.servis_durum(tid)
        except Exception as e:  # noqa: BLE001
            st.warning(BL.hata_metni(e))
            durum = {"durum": "BILINMIYOR"}
        if durum.get("onay_sonucu"):
            karar = durum
    if karar is not None:
        _karar_karti(karar.get("onay_sonucu") or {})
        st.caption("Bu talep karara bağlandı; düğmeler pasif.")
        return
    if not servis_acik:
        st.caption("Onay için ajan servisi gerekir.")          # gerekçe kutusu ve düğmeler gösterilmez
        return
    bekliyor = (durum or {}).get("durum") == "ONAY_BEKLIYOR"
    if not bekliyor:
        st.info(f"Talep şu an onay beklemiyor (durum: {(durum or {}).get('durum')}); düğmeler pasif.")
    if "n8n onay vermez" not in f"{b.get('baslik', '')} {b.get('mesaj', '')}":     # kart metninde varsa tekrarlama
        st.caption("Karar yalnızca yöneticidedir; n8n onay vermez.")
    gerekce = st.text_input("Gerekçe (Reddet için zorunlu)", key=f"bgerekce_{anahtar}", disabled=not bekliyor)
    c1, c2 = dugme_cifti(f"bildirim_{anahtar}")
    verilen = "onayla" if c1.button("Onayla", key=f"bonay_{anahtar}", type="primary", disabled=not bekliyor) else \
        ("reddet" if c2.button("Reddet", key=f"bred_{anahtar}", disabled=not bekliyor) else None)
    if verilen:
        if verilen == "reddet" and not gerekce.strip():
            st.error("Reddetmek için gerekçe zorunludur; istek gönderilmedi.")
            return
        try:
            yanit = BL.onay_gonder(tid, verilen, gerekce)
        except Exception as e:  # noqa: BLE001  (servis kapalı, 409, 404 ... : çökme yok)
            st.error(BL.hata_metni(e))
            return
        ss.bildirim_kararlari[tid] = yanit
        st.rerun()


def bildirimler_sekmesi():
    st.markdown("**Sentetik** bildirimler; gerçek e-posta/Slack'e gönderilmez.")
    with st.expander("Teknik bilgi"):
        st.caption("Kaynak: dis_sistem/bildirimler.jsonl (ajan servisi ve n8n akışı yazar).")
    st.button("Yenile", key="bildirim_yenile")                      # tıklama sayfayı yeniden çalıştırır
    liste = BL.oku()
    if not liste:
        st.info("Henüz bildirim yok.")
        return
    gosterilen = liste[:30]
    servis_acik = BL.servis_calisiyor() if any(BL.onay_karti_mi(b) for b in gosterilen) else True
    st.caption(f"{len(liste)} bildirim" + (f" (en yeni {len(gosterilen)} gösteriliyor)" if len(liste) > len(gosterilen) else "") + " · yeniden eskiye")
    for i, b in enumerate(gosterilen):
        _bildirim_karti(b, f"{i}_{b.get('talep_id')}_{b.get('zaman')}", servis_acik)


# ------------------------------------------------------------------ Kayıtlı çalıştırmalar
def kayitli_sekmesi():
    st.markdown("Gerçek modelde **önceden** çalıştırılmış demo sonuçları (yedek).")
    try:
        kayitlar = kayitli.yukle()
    except Exception as e:  # noqa: BLE001
        st.error(f"Kayıtlı sonuçlar okunamadı: {type(e).__name__}: {e}")
        return
    if not kayitlar:
        st.warning("Kayıtlı sonuç bulunamadı (demo/kayitli_sonuclar.json). `python demo/kayit_al.py` ile oluşturulur.")
        return
    ad = st.selectbox("Kayıt", [k["ad"] for k in kayitlar], key="kayit_sec")
    k = next(x for x in kayitlar if x["ad"] == ad)
    st.markdown(f"**Talep:** {k['metin']}")
    def kayit_onay():
        with st.container(key="kayit_onay"):
            st.caption("Kayıt, onay verilemez: kayıtta yönetici kararı yoktur; canlı onay paneli Talep İşle sekmesindedir.")
            c1, c2 = dugme_cifti("kayit")
            c1.button("Onayla", key="kayit_onayla", disabled=True)
            c2.button("Reddet", key="kayit_reddet", disabled=True)
    sonuc_goster({**k["sonuc"], "talep": k["metin"], "toplam_sn": k["sonuc"].get("toplam_sn")}, kayit=k,
                 onay=kayit_onay if k["sonuc"]["durum"] == "BEKLEMEDE" else None)


def sayfa():
    st.set_page_config(page_title="SLA Operasyon Paneli", layout="wide")
    S.uygula()
    _durum_baslat()
    yan_cubuk()
    st.title("SLA Uyum ve Eskalasyon Ajanı")
    st.caption("Poyraz Bulut Yazılım A.Ş. (kurgusal) — prototip. Veri sentetiktir.")
    t1, t2, t3, tb, t4 = st.tabs(SEKMELER)
    with t1:
        talep_sekmesi()
    with t2:
        olcum_sekmesi()
    with t3:
        mimari_sekmesi()
    with tb:
        bildirimler_sekmesi()
    with t4:
        kayitli_sekmesi()
    bekleyen_sayisi_yaz()
