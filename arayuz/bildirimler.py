"""Bildirimler paneli yardımcıları (Streamlit'ten bağımsız, test edilebilir).

Bildirimler dis_sistem/bildirimler.jsonl dosyasından okunur (alanlar: zaman, kanal, baslik, mesaj, oncelik, talep_id).
Onay düğmeleri ajan servisini (varsayılan http://127.0.0.1:8000) çağırır; bunlar İNSAN kararıdır, otomatik onay yoktur.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]


def bildirim_dosyasi() -> Path:
    return Path(os.getenv("SLA_BILDIRIM_DOSYASI", str(KOK / "dis_sistem" / "bildirimler.jsonl")))


def servis_adresi() -> str:
    return os.getenv("SLA_SERVIS_URL", "http://127.0.0.1:8000").rstrip("/")


# kanal -> (okunur ad, rozet sınıfı); bilinmeyen kanal da gösterilir
KANALLAR = {
    "guvenlik-insan-inceleme": ("Güvenlik / insan inceleme", "engelle"),
    "onay-kuyrugu": ("Onay kuyruğu", "p2"),
    "insan-destek": ("İnsan destek", "soru"),
    "destek-ozet": ("Destek özeti", "hesapla"),
    "sistem-uyari": ("Sistem uyarısı", "hata"),
}
ONCELIK = {"yuksek": ("Yüksek", "p1"), "orta": ("Orta", "p3"), "normal": ("Normal", "p4")}


def oku(yol: Path | None = None) -> list[dict]:
    """Bildirimleri yeniden eskiye sıralı okur; dosya yoksa boş liste. Bozuk satırlar atlanır (panel çökmez)."""
    yol = yol or bildirim_dosyasi()
    try:
        satirlar = yol.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    liste = []
    for s in satirlar:
        if not s.strip():
            continue
        try:
            d = json.loads(s)
        except ValueError:
            continue
        if isinstance(d, dict):
            liste.append(d)
    return sorted(liste, key=lambda b: str(b.get("zaman", "")), reverse=True)


def onay_karti_mi(b: dict) -> bool:
    """Onay düğmeleri yalnızca onay-kuyrugu kanalında ve ajan talep_id'si (t-...) varsa gösterilir."""
    return b.get("kanal") == "onay-kuyrugu" and str(b.get("talep_id") or "").startswith("t-")


def zaman_yaz(z: str | None) -> str:
    from datetime import datetime
    try:
        return datetime.fromisoformat(z).strftime("%d.%m.%Y %H:%M:%S")
    except (TypeError, ValueError):
        return z or "—"


# ------------------------------------------------------------------ servis istemcisi
class ServisKapali(Exception):
    """Ajan servisine ulaşılamadı."""


class ServisHatasi(Exception):
    """Servis yanıt verdi ama hata döndü (durum kodu ve ayrıntı ile)."""

    def __init__(self, kod: int, ayrinti: str):
        super().__init__(f"{kod}: {ayrinti}")
        self.kod, self.ayrinti = kod, ayrinti


def _istek(yontem: str, yol: str, govde: dict | None = None, zaman_asimi: float = 5.0) -> dict:
    r = urllib.request.Request(servis_adresi() + yol, method=yontem, headers={"Content-Type": "application/json"},
                               data=json.dumps(govde).encode("utf-8") if govde is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=zaman_asimi) as x:
            return json.loads(x.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            d = json.loads(e.read() or b"{}").get("detail", "")
        except ValueError:
            d = ""
        raise ServisHatasi(e.code, d if isinstance(d, str) else json.dumps(d, ensure_ascii=False)) from None
    except (urllib.error.URLError, OSError, TimeoutError):
        raise ServisKapali(servis_adresi()) from None


def servis_calisiyor() -> bool:
    """Hafif yoklama (GET /bekleyen: Ollama'ya dokunmaz, hızlı). Ulaşılamazsa False; yanıt hata kodu verse de servis ayaktadır."""
    try:
        _istek("GET", "/bekleyen", zaman_asimi=3.0)
    except ServisKapali:
        return False
    except ServisHatasi:
        return True
    return True


def servis_durum(talep_id: str) -> dict:
    return _istek("GET", f"/durum/{talep_id}")


def onay_gonder(talep_id: str, karar: str, gerekce: str = "") -> dict:
    """Önce GET /durum ile ONAY_BEKLIYOR doğrulanır; sonra POST /onay. Reddette boş gerekçe GÖNDERİLMEZ (ValueError)."""
    karar = karar.lower()
    if karar not in ("onayla", "reddet"):
        raise ValueError("karar onayla ya da reddet olmalı")
    if karar == "reddet" and not (gerekce or "").strip():
        raise ValueError("Reddetmek için gerekçe zorunludur.")
    d = servis_durum(talep_id)
    if d.get("durum") != "ONAY_BEKLIYOR":
        raise ServisHatasi(409, f"Talep onay beklemiyor (durum: {d.get('durum')}).")
    return _istek("POST", f"/onay/{talep_id}", {"karar": karar, "gerekce": (gerekce or "").strip()})


def hata_metni(e: Exception) -> str:
    if isinstance(e, ServisKapali):
        return f"Ajan servisi çalışmıyor ({e}). Servisi başlatın: python servis.py"
    if isinstance(e, ServisHatasi):
        return f"Servis isteği reddetti ({e.kod}): {e.ayrinti}" if e.kod != 404 else \
            "Servis bu talebi tanımıyor (404): talep başka bir servis oturumundan olabilir."
    return str(e)
