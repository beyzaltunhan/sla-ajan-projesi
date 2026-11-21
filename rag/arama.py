"""retrieve(sorgu, k): Chroma'dan en benzer madde parçalarını getirir."""
from __future__ import annotations

from rag.indeks import vektor_deposu

VARSAYILAN_K = 5
_depo = None


def retrieve(sorgu: str, k: int = VARSAYILAN_K, dokuman: str | None = None, depo=None) -> list[dict]:
    """Döner: [{dokuman, madde, skor, metin}], en benzer önce.

    skor = kosinüs mesafesi (0 = aynı yön; KÜÇÜK = daha iyi).
    dokuman: isteğe bağlı filtre, örn. "02_oncelik_rehberi".
    """
    global _depo
    if depo is None:
        _depo = _depo or vektor_deposu()
        depo = _depo
    filtre = {"dokuman": dokuman} if dokuman else None
    sonuc = depo.similarity_search_with_score(sorgu, k=k, filter=filtre)
    return [{"dokuman": d.metadata["dokuman"], "madde": d.metadata["madde"],
             "skor": float(s), "metin": d.page_content} for d, s in sonuc]
