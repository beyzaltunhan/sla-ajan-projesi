"""RAG katmanı: dokümanların madde bazında parçalanması, Chroma indeksi, retrieve().

Parçalama birimi (dokümanların kendi yapısından): Doküman 01-03'te numaralı hüküm
("5.5", "8.3" ...), Doküman 04'te soru ("Soru 4"). Üst başlık ("Madde 5 – ...")
her hükmün metnine bağlam olarak eklenir. Tablo ve madde işaretli listeler
kendi hükmünün parçasıdır.
"""
from __future__ import annotations

import re
from pathlib import Path  # noqa: F401

from config import DOCS_DIR
_HUKUM = re.compile(r"^(\d+\.\d+) ")
_MADDE_BASLIK = re.compile(r"^## (?:Madde \d+|Soru (\d+)) – (.+)$")


def dokumanlari_parcala(docs_dir: Path = DOCS_DIR) -> list[dict]:
    """Her parça: dokuman, madde, baslik, metin (bağlam başlığı + hüküm gövdesi)."""
    parcalar: list[dict] = []
    for yol in sorted(docs_dir.glob("*.md")):
        dokuman = yol.stem
        baslik = None          # güncel "## ..." satırı (bağlam)
        soru_no = None
        hukum_no = None
        satirlar: list[str] = []

        def kapat():
            nonlocal hukum_no, satirlar
            govde = "\n".join(satirlar).strip()
            if baslik and govde:
                madde = hukum_no if hukum_no else (f"Soru {soru_no}" if soru_no else None)
                if madde:
                    parcalar.append({"dokuman": dokuman, "madde": madde,
                                     "baslik": baslik[3:], "metin": f"{baslik[3:]}\n{govde}"})
            hukum_no, satirlar = None, []

        for satir in yol.read_text(encoding="utf-8").splitlines():
            m = _MADDE_BASLIK.match(satir)
            if m:
                kapat()
                baslik, soru_no = satir, m.group(1)
                continue
            if baslik is None:      # ilk başlıktan önceki künye/uyarı satırları indekslenmez
                continue
            h = _HUKUM.match(satir)
            if h:
                kapat()
                hukum_no = h.group(1)
            satirlar.append(satir)
        kapat()
    return parcalar
