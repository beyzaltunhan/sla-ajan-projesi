"""LangGraph ajanı: tasarim/karar_sirasi.md Bölüm 3-6'nın düğüm ve koşullu kenarlara birebir çevirisi.

Akış:  1a müşteri arama (kod) -> 1b talimat (LLM) -> [ENGELLE] -> 1c talep türü (LLM) -> ön yönlendirme (kod)
       -> [BILMIYORUM / SORU_SOR] | 1d firma adı yedeği (LLM, yalnız 1a BULUNAMADI) -> ön yönlendirme
       -> Adım 4 öncelik (RAG + LLM) -> öncelik yönlendirme (kod) -> [SORU_SOR / ONCELIK_BELIRLENEMEDI]
       -> hesap araçları -> onay kapısı -> paket doğrulama (Pydantic) -> [insan onayı: interrupt] -> uygulama.
LLM çağrıları tembeldir: yalnızca ilgili yola girilirse çalışır.

API: talep_isle(talep_metni, kayit_zamani, simdi, thread_id, soru_soruldu=False) ve onay_ver(thread_id, karar, gerekce).
Her thread_id BİR talep içindir (tekrar kullanılamaz). Kayıt zamanı ve şimdiki an dışarıdan verilir.
"""
from __future__ import annotations

import json
import logging
import operator
import sqlite3
import time
from datetime import datetime
from functools import wraps
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import ValidationError

import atif
import config
import llm_adimlari as L
import oncelik_onerisi as O
import sla_araclari as s
from schemas.onay_paketi import BILMIYORUM_YANITI, KararCiktisi

log = logging.getLogger("ajan")
STRATEJI = "getirilen+cekirdek"
MESAJLAR = {
    "talimat_iceriyor": "Talep metni sistemi yönlendirmeye çalışan bir talimat içerdiği için otomatik işlenmedi; "
                        "insan incelemesine iletildi.",
    "musteri_adi_eksik": "Talebinizi değerlendirebilmek için lütfen müşteri (firma) adınızı yazar mısınız?",
    "musteri_belirsiz": "Yazdığınız ad birden fazla kayıtlı müşteriyle eşleşiyor; hangi müşteri için yazıyorsunuz?",
    "oncelik_belirsiz": "Hizmetin tamamı mı yoksa yalnızca bir bölümü mü etkileniyor ve çalışan bir geçici çözüm var mı?",
    "oncelik_belirlenemedi": "Öncelik belirlenemedi; talep \"öncelik belirlenemedi\" notuyla destek yöneticisine iletildi.",
    "sema_hatasi": "Talep işlenemedi; yöneticiye iletildi.",
}


# ------------------------------------------------------------------ durum
class Durum(TypedDict, total=False):
    # girdiler
    talep_metni: str
    kayit_zamani: str            # ISO; sistemden gelir
    simdi: str                   # ISO; sistemden gelir
    soru_soruldu: bool
    # ara sonuçlar
    musteri_durum: str           # TEK | BELIRSIZ | BULUNAMADI (1a)
    musteri: Optional[dict]
    talimat: bool                # 1b
    talep_turu: str              # 1c
    firma_1d_yapildi: bool
    firma_adi: Optional[str]     # 1d (metinde birebir doğrulanmış)
    yon: str
    neden: Optional[str]
    oncelik: str
    oncelik_maddeleri: list
    etki: str
    hesap: dict
    # çıktı
    cikti: dict                  # KararCiktisi (json)
    hata: dict
    onay_sonucu: dict
    adim_sureleri: Annotated[list, operator.add]


