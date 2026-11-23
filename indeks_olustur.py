"""Chroma indeksini (chroma_db/) docs/ altındaki 4 dokümandan oluşturur.

Ne yapar: dokümanları madde madde parçalar, her parçanın embedding'ini Ollama ile (embeddinggemma) hesaplar ve
chroma_db/ klasörüne kaydeder. Ajanın "öncelik önerisi" adımı kaynak maddeleri buradan getirir.
Gereksinim: Ollama çalışıyor ve `embeddinggemma` modeli yüklü olmalı (`ollama pull embeddinggemma`).

Kullanım:
    python indeks_olustur.py             # chroma_db yoksa/boşsa oluşturur; doluysa dokunmadan çıkar
    python indeks_olustur.py --yenile    # mevcut chroma_db'yi SİLİP yeniden oluşturur
    python indeks_olustur.py --db-dir <klasör>   # (deneme) başka bir klasöre yazar; mevcut chroma_db'ye dokunmaz
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import config


def ollama_hazir_mi() -> str | None:
    """Embedding modeli kullanılabilir mi? Sorun varsa anlaşılır Türkçe mesaj döner, yoksa None."""
    try:
        import ollama
        ollama.Client(host=config.OLLAMA_URL).embed(model=config.EMBED_MODEL, input="deneme")
    except Exception as e:  # noqa: BLE001
        return (f"Ollama'ya ulaşılamadı ya da '{config.EMBED_MODEL}' modeli yüklü değil ({type(e).__name__}).\n"
                f"Ollama'yı başlatın ve şunu çalıştırın: ollama pull {config.EMBED_MODEL}")
    return None


def dolu_mu(klasor: Path) -> bool:
    return klasor.exists() and any(klasor.iterdir())


def calistir(yenile: bool = False, db_dir: Path | None = None) -> int:
    from rag.indeks import indeks_olustur
    from rag.parcala import dokumanlari_parcala
    hedef = Path(db_dir) if db_dir else config.DB_DIR
    if dolu_mu(hedef) and not yenile:
        print(f"{hedef} zaten dolu; dokunulmadı. Silip yeniden oluşturmak için: python indeks_olustur.py --yenile")
        return 0
    sorun = ollama_hazir_mi()
    if sorun:
        print("HATA:", sorun)
        return 1
    parca = len(dokumanlari_parcala())
    print(f"{parca} madde parçası için embedding hesaplanıyor (Ollama gerekir, CPU'da biraz sürebilir)...")
    try:
        # Özel klasörde sifirla=False: rag.indeks yalnızca config.DB_DIR'i silmeye izin verir.
        indeks_olustur(db_dir=db_dir, sifirla=db_dir is None)
    except Exception as e:  # noqa: BLE001
        print(f"HATA: indeks oluşturulamadı ({type(e).__name__}: {e})")
        return 1
    print(f"Tamam: {parca} parça {hedef} içine yüklendi. (Ollama yalnızca bu adım ve ajan çalışırken gerekir.)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SLA dokümanlarından Chroma indeksi oluşturur.")
    ap.add_argument("--yenile", action="store_true", help="mevcut chroma_db'yi silip yeniden oluştur")
    ap.add_argument("--db-dir", type=Path, default=None, help="(deneme) başka bir klasöre yaz")
    a = ap.parse_args()
    sys.exit(calistir(a.yenile, a.db_dir))
