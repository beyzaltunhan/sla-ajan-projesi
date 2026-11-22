"""Model ön ısıtma: Ollama'ya kısa bir sohbet ve bir embedding çağrısı (modelleri belleğe yükler)."""
from __future__ import annotations

import time

import config


def isit() -> dict:
    """{'durum': 'hazir'|'hata', 'sure_sn', 'ayrinti'}. Hata durumunda uygulama çökmez; anlaşılır mesaj döner."""
    import ollama
    import llm_adimlari
    t0 = time.perf_counter()
    adim = "sohbet modeli"
    try:
        llm_adimlari._sohbet([{"role": "user", "content": "Merhaba"}], {"type": "object", "properties": {"a": {"type": "string"}}})
        adim = "embedding modeli"
        ollama.Client(host=config.OLLAMA_URL).embed(model=config.EMBED_MODEL, input="ısınma")
    except Exception as e:  # noqa: BLE001
        return {"durum": "hata", "sure_sn": round(time.perf_counter() - t0, 1),
                "ayrinti": f"{adim} çağrısı başarısız ({type(e).__name__}). Ollama'nın çalıştığını ve "
                           f"'{config.CHAT_MODEL}' / '{config.EMBED_MODEL}' modellerinin yüklü olduğunu kontrol edin."}
    return {"durum": "hazir", "sure_sn": round(time.perf_counter() - t0, 1),
            "ayrinti": f"{config.CHAT_MODEL} ve {config.EMBED_MODEL} hazır."}
