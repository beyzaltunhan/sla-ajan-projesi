"""Ajan servisi (FastAPI): ajanı HTTP üzerinden çağrılabilir yapar (n8n gibi dış otomasyonlar için).

Ajan koduna dokunmaz: ajan.talep_isle / ajan.onay_ver / ajan.graf aynen kullanılır. Servis, Streamlit arayüzüyle
checkpoint dosyasını PAYLAŞMAMAK için AYRI bir dosya kullanır (servis_checkpoints.sqlite; ortam değişkeni SERVIS_CHECKPOINT).
Model CPU'da tek olduğundan talepler tek işçide, sırayla işlenir; POST /talep asenkrondur (202).

Çalıştırma:  python servis.py [--host 127.0.0.1] [--port 8000]     veya     uvicorn servis:app
"""
from __future__ import annotations

import argparse
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

import config
from schemas.onay_paketi import KararCiktisi

log = logging.getLogger("servis")
CHECKPOINT = Path(os.getenv("SERVIS_CHECKPOINT", str(config.ROOT / "servis_checkpoints.sqlite")))

Durum = Literal["ISLENIYOR", "ONAY_BEKLIYOR", "TAMAMLANDI", "ISLENEMEDI"]


# ------------------------------------------------------------------ ajan erişimi (testlerde taklit edilir)
class _Ajan:
    """ajan modülüne ince erişim katmanı; birim testleri bunu değiştirir (ajan CPU'da yavaş, Ollama gerektirir)."""

    def hazirla(self):
        import ajan
        ajan.graf(yeni=True, checkpointer=ajan.sqlite_checkpointer(CHECKPOINT))   # servise özel checkpoint dosyası
        return ajan

    def talep_isle(self, *a, **k):
        import ajan
        return ajan.talep_isle(*a, **k)

    def onay_ver(self, *a, **k):
        import ajan
        return ajan.onay_ver(*a, **k)

    def graf(self):
        import ajan
        return ajan.graf()


AJAN = _Ajan()


# ------------------------------------------------------------------ şemalar
def _naif(v: Optional[datetime], alan: str) -> Optional[datetime]:
    if v is not None and v.tzinfo is not None:
        raise ValueError(f"{alan} saat dilimi içermemeli (yerel saat kabul edilir), örn. 2026-11-19T10:00:00")
    return v


class TalepGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid")
    talep_metni: str = Field(min_length=1, max_length=5000, description="Müşteri talep metni")
    kayit_zamani: Optional[datetime] = Field(default=None, description="Talebin kaydedildiği an (ISO 8601, saat dilimsiz); yoksa şimdi")
    simdi: Optional[datetime] = Field(default=None, description="Değerlendirme anı (ISO 8601, saat dilimsiz); yoksa sistem saati")
    soru_soruldu: bool = Field(default=False, description="Müşteriye bu talepte daha önce soru soruldu mu (ikinci tur)")

    @field_validator("talep_metni")
    @classmethod
    def _bos_degil(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("talep_metni boş olamaz")
        return v

    @field_validator("kayit_zamani")
    @classmethod
    def _kz(cls, v):
        return _naif(v, "kayit_zamani")

    @field_validator("simdi")
    @classmethod
    def _sm(cls, v):
        return _naif(v, "simdi")


class OnayGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid")
    karar: Literal["onayla", "reddet"]
    gerekce: str = Field(default="", max_length=2000)

    @field_validator("karar", mode="before")
    @classmethod
    def _kucuk(cls, v):
        return v.strip().lower() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _red_gerekcesi(self):
        if self.karar == "reddet" and not self.gerekce.strip():
            raise ValueError("Reddetmek için gerekce zorunludur")
        return self


class TalepYaniti(BaseModel):
    talep_id: str
    durum: Durum


class DurumYaniti(BaseModel):
    talep_id: str
    durum: Durum
    sirada: bool = Field(default=False, description="ISLENIYOR iken: henüz işçiye alınmadı (sırada bekliyor)")
    cikti: Optional[KararCiktisi] = None
    onay_sonucu: Optional[dict[str, Any]] = None
    sure_sn: Optional[float] = Field(default=None, description="Ajanın çalışma süresi (onay bekleme süresi hariç)")
    adim_sureleri: list[dict[str, Any]] = Field(default_factory=list)
    hata: Optional[dict[str, Any]] = None


# ------------------------------------------------------------------ iş durumu (bellekte) + kuyruk
_isci = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ajan-isci")    # tek işçi: aynı anda tek talep
_kilit = threading.Lock()
_isler: dict[str, dict[str, Any]] = {}
_hazir = False
_hazir_kilit = threading.Lock()


def _hazirla():
    global _hazir
    with _hazir_kilit:
        if not _hazir:
            AJAN.hazirla()
            _hazir = True


def _durum_adi(sonuc: dict) -> Durum:
    if sonuc.get("durum") == "BEKLEMEDE":
        return "ONAY_BEKLIYOR"
    if sonuc.get("durum") == "ISLENEMEDI" or not sonuc.get("cikti"):
        return "ISLENEMEDI"
    return "TAMAMLANDI"


def _calistir(talep_id: str, g: TalepGirdisi):
    with _kilit:
        _isler[talep_id]["sirada"] = False
        _isler[talep_id]["baslangic"] = time.perf_counter()
    simdi = g.simdi or datetime.now().replace(microsecond=0)
    try:
        _hazirla()
        sonuc = AJAN.talep_isle(g.talep_metni, g.kayit_zamani or simdi, simdi, talep_id, soru_soruldu=g.soru_soruldu)
        yeni = {"durum": _durum_adi(sonuc), "sonuc": sonuc}
    except Exception as e:  # noqa: BLE001 — servis çökmesin; hata durum olarak raporlanır
        log.exception("talep işlenemedi: %s", talep_id)
        yeni = {"durum": "ISLENEMEDI", "sonuc": {"hata": {"adim": "servis", "mesaj": f"{type(e).__name__}: {e}"}}}
    with _kilit:
        _isler[talep_id].update(yeni)
        _isler[talep_id]["sure_sn"] = round(time.perf_counter() - _isler[talep_id]["baslangic"], 1)


def _canli_adimlar(talep_id: str) -> list[dict]:
    """ISLENIYOR iken tamamlanan adımlar (checkpointer'dan; hata olursa boş)."""
    try:
        _hazirla()          # graf, servis checkpoint'iyle kurulmadan ajan.graf() ÇAĞRILMAMALI (varsayılan dosyayı açar, yarış yaratır)
        return list(AJAN.graf().get_state({"configurable": {"thread_id": talep_id}}).values.get("adim_sureleri", []))
    except Exception:  # noqa: BLE001
        return []


def _yanit(talep_id: str, is_: dict) -> DurumYaniti:
    s = is_.get("sonuc") or {}
    d = is_["durum"]
    return DurumYaniti(
        talep_id=talep_id, durum=d, sirada=bool(is_.get("sirada")) if d == "ISLENIYOR" else False,
        cikti=s.get("cikti"), onay_sonucu=s.get("onay_sonucu"), sure_sn=is_.get("sure_sn"),
        adim_sureleri=s.get("adim_sureleri") or (_canli_adimlar(talep_id) if d == "ISLENIYOR" and not is_.get("sirada") else []),
        hata=s.get("hata"))


def _kayitli_is(talep_id: str) -> Optional[dict]:
    """Servis yeniden başlamış olabilir: bekleyen onaylar checkpoint dosyasından geri yüklenir (thread_id = talep_id)."""
    try:
        _hazirla()
        st = AJAN.graf().get_state({"configurable": {"thread_id": talep_id}})
    except Exception:  # noqa: BLE001
        return None
    if not st.values:
        return None
    v = st.values
    bekliyor = st.next == ("insan_onayi",)
    sonuc = {"durum": "BEKLEMEDE" if bekliyor else (v.get("cikti") or {}).get("durum", "ISLENEMEDI"), "cikti": v.get("cikti"),
             "onay_sonucu": v.get("onay_sonucu"), "adim_sureleri": v.get("adim_sureleri", []), "hata": v.get("hata")}
    if v.get("onay_sonucu"):
        sonuc["durum"] = "TAMAMLANDI"
    return {"durum": _durum_adi(sonuc), "sonuc": sonuc, "sirada": False}


# ------------------------------------------------------------------ uygulama
app = FastAPI(title="SLA Ajan Servisi", version="1.0",
              description="SLA uyum ve eskalasyon ajanını HTTP üzerinden çağırır. Prototip: kimlik doğrulama yoktur.")


@app.post("/talep", status_code=202, response_model=TalepYaniti, summary="Talebi asenkron işlemeye al")
def talep_olustur(g: TalepGirdisi):
    talep_id = "t-" + uuid.uuid4().hex[:12]
    with _kilit:
        _isler[talep_id] = {"durum": "ISLENIYOR", "sirada": True, "sonuc": None, "olusturma": datetime.now().isoformat()}
    _isci.submit(_calistir, talep_id, g)
    return TalepYaniti(talep_id=talep_id, durum="ISLENIYOR")


def _is_getir(talep_id: str) -> dict:
    with _kilit:
        is_ = _isler.get(talep_id)
    if is_ is None:
        is_ = _kayitli_is(talep_id)
        if is_ is not None:
            with _kilit:
                _isler[talep_id] = is_
    if is_ is None:
        raise HTTPException(404, f"Bilinmeyen talep_id: {talep_id}")
    return is_


@app.get("/durum/{talep_id}", response_model=DurumYaniti, summary="Talebin durumu ve sonucu")
def durum(talep_id: str):
    return _yanit(talep_id, dict(_is_getir(talep_id)))


@app.post("/onay/{talep_id}", response_model=DurumYaniti, summary="Bekleyen onayı sonuçlandır")
def onay(talep_id: str, g: OnayGirdisi):
    is_ = _is_getir(talep_id)
    with _kilit:
        if is_["durum"] != "ONAY_BEKLIYOR":
            raise HTTPException(409, f"Talep onay beklemiyor (durum: {is_['durum']}).")
    try:
        sonuc = AJAN.onay_ver(talep_id, g.karar.upper(), g.gerekce.strip() or None)
    except ValueError as e:                      # ajanın kendi engeli (ör. bekleyen onay yok) olduğu gibi
        raise HTTPException(409, str(e)) from None
    with _kilit:
        eski = _isler[talep_id].get("sonuc") or {}
        _isler[talep_id].update({"durum": _durum_adi(sonuc), "sonuc": {**eski, **sonuc}})
        is_ = dict(_isler[talep_id])
    return _yanit(talep_id, is_)


@app.get("/bekleyen", summary="Onay bekleyen talepler")
def bekleyen():
    with _kilit:
        liste = [{"talep_id": t, "musteri": ((i.get("sonuc") or {}).get("cikti") or {}).get("musteri"),
                  "oncelik": ((i.get("sonuc") or {}).get("cikti") or {}).get("oncelik")}
                 for t, i in _isler.items() if i["durum"] == "ONAY_BEKLIYOR"]
    return {"adet": len(liste), "talepler": liste}


@app.get("/saglik", summary="Servis ve Ollama durumu")
def saglik():
    ollama_durum, ayrinti = "bilinmiyor", None
    try:
        import ollama
        yuklu = [m.model for m in ollama.Client(host=config.OLLAMA_URL, timeout=3).list().models]
        ollama_durum = "acik"
        ayrinti = {"sohbet_modeli_yuklu": any(a.split(":")[0] == config.CHAT_MODEL.split(":")[0] for a in yuklu),
                   "embedding_modeli_yuklu": any(a.split(":")[0] == config.EMBED_MODEL.split(":")[0] for a in yuklu)}
    except Exception as e:  # noqa: BLE001
        ollama_durum, ayrinti = "kapali", f"{type(e).__name__}"
    with _kilit:
        isleniyor = sum(1 for i in _isler.values() if i["durum"] == "ISLENIYOR")
    return {"servis": "calisiyor", "ollama": ollama_durum, "ollama_ayrinti": ayrinti, "chat_modeli": config.CHAT_MODEL,
            "checkpoint_dosyasi": CHECKPOINT.name, "isleniyor_veya_sirada": isleniyor}


def main():
    import uvicorn
    ap = argparse.ArgumentParser(description="SLA ajan servisi")
    ap.add_argument("--host", default="127.0.0.1", help="Docker'daki n8n erişecekse 0.0.0.0 (yalnızca yerel ağ!)")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
