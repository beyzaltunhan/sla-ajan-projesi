"""Demo örneklerini gerçek modelle çalıştırır (ajana dokunmadan; geçici checkpoint veritabanı kullanır, kalıcı kayıtları kirletmez)."""
from __future__ import annotations

import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

import ajan  # noqa: E402
from arayuz import bicimle as B  # noqa: E402


def gecici_graf():
    """Geçici sqlite ile yeni graf kurar; (klasör, graf) döner. Klasör çağıran tarafından silinmeli."""
    klasor = tempfile.TemporaryDirectory(prefix="sla_demo_", ignore_cleanup_errors=True)
    g = ajan.graf(yeni=True, checkpointer=ajan.sqlite_checkpointer(Path(klasor.name) / "demo.sqlite"))
    return klasor, g


def ornek_calistir(ad: str, sayac: int, simdi: datetime | None = None) -> dict:
    simdi = simdi or datetime.now().replace(microsecond=0)
    o = B.ornekler(simdi)[ad]
    tid = f"demo-{datetime.now():%H%M%S}-{sayac}"
    t0 = time.perf_counter()
    try:
        s = ajan.talep_isle(o["metin"], o["kayit_zamani"], simdi, tid, soru_soruldu=o["soru_soruldu"])
    except Exception as e:  # noqa: BLE001
        s = {"thread_id": tid, "durum": "ISLENEMEDI", "cikti": None, "onay_sonucu": None, "bekleyen_onay": None,
             "adim_sureleri": [], "hata": {"adim": "?", "mesaj": f"{type(e).__name__}: {e}"}}
    s["toplam_sn"] = round(time.perf_counter() - t0, 1)
    return {"ad": ad, "metin": o["metin"], "kayit_zamani": o["kayit_zamani"].isoformat(), "simdi": simdi.isoformat(),
            "soru_soruldu": o["soru_soruldu"], "beklenen": o["beklenen"], "sonuc": s}
