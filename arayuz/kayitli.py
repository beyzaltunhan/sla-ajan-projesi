"""Önceden çalıştırılmış (kayıtlı) sonuçlar: demo/kayitli_sonuclar.json. Canlı sonuç gibi sunulmaz (bkz. bilesenler.sonuc_goster)."""
from __future__ import annotations

import json
from pathlib import Path

DOSYA = Path(__file__).resolve().parents[1] / "demo" / "kayitli_sonuclar.json"


def yukle(yol: Path = DOSYA) -> list[dict]:
    """Kayıt listesi; dosya yoksa boş liste. Her kayıt: ad, metin, kayit_tarihi, sonuc{...}."""
    if not yol.exists():
        return []
    return json.loads(yol.read_text(encoding="utf-8")).get("kayitlar", [])