# ------------------------------------------------------------- sarmalayıcı
def tracked(ad: str, tur: str):
    """Düğümün adını, süresini (tur: "llm" | "kod") ve değiştirdiği alanları loglar; state'e adim_sureleri ekler."""
    def deco(fn):
        @wraps(fn)
        def sarmal(state):
            t0 = time.perf_counter()
            try:
                cikis = dict(fn(state))
            except GraphBubbleUp:               # interrupt vb. yukarı geçmeli
                raise
            except Exception as e:              # beklenmeyen hata -> hata düğümü (ISLENEMEDI)
                cikis = {"hata": {"adim": ad, "mesaj": f"{type(e).__name__}: {e}"}}
            kayit = {"adim": ad, "tur": tur, "sure_sn": round(time.perf_counter() - t0, 4),
                     "degisen": sorted(cikis)}
            log.info(json.dumps(kayit, ensure_ascii=False))
            cikis["adim_sureleri"] = [kayit]
            return cikis
        return sarmal
    return deco


def _dt(v) -> datetime:
    return v if isinstance(v, datetime) else datetime.fromisoformat(v)


def _musteri_adi(state) -> Optional[str]:
    if state.get("musteri"):
        return state["musteri"]["ad"]
    return state.get("firma_adi")


def _kaynaklar(cift: list[tuple[str, str]]) -> list[dict]:
    return [{"dokuman": d, "madde": m} for d, m in atif.tekil(cift)]


def _dogrula(**alanlar) -> dict:
    return KararCiktisi(**alanlar).model_dump(mode="json")


# ---------------------------------------------------------------- düğümler
@tracked("1a_musteri_arama", "kod")
def n_musteri_arama(state):
    durum, kayit = s.musteri_metinde_ara(state["talep_metni"], _musteriler())
    return {"musteri_durum": durum, "musteri": kayit}


def _musteriler() -> list[dict]:
    return json.loads((config.DATA_DIR / "musteriler.json").read_text(encoding="utf-8"))["musteriler"]


def _llm_sonucu(sonuc, adim) -> dict:
    if sonuc.durum == "ISLENEMEDI":
        return {"hata": {"adim": adim, "mesaj": "LLM çıktısı şemaya uymadı (tek yeniden deneme sonrası)"}}
    return {}


@tracked("1b_talimat", "llm")
def n_talimat(state):
    r = L.talimat_tespit(state["talep_metni"])
    return _llm_sonucu(r, "1b") or {"talimat": bool(r.deger)}


@tracked("1c_talep_turu", "llm")
def n_talep_turu(state):
    r = L.talep_turu_bul(state["talep_metni"])
    return _llm_sonucu(r, "1c") or {"talep_turu": r.deger}


@tracked("1d_firma_adi", "llm")
def n_firma_adi(state):
    r = L.firma_adi_bul(state["talep_metni"])        # metinde birebir geçmeyen ad burada None olur (kod)
    return _llm_sonucu(r, "1d") or {"firma_adi": r.deger, "firma_1d_yapildi": True}


@tracked("3_on_yonlendirme", "kod")
def n_on_yonlendirme(state):
    """Bölüm 4 tablosu (1. satır ENGELLE, 1b'den sonra verilir)."""
    if state["talep_turu"] in ("kapsam_disi", "dokumanda_olmayan"):                     # sıra 2
        return {"yon": "bilmiyorum",
                "neden": "kapsam_disi" if state["talep_turu"] == "kapsam_disi" else "dokumanda_yok"}
    d = state["musteri_durum"]
    if d == "BELIRSIZ":                                                                  # sıra 4
        return {"yon": "soru_sor", "neden": "musteri_belirsiz"}
    if d == "BULUNAMADI":
        if not state.get("firma_1d_yapildi"):
            return {"yon": "firma_1d"}                                                   # tembel 1d
        if state.get("firma_adi"):                                                       # sıra 5
            return {"yon": "bilmiyorum", "neden": "musteri_kayitsiz"}
        return {"yon": "soru_sor", "neden": "musteri_adi_eksik"}                         # sıra 3
    if state["musteri"]["ozel_anlasma"]:                                                 # sıra 6
        return {"yon": "bilmiyorum", "neden": "ozel_anlasma"}
    return {"yon": "oncelik"}                                                            # sıra 7


