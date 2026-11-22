"""Destek sistemi ve bildirim SİMÜLATÖRÜ (sentetik/kurgusal).

Gerçek e-posta, Slack veya destek sistemine BAĞLI DEĞİLDİR. n8n akışının dış dünyasını taklit eder:
  - GET  /talepler/sonraki          : demo/kayitli_sonuclar.json'daki Demo 1 ve Demo 2'yi (sabit metin ve zamanlarla) sırayla verir
  - POST /talepler/{id}/sonuc       : n8n sonucu geri yazar (dosyada saklanır), GET ile okunur
  - POST /bildirim, GET /bildirimler: bildirimleri dis_sistem/bildirimler.jsonl dosyasına kaydeder / listeler

Çalıştırma:  python dis_sistem/simulator.py [--host 127.0.0.1] [--port 8001]
(Docker'daki n8n'in erişebilmesi için --host 0.0.0.0; yalnızca yerel ağ, kimlik doğrulama yok.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import Body, FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
KAYITLI = KOK / "demo" / "kayitli_sonuclar.json"
VERI_DIZINI = Path(os.getenv("SIM_VERI_DIZINI", str(Path(__file__).resolve().parent)))
BILDIRIMLER = VERI_DIZINI / "bildirimler.jsonl"
SONUCLAR = VERI_DIZINI / "sonuclar.json"
DEMO_ADLARI = ("Demo 1: Komutlu talep", "Demo 2: İhlalli P2 talep")

_kilit = threading.Lock()
_sayac = 0


def _talepler() -> list[dict]:
    """Sabit talep listesi: Demo 1 ve Demo 2 (metin, kayıt zamanı ve 'şimdi' kayıtlı dosyadan; rastgele veri yok)."""
    kayitlar = {k["ad"]: k for k in json.loads(KAYITLI.read_text(encoding="utf-8"))["kayitlar"]}
    return [{"kaynak": ad, "talep_metni": kayitlar[ad]["metin"], "kayit_zamani": kayitlar[ad]["kayit_zamani"],
             "simdi": kayitlar[ad]["simdi"]} for ad in DEMO_ADLARI]


class Bildirim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kanal: str = Field(min_length=1, max_length=100)
    baslik: str = Field(min_length=1, max_length=300)
    mesaj: str = Field(min_length=1, max_length=5000)
    oncelik: str = Field(min_length=1, max_length=30)
    talep_id: Optional[str] = Field(default=None, max_length=100)


app = FastAPI(title="Destek sistemi ve bildirim simülatörü (sentetik)",
              description="Gerçek e-posta/Slack/destek sistemine bağlı değildir; yalnızca demo içindir.")


@app.get("/talepler/sonraki", summary="Sıradaki sentetik talep (Demo 1, Demo 2, tekrar başa)")
def sonraki():
    global _sayac
    with _kilit:
        liste = _talepler()
        t = liste[_sayac % len(liste)]
        _sayac += 1
        return {"talep_id": f"DS-{_sayac:04d}", **t}


def _sonuclari_oku() -> dict:
    try:
        return json.loads(SONUCLAR.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@app.post("/talepler/{talep_id}/sonuc", summary="n8n ajan sonucunu geri yazar")
def sonuc_yaz(talep_id: str, govde: dict[str, Any] = Body(...)):
    with _kilit:
        d = _sonuclari_oku()
        d[talep_id] = {"yazma_zamani": datetime.now().isoformat(timespec="seconds"), "sonuc": govde}
        SONUCLAR.parent.mkdir(parents=True, exist_ok=True)
        SONUCLAR.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"talep_id": talep_id, "kaydedildi": True}


@app.get("/talepler/{talep_id}/sonuc", summary="Geri yazılan sonuç")
def sonuc_oku(talep_id: str):
    d = _sonuclari_oku()
    if talep_id not in d:
        raise HTTPException(404, f"{talep_id} için sonuç yok")
    return {"talep_id": talep_id, **d[talep_id]}


@app.post("/bildirim", status_code=201, summary="Bildirim kaydeder (gerçek kanala gönderilmez)")
def bildirim_yaz(b: Bildirim):
    kayit = {"zaman": datetime.now().isoformat(timespec="seconds"), **b.model_dump()}
    with _kilit:
        BILDIRIMLER.parent.mkdir(parents=True, exist_ok=True)
        with BILDIRIMLER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return kayit


@app.get("/bildirimler", summary="Kaydedilen bildirimler")
def bildirimler():
    if not BILDIRIMLER.exists():
        return {"adet": 0, "bildirimler": []}
    liste = [json.loads(s) for s in BILDIRIMLER.read_text(encoding="utf-8").splitlines() if s.strip()]
    return {"adet": len(liste), "bildirimler": liste}


@app.post("/sifirla", summary="Demo için: sayaç, sonuçlar ve bildirimleri temizler")
def sifirla():
    global _sayac
    with _kilit:
        _sayac = 0
        for p in (BILDIRIMLER, SONUCLAR):
            p.unlink(missing_ok=True)
    return {"sifirlandi": True}


def main():
    import uvicorn
    ap = argparse.ArgumentParser(description="Destek sistemi ve bildirim simülatörü")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8001)
    a = ap.parse_args()
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
