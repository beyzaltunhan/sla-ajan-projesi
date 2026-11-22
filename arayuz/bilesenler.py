"""Streamlit bileşenleri. Görsel stil 7B'de eklenecek: tüm çıktı bu dosyadaki küçük fonksiyonlardan geçer."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime

import streamlit as st

import ajan
import config
from arayuz import bicimle as B
from arayuz import model, olcum

ONAY_YOK = "Bu talep için onay gerekmiyor."


# ------------------------------------------------------------------ yardımcılar
def _durum_baslat():
    ss = st.session_state
    ss.setdefault("sayac", 0)
    ss.setdefault("son", None)             # son işlenen talebin sonuç sözlüğü (+ talep metni)
    ss.setdefault("onay_hatasi", {})       # thread_id -> ajanın verdiği hata/engel mesajı
    ss.setdefault("onaylananlar", {})      # thread_id -> onay_ver sonucu
    ss.setdefault("isinma", None)


def _birlestir(d, t) -> datetime:
    return datetime.combine(d, t)


# ------------------------------------------------------------------ ısıtma (yan çubuk)
def isinma_paneli():
    ss = st.session_state
    st.sidebar.subheader("Model durumu")
    if ss.isinma is None:
        with st.sidebar, st.spinner("Modeller ısıtılıyor…"):
            ss.isinma = model.isit()
    if st.sidebar.button("Modeli yeniden ısıt"):
        with st.sidebar, st.spinner("Modeller ısıtılıyor…"):
            ss.isinma = model.isit()
    i = ss.isinma
    if i["durum"] == "hazir":
        st.sidebar.success(f"{i['ayrinti']} ({B.sure_yaz(i['sure_sn'])})")
    else:
        st.sidebar.error(i["ayrinti"])
    st.sidebar.caption("Model: CPU üzerinde çalışır; bir talep yaklaşık 15–100 sn sürebilir.")


# ------------------------------------------------------------------ Talep İşle
def _ornek_sec():
    ss = st.session_state
    ad = ss.get("ornek_ad")
    simdi = _birlestir(ss.simdi_d, ss.simdi_t)
    if ad and ad != "—":
        o = B.ornekler(simdi)[ad]
        ss.talep_metni = o["metin"]
        ss.kayit_d, ss.kayit_t = o["kayit_zamani"].date(), o["kayit_zamani"].time().replace(microsecond=0, second=0)


def _simdiyi_guncelle():
    n = datetime.now().replace(microsecond=0, second=0)
    st.session_state.simdi_d, st.session_state.simdi_t = n.date(), n.time()


def talep_formu() -> tuple[str, datetime, datetime] | None:
    ss = st.session_state
    if "simdi_d" not in ss:
        _simdiyi_guncelle()
        ss.kayit_d, ss.kayit_t = ss.simdi_d, ss.simdi_t
    ss.setdefault("talep_metni", "")
    st.selectbox("Hazır örnek", ["—"] + list(B.ornekler(datetime.now())), key="ornek_ad", on_change=_ornek_sec)
    st.text_area("Talep metni", key="talep_metni", height=130)
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
    if st.button("İşle", type="primary"):
        if not ss.talep_metni.strip():
            st.warning("Lütfen bir talep metni yazın.")
            return None
        return ss.talep_metni, _birlestir(ss.kayit_d, ss.kayit_t), _birlestir(ss.simdi_d, ss.simdi_t)
    return None


def isle_canli(metin: str, kayit: datetime, simdi: datetime):
    """Ajanı ayrı thread'de çalıştırır; ana thread checkpointer'dan adım durumunu okuyup canlı gösterir."""
    ss = st.session_state
    ss.sayac += 1
    tid = B.yeni_thread_id(ss.sayac)
    g = ajan.graf()                                    # ana thread'de oluştur (thread'de yarış olmasın)
    cfg = {"configurable": {"thread_id": tid}}
    kutu: dict = {}

    def hedef():
        try:
            kutu["sonuc"] = ajan.talep_isle(metin, kayit, simdi, tid)
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
            st.markdown(f"**İşleniyor…** geçen süre {B.sure_yaz(time.perf_counter() - t0)}")
            st.markdown(B.adim_metni(satirlar))
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


def sonuc_goster(s: dict):
    """Bir talebin sonucu: adım tablosu, durum kartı veya HESAPLA ayrıntıları, ham JSON."""
    c = s.get("cikti")
    st.markdown(f"#### Sonuç — durum: `{s['durum']}`  ·  toplam {B.sure_yaz(s.get('toplam_sn'))}")
    with st.expander("Adımlar ve süreler", expanded=True):
        st.markdown(B.adim_metni(B.adim_satirlari(s.get("adim_sureleri", []))))
    kart = B.durum_karti(c, s.get("hata"), (st.session_state.get("isinma") or {}).get("durum") == "hata")
    if kart:
        (st.error if kart[0] == "hata" else st.info)(kart[1])
        if c and c.get("davranis") and c.get("musteri"):
            st.caption(f"Bulunan müşteri: {c['musteri']}")
    else:
        _hesapla_goster(c)
    if c:
        with st.expander("Ham JSON (KararCiktisi)"):
            st.json(c)
    if s.get("onay_sonucu"):
        _onay_sonrasi_goster(s)


def _hesapla_goster(c: dict):
    st.markdown(f"**Davranış:** {c['davranis']}")
    a, b, d = st.columns(3)
    a.metric("Müşteri", c["musteri"])
    b.metric("Paket", c["paket"])
    d.metric("Öncelik", c["oncelik"])
    e, f, g = st.columns(3)
    e.metric("İlk yanıt son tarihi", B.tarih_yaz(c["son_tarih"]))
    f.metric("Kalan süre", B.kalan_sure_yaz(c.get("kalan_dk")))
    g.metric("Risk", c["risk"])
    k = c.get("kredi") or {}
    st.markdown(f"**Kredi:** %{k.get('yuzde', 0):g} ({k.get('tutar', 0):g} TL) — {k.get('neden', '—')}")
    st.markdown(f"**Onay:** {'gerekli' if c['onay_gerekli'] else 'gerekmiyor'}"
                + (f" — nedenler: {B.onay_nedenleri_yaz(c['onay_nedenleri'])}" if c["onay_gerekli"] else ""))
    st.markdown("**Gerekçe / özet:** " + c["mesaj"])
    st.markdown("**Kaynak maddeler**")
    for k in B.kaynak_listesi(c["kaynaklar"]):
        st.markdown(f"- **{k['dokuman']}, Madde {k['madde']}** — {k['metin']}")


def _onay_sonrasi_goster(s: dict):
    o = s["onay_sonucu"]
    st.success(B.onay_sonucu_ozet(o))
    islemler = B.uygulanan_islemler(o)
    st.markdown("**Onaydan sonra yapılan işler**")
    if islemler:
        for i in islemler:
            st.markdown(f"- {i}")
    else:
        st.markdown("- Ajan hiçbir işlem uygulamadı (reddedildi ya da uygulanacak işlem yok).")
    st.caption("Onay paketinin durum alanı BEKLEMEDE kalır; sonuç `onay_sonucu` alanındadır (karar/uygulandı).")


# ------------------------------------------------------------------ Onay
def onay_paneli(tid: str, paket: dict, anahtar: str):
    """Onay paketi özeti + Onayla/Reddet. Reddet için gerekçe zorunludur (kuralı ajan uygular; boşsa ajanın hatası gösterilir)."""
    ss = st.session_state
    st.markdown(f"**Onay bekleyen paket** (`{tid}`)")
    st.markdown(f"{paket['musteri']} ({paket['paket']}) · öncelik {paket['oncelik']} · risk {paket['risk']} · "
                f"son tarih {B.tarih_yaz(paket['son_tarih'])} · kalan {B.kalan_sure_yaz(paket.get('kalan_dk'))}")
    k = paket.get("kredi") or {}
    st.markdown(f"Kredi önerisi: %{k.get('yuzde', 0):g} ({k.get('tutar', 0):g} TL) · onay nedenleri: "
                f"{B.onay_nedenleri_yaz(paket['onay_nedenleri'])}")
    st.caption(paket["mesaj"])
    gerekce = st.text_input("Gerekçe (Reddet için zorunlu)", key=f"gerekce_{anahtar}")
    c1, c2 = st.columns(2)
    karar = "ONAYLA" if c1.button("Onayla", key=f"onayla_{anahtar}") else ("REDDET" if c2.button("Reddet", key=f"reddet_{anahtar}") else None)
    if karar:
        try:
            r = ajan.onay_ver(tid, karar, gerekce)
        except ValueError as e:                        # ajanın kendi engeli (ör. gerekçesiz red) olduğu gibi gösterilir
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
        st.divider()
        st.markdown(f"**Talep:** {ss.son['talep']}")
        sonuc_goster(ss.son)
        if ss.son["durum"] == "BEKLEMEDE" and ss.son.get("cikti"):
            st.divider()
            onay_paneli(ss.son["thread_id"], ss.son["cikti"], "son")
    st.divider()
    bekleyen_onaylar_paneli(haric=ss.son["thread_id"] if ss.son and ss.son["durum"] == "BEKLEMEDE" else None)


# ------------------------------------------------------------------ Ölçüm Sonuçları
def olcum_sekmesi():
    st.info(olcum.NOT)
    try:
        r = olcum.karsilastir()
    except Exception as e:  # noqa: BLE001
        st.error(f"Ölçüm dosyaları okunamadı: {type(e).__name__}: {e}")
        return
    ilk, sonra = r["ilk"], r["sonra"]
    st.caption(f"İlk koşu: commit {ilk['meta']['commit'][:8]}, {ilk['meta']['tarih']} · Düzeltme sonrası: commit "
               f"{sonra['meta']['commit'][:8]}, {sonra['meta']['tarih']} · model {sonra['meta']['chat_model']}")
    st.subheader("Doğruluk: ilk koşu → düzeltme sonrası (kaç/N)")
    satirlar = []
    for ad in ("Ana set", "Zor set", "Bağımsız 15"):
        satirlar.append({"Küme": ad, "Tam doğru": f"{olcum.kn(*ilk['tam'][ad])} → {olcum.kn(*sonra['tam'][ad])}",
                         "Davranış doğru": f"{olcum.kn(*ilk['dav'][ad])} → {olcum.kn(*sonra['dav'][ad])}"})
    st.table(satirlar)
    a, b, c = st.columns(3)
    a.metric("Onay yakalama", f"{olcum.kn(*ilk['onay_yakalama'])} → {olcum.kn(*sonra['onay_yakalama'])}")
    b.metric("Yanlış alarm", f"{olcum.kn(*ilk['yanlis_alarm'])} → {olcum.kn(*sonra['yanlis_alarm'])}")
    c.metric("Ortalama gecikme (talep başı)", f"{ilk['gecikme_ort']} → {sonra['gecikme_ort']} sn")
    st.caption(f"Kesinti şüpheli talepler hariç ortalama: {ilk['gecikme_ort_supheli_haric']} → {sonra['gecikme_ort_supheli_haric']} sn "
               f"(işaretlenenler: ilk {', '.join(ilk['supheli']) or '—'}; sonra {', '.join(sonra['supheli']) or '—'}). "
               "Süre, CPU'da çalışan küçük modelin ve o anki makine yükünün ürünüdür.")
    st.subheader("Hata türleri (hatalı talep sayısı, adım bazında)")
    satir = []
    for ad in ("Ana set", "Zor set"):
        for adim in sorted(set(ilk["hata_turleri"][ad]) | set(sonra["hata_turleri"][ad])):
            satir.append({"Küme": ad, "Hata adımı": adim, "İlk koşu": ilk["hata_turleri"][ad].get(adim, 0),
                          "Düzeltme sonrası": sonra["hata_turleri"][ad].get(adim, 0)})
    st.table(satir)
    st.subheader("Talep bazında değişim")
    st.markdown(f"- **Düzeldi ({len(r['duzeldi'])}):** {', '.join(r['duzeldi']) or '—'}\n"
                f"- **Bozuldu — yeni regresyon ({len(r['bozuldu'])}):** {', '.join(r['bozuldu']) or '—'}\n"
                f"- **Hâlâ hatalı ({len(r['hala_hatali'])}):** {', '.join(r['hala_hatali']) or '—'}\n"
                f"- **İki koşuda da doğru:** {r['degismedi_dogru']}")
    for baslik, yol in (("İlk koşu raporu (dondurulmuş)", olcum.ILK_RAPOR), ("Düzeltme sonrası rapor", olcum.SONRA_RAPOR)):
        with st.expander(baslik):
            md = olcum.rapor_oku(yol)
            st.markdown(md) if md else st.warning(f"{yol.name} bulunamadı.")


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
    "Küçük model (qwen3.5:4b) CPU'da çalışır; talep başına yaklaşık 15–100 sn sürer.",
    "Düzeltme sonrası sayılar tam bağımsız değildir (düzeltmeler ilk koşu hatalarının kategorisine bakılarak yapıldı).",
    "Onaydan sonraki işlemler prototipte yalnızca kayıt olarak tutulur; gerçek sisteme yazılmaz.",
    "Dış sistem / n8n entegrasyonu yoktur (gelecek çalışma).",
    "Test seti küçüktür (59 talep); sayılar kaba bir göstergedir.",
]


def mimari_sekmesi():
    st.subheader("Adımlar (hangisi model, hangisi kod)")
    st.table([{"Adım": a, "Tür": t, "Açıklama": x} for a, t, x in ADIMLAR])
    st.subheader("Karar sırası özeti")
    st.markdown("1. Komut içeren talep **işlenmez** (ENGELLE).\n"
                "2. Müşteri bulunamazsa/belirsizse **sorulur**; kayıtsız firma, kapsam dışı ya da dokümanda olmayan konu için "
                "**\"Dokümanda bilgi bulunmamaktadır.\"**\n"
                "3. Öncelik kaynaklı önerilir; bilgi yetersizse sorulur, yine belirsizse yöneticiye iletilir.\n"
                "4. Süre ve kredi hesapları **kodla** yapılır, modelden istenmez.\n"
                "5. Onay gerekiyorsa **insan karar verir**; reddetmek için gerekçe zorunludur.")
    st.subheader("Sınırlamalar")
    for x in SINIRLAMALAR:
        st.markdown(f"- {x}")
    st.caption(f"Model: {config.CHAT_MODEL} (think kapalı) · Embedding: {config.EMBED_MODEL}")


def sayfa():
    st.set_page_config(page_title="SLA Uyum ve Eskalasyon Ajanı", layout="wide")
    _durum_baslat()
    st.title("SLA Uyum ve Eskalasyon Ajanı")
    st.caption("Poyraz Bulut Yazılım A.Ş. (kurgusal) — prototip. Veri sentetiktir.")
    isinma_paneli()
    t1, t2, t3 = st.tabs(["Talep İşle", "Ölçüm Sonuçları", "Mimari ve Sınırlamalar"])
    with t1:
        talep_sekmesi()
    with t2:
        olcum_sekmesi()
    with t3:
        mimari_sekmesi()