@tracked("4_oncelik_rag_llm", "llm")
def n_oncelik(state):
    parcalar = O.baglam_parcalari(STRATEJI, talep=state["talep_metni"])    # RAG: dokuman=02, k=8 + sabit çekirdek
    r = O.oncelik_oner(state["talep_metni"], parcalar)
    if r.durum == "ISLENEMEDI":
        return {"hata": {"adim": "4", "mesaj": "Öncelik çıktısı şemaya uymadı (tek yeniden deneme sonrası)"}}
    return {"oncelik": r.oncelik, "oncelik_maddeleri": r.maddeler, "etki": r.etki}


@tracked("5_oncelik_yonlendirme", "kod")
def n_oncelik_yonlendirme(state):
    if state["oncelik"] in ("P1", "P2", "P3", "P4"):
        return {"yon": "hesap"}
    if not state.get("soru_soruldu"):
        return {"yon": "soru_sor", "neden": "oncelik_belirsiz"}
    return {"yon": "oncelik_belirlenemedi", "neden": "oncelik_belirlenemedi"}


@tracked("6_hesap_araclari", "kod")
def n_hesap(state):
    m, oncelik = state["musteri"], state["oncelik"]
    olus, simdi = _dt(state["kayit_zamani"]), _dt(state["simdi"])
    sd = s.son_tarih_hesapla(olus, m["paket"], oncelik)
    rk = s.risk_degerlendir(sd["son_tarih"], simdi, sd["takvim"], sd["sure_dk"])
    kr = s.kredi_hesapla(m["paket"], oncelik, rk["risk"] == "IHLAL", m["aylik_ucret"], m["bu_ay_kredi_yuzdesi"])
    return {"hesap": {
        "son_tarih": sd["son_tarih"].isoformat(), "takvim": sd["takvim"], "risk": rk["risk"], "kalan_dk": rk["kalan_dk"],
        "kredi": kr,
        "atif": atif.son_tarih_atfi(olus, sd) + atif.risk_atfi(rk["risk"]) + atif.kredi_atfi(kr)}}


@tracked("7_onay_kapisi", "kod")
def n_onay_kapisi(state):
    h = state["hesap"]
    onay, nedenler = s.onay_gerekli(state["oncelik"], h["risk"], h["kredi"]["yuzde"])
    atif_listesi = h["atif"] + atif.onay_atfi(onay, nedenler)
    return {"hesap": {**h, "onay": onay, "onay_nedenleri": nedenler, "atif": atif_listesi}}


@tracked("8_paket_dogrulama", "kod")
def n_paket_dogrula(state):
    """HESAPLA çıktısı Pydantic ile doğrulanır; şemaya uymayan paket yöneticiye gitmez (§3 adım 8)."""
    h, m = state["hesap"], state["musteri"]
    kaynak02 = [(atif.D02, x) for x in state.get("oncelik_maddeleri", [])]
    mesaj = (f"{m['ad']} ({m['paket']}) için öncelik {state['oncelik']} önerildi: {state['etki']} "
             f"İlk yanıt son tarihi {_dt(h['son_tarih']):%d.%m.%Y %H:%M}; risk {h['risk']}, kalan süre {h['kalan_dk']} dk."
             + (f" Önerilen hizmet kredisi %{h['kredi']['yuzde']:g} ({h['kredi']['tutar']:g} TL)." if h["kredi"]["yuzde"] else "")
             + (" Yönetici onayı bekleniyor." if h["onay"] else ""))
    try:
        cikti = _dogrula(davranis="HESAPLA", musteri=m["ad"], paket=m["paket"], oncelik=state["oncelik"],
                         son_tarih=h["son_tarih"], risk=h["risk"], kalan_dk=h["kalan_dk"], kredi=h["kredi"],
                         onay_gerekli=h["onay"], onay_nedenleri=h["onay_nedenleri"],
                         kaynaklar=_kaynaklar(kaynak02 + [tuple(x) for x in h["atif"]]),
                         durum="BEKLEMEDE" if h["onay"] else "TAMAMLANDI", mesaj=mesaj)
    except ValidationError as e:
        return {"hata": {"adim": "8", "mesaj": f"Paket şemaya uymadı: {e.errors()[0]['msg']}"}}
    return {"cikti": cikti}


