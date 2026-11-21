"""RAG katmanı birim testleri (Ollama/Chroma gerektirmez)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from rag.arama import retrieve
from rag.indeks import indeksi_sifirla
from rag.parcala import dokumanlari_parcala
from schemas.onay_paketi import Kaynak

PARCALAR = dokumanlari_parcala()


def test_parca_sayilari():
    sayi = {}
    for p in PARCALAR:
        sayi[p["dokuman"]] = sayi.get(p["dokuman"], 0) + 1
    assert len(PARCALAR) == 87
    assert sayi == {"01_sla_sozlesmesi": 27, "02_oncelik_rehberi": 28,
                    "03_eskalasyon_proseduru": 22, "04_destek_sss": 10}


def test_parca_kaynak_semasina_uyar():
    for p in PARCALAR:
        Kaynak(dokuman=p["dokuman"], madde=p["madde"])  # geçersizse ValidationError


def test_parca_kimlikleri_tekil_ve_metin_dolu():
    ids = [(p["dokuman"], p["madde"]) for p in PARCALAR]
    assert len(ids) == len(set(ids))
    assert all(p["metin"].startswith(p["baslik"]) and len(p["metin"]) > len(p["baslik"]) + 5 for p in PARCALAR)


def test_kunye_satirlari_indekslenmez():
    assert not any("KURGUSAL DOKÜMAN" in p["metin"] or "Doküman No:" in p["metin"] for p in PARCALAR)


def test_tablo_hukmun_icinde_kalir():
    p = next(x for x in PARCALAR if (x["dokuman"], x["madde"]) == ("01_sla_sozlesmesi", "3.1"))
    assert "| Kurumsal |" in p["metin"]


class _SahteDepo:
    def __init__(self):
        self.cagri = None

    def similarity_search_with_score(self, sorgu, k, filter=None):
        from langchain_core.documents import Document
        self.cagri = (sorgu, k, filter)
        return [(Document(page_content="Madde 3 – X\n3.1 ...", metadata={"dokuman": "01_sla_sozlesmesi", "madde": "3.1"}), 0.25)]


def test_retrieve_cikti_semasi_ve_filtre():
    depo = _SahteDepo()
    sonuc = retrieve("soru", k=5, dokuman="02_oncelik_rehberi", depo=depo)
    assert depo.cagri == ("soru", 5, {"dokuman": "02_oncelik_rehberi"})
    assert set(sonuc[0]) == {"dokuman", "madde", "skor", "metin"}
    assert isinstance(sonuc[0]["skor"], float)
    Kaynak(dokuman=sonuc[0]["dokuman"], madde=sonuc[0]["madde"])


def test_retrieve_varsayilan_k_5_ve_filtresiz():
    depo = _SahteDepo()
    retrieve("soru", depo=depo)
    assert depo.cagri == ("soru", 5, None)


def test_sifirla_baska_yolu_reddeder(tmp_path):
    hedef = tmp_path / "onemli"
    hedef.mkdir()
    with pytest.raises(ValueError):
        indeksi_sifirla(hedef)
    assert hedef.exists()