@tracked("9_insan_onayi", "kod")
def n_insan_onayi(state):
    """YALNIZCA onay paketini hazırlar ve interrupt çağırır. Burada yan etkili hiçbir işlem yoktur:
    devam edildiğinde düğüm baştan çalışır. Uygulama ayrı düğümlerde, onaydan sonra yapılır."""
    mesaj = {"paket": state["cikti"], "istenen": "Onayla veya Reddet (Reddet için gerekçe zorunlu)"}
    while True:
        cevap = interrupt(mesaj)
        karar = str((cevap or {}).get("karar", "")).upper()
        gerekce = ((cevap or {}).get("gerekce") or "").strip()
        if karar == "ONAYLA" or (karar == "REDDET" and gerekce):
            return {"onay_sonucu": {"karar": karar, "gerekce": gerekce or None,
                                    "karar_zamani": (cevap or {}).get("karar_zamani")}}
        mesaj = {**mesaj, "hata": "Geçersiz karar: ONAYLA veya gerekçeli REDDET gerekir"}


@tracked("10_uygulama", "kod")
def n_uygula(state):
    """Onaydan SONRA: onay paketindeki işlemler uygulanır (prototipte gerçek sistem yok; kayıt tutulur, Doküman 03 §8)."""
    c = state["cikti"]
    islemler = []
    if "kredi_onerisi" in c["onay_nedenleri"]:
        islemler.append(f"hizmet kredisi %{c['kredi']['yuzde']:g} ({c['kredi']['tutar']:g} TL) bir sonraki faturadan düşülmek üzere kaydedildi")
    if "p1_kritik" in c["onay_nedenleri"] or "ihlal" in c["onay_nedenleri"]:
        islemler.append("üst seviyeye çıkarma (eskalasyon) kaydedildi")
    return {"onay_sonucu": {**state["onay_sonucu"], "uygulanan_islemler": islemler, "uygulandi": True}}


@tracked("10_red_kaydi", "kod")
def n_red_kaydi(state):
    """Reddedildi: işlem uygulanmaz, talep olağan akışa döner (Doküman 03 §6.3)."""
    return {"onay_sonucu": {**state["onay_sonucu"], "uygulanan_islemler": [], "uygulandi": False}}


# ---- terminal düğümler (davranış çıktıları)
def _terminal(ad, davranis, kaynaklar=None, **ek):
    @tracked(ad, "kod")
    def dugum(state):
        neden = state.get("neden")
        musteri = _musteri_adi(state)
        paket = state["musteri"]["paket"] if state.get("musteri") else None
        mesaj = MESAJLAR.get(neden, "")
        if davranis == "BILMIYORUM":
            mesaj, paket = BILMIYORUM_YANITI, None
        if davranis == "ENGELLE":
            neden, paket, mesaj = "talimat_iceriyor", None, MESAJLAR["talimat_iceriyor"]
        if davranis == "SORU_SOR" and neden != "oncelik_belirsiz":
            paket = None
        return {"cikti": _dogrula(davranis=davranis, neden=neden, musteri=musteri, paket=paket,
                                  kaynaklar=_kaynaklar(kaynaklar or []), durum="TAMAMLANDI", mesaj=mesaj)}
    return dugum


n_engelle = _terminal("2_engelle", "ENGELLE")
n_bilmiyorum = _terminal("bilmiyorum", "BILMIYORUM")
n_soru_sor = _terminal("soru_sor", "SORU_SOR")
n_oncelik_belirlenemedi = _terminal(
    "oncelik_belirlenemedi", "ONCELIK_BELIRLENEMEDI",
    kaynaklar=[(atif.D02, "8.3"), (atif.D03, "7.1"), (atif.D03, "7.2")])


@tracked("hata", "kod")
def n_hata(state):
    h = state.get("hata", {})
    return {"cikti": _dogrula(davranis=None, neden="sema_hatasi", durum="ISLENEMEDI",
                              mesaj=f"{MESAJLAR['sema_hatasi']} (adım {h.get('adim', '?')})")}


# ------------------------------------------------------------ yönlendirme
def _hata_oncelikli(fn):
    @wraps(fn)
    def r(state):
        return "hata" if state.get("hata") else fn(state)
    return r


@_hata_oncelikli
def r_1b(state):
    return "engelle" if state["talimat"] else "talep_turu"


@_hata_oncelikli
def r_ilk_sonra_on_yonlendirme(state):
    return "on_yonlendirme"


@_hata_oncelikli
def r_on_yonlendirme(state):
    return state["yon"]


@_hata_oncelikli
def r_oncelik(state):
    return "oncelik_yonlendirme"


@_hata_oncelikli
def r_oncelik_yonlendirme(state):
    return state["yon"]


@_hata_oncelikli
def r_hesap(state):
    return "onay_kapisi"


@_hata_oncelikli
def r_paket(state):
    return "insan_onayi" if state["cikti"]["onay_gerekli"] else "bitti"


def r_onay(state):
    return "uygula" if state["onay_sonucu"]["karar"] == "ONAYLA" else "red_kaydi"


def graf_olustur(checkpointer):
    g = StateGraph(Durum)
    for ad, fn in [("musteri_arama", n_musteri_arama), ("talimat", n_talimat), ("talep_turu", n_talep_turu),
                   ("firma_adi", n_firma_adi), ("on_yonlendirme", n_on_yonlendirme), ("oncelik", n_oncelik),
                   ("oncelik_yonlendirme", n_oncelik_yonlendirme), ("hesap", n_hesap), ("onay_kapisi", n_onay_kapisi),
                   ("paket_dogrula", n_paket_dogrula), ("insan_onayi", n_insan_onayi), ("uygula", n_uygula),
                   ("red_kaydi", n_red_kaydi), ("engelle", n_engelle), ("bilmiyorum", n_bilmiyorum),
                   ("soru_sor", n_soru_sor), ("oncelik_belirlenemedi", n_oncelik_belirlenemedi), ("hata", n_hata)]:
        g.add_node(ad, fn)
    g.add_edge(START, "musteri_arama")
    g.add_edge("musteri_arama", "talimat")
    g.add_conditional_edges("talimat", r_1b, {"engelle": "engelle", "talep_turu": "talep_turu", "hata": "hata"})
    g.add_conditional_edges("talep_turu", r_ilk_sonra_on_yonlendirme, {"on_yonlendirme": "on_yonlendirme", "hata": "hata"})
    g.add_conditional_edges("on_yonlendirme", r_on_yonlendirme,
                            {"bilmiyorum": "bilmiyorum", "soru_sor": "soru_sor", "firma_1d": "firma_adi",
                             "oncelik": "oncelik", "hata": "hata"})
    g.add_conditional_edges("firma_adi", r_ilk_sonra_on_yonlendirme, {"on_yonlendirme": "on_yonlendirme", "hata": "hata"})
    g.add_conditional_edges("oncelik", r_oncelik, {"oncelik_yonlendirme": "oncelik_yonlendirme", "hata": "hata"})
    g.add_conditional_edges("oncelik_yonlendirme", r_oncelik_yonlendirme,
                            {"hesap": "hesap", "soru_sor": "soru_sor",
                             "oncelik_belirlenemedi": "oncelik_belirlenemedi", "hata": "hata"})
    g.add_conditional_edges("hesap", r_hesap, {"onay_kapisi": "onay_kapisi", "hata": "hata"})
    g.add_edge("onay_kapisi", "paket_dogrula")
    g.add_conditional_edges("paket_dogrula", r_paket, {"insan_onayi": "insan_onayi", "bitti": END, "hata": "hata"})
    g.add_conditional_edges("insan_onayi", r_onay, {"uygula": "uygula", "red_kaydi": "red_kaydi"})
    for son in ("uygula", "red_kaydi", "engelle", "bilmiyorum", "soru_sor", "oncelik_belirlenemedi", "hata"):
        g.add_edge(son, END)
    return g.compile(checkpointer=checkpointer)


# ------------------------------------------------------------------- API
_graf = None


def sqlite_checkpointer(yol=None) -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(str(yol or config.CHECKPOINT_DB), check_same_thread=False))


def graf(yeni: bool = False, checkpointer=None):
    """Varsayılan: kalıcı SQLite checkpointer. Testlerde graf(yeni=True, checkpointer=...) verilir."""
    global _graf
    if yeni or _graf is None:
        _graf = graf_olustur(checkpointer or sqlite_checkpointer())
    return _graf


def _cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _sonuc(thread_id: str, r: dict) -> dict:
    """Çağıran için özet: durum, çıktı, bekleyen onay, adım süreleri."""
    st = graf().get_state(_cfg(thread_id)).values
    bekliyor = bool(r.get("__interrupt__"))
    cikti = st.get("cikti")
    onay = st.get("onay_sonucu")
    durum = "BEKLEMEDE" if bekliyor else (cikti["durum"] if cikti else "ISLENEMEDI")
    if onay and not bekliyor:
        durum = "TAMAMLANDI"
    return {"thread_id": thread_id, "durum": durum, "cikti": cikti, "onay_sonucu": onay,
            "bekleyen_onay": r["__interrupt__"][0].value if bekliyor else None,
            "adim_sureleri": st.get("adim_sureleri", []), "hata": st.get("hata")}


def talep_isle(talep_metni: str, kayit_zamani, simdi, thread_id: str, soru_soruldu: bool = False) -> dict:
    """Bir talebi işler. Onay gerekiyorsa BEKLEMEDE döner (otomatik onay yok)."""
    g = graf()
    if g.get_state(_cfg(thread_id)).values:
        raise ValueError(f"thread_id zaten kullanılmış: {thread_id!r} (her talep için benzersiz olmalı)")
    r = g.invoke({"talep_metni": talep_metni, "kayit_zamani": _dt(kayit_zamani).isoformat(),
                  "simdi": _dt(simdi).isoformat(), "soru_soruldu": soru_soruldu, "adim_sureleri": []}, _cfg(thread_id))
    return _sonuc(thread_id, r)


def onay_ver(thread_id: str, karar: str, gerekce: Optional[str] = None, karar_zamani=None) -> dict:
    """Bekleyen onayı sonlandırır. karar: "ONAYLA" | "REDDET" (REDDET için gerekçe zorunlu)."""
    karar = (karar or "").upper()
    if karar not in ("ONAYLA", "REDDET"):
        raise ValueError("karar ONAYLA veya REDDET olmalı")
    if karar == "REDDET" and not (gerekce or "").strip():
        raise ValueError("Reddetmek için gerekçe zorunludur (Doküman 03 Madde 6.2)")
    g = graf()
    if g.get_state(_cfg(thread_id)).next != ("insan_onayi",):
        raise ValueError(f"{thread_id!r} için bekleyen onay yok")
    kz = _dt(karar_zamani) if karar_zamani else datetime.now()
    r = g.invoke(Command(resume={"karar": karar, "gerekce": gerekce, "karar_zamani": kz.isoformat()}), _cfg(thread_id))
    return _sonuc(thread_id, r)
