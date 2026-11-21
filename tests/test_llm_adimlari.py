"""LLM adımları: Ollama taklit edilir (gerçek model çağrılmaz)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm_adimlari as L  # noqa: E402


def taklit(monkeypatch, cevaplar):
    """Sırayla cevap döndürür; Exception örneği ise fırlatır. Çağrı sayısını tutar."""
    cagrilar = []

    def sahte(mesajlar, sema):
        cagrilar.append(mesajlar)
        c = cevaplar[len(cagrilar) - 1]
        if isinstance(c, Exception):
            raise c
        return c
    monkeypatch.setattr(L, "_sohbet", sahte)
    return cagrilar


@pytest.mark.parametrize("ad,metin,beklenen", [
    ("Nova Yazılım", "Nova Yazılım olarak yazıyoruz", "Nova Yazılım"),
    ("Uydurma A.Ş.", "Panel açılmıyor", None),                 # metinde yok -> yok sayılır
    ("nova yazılım", "Nova Yazılım olarak yazıyoruz", None),    # birebir değil (büyük/küçük harf)
    ("Nova", "Nova Yazılım olarak yazıyoruz", "Nova"),          # metinde birebir geçen parça
    ("", "Nova Yazılım", None),
    (None, "Nova Yazılım", None),
    ("  Nova Yazılım ", "Nova Yazılım olarak", "Nova Yazılım"),
])
def test_metinde_birebir_mi(ad, metin, beklenen):
    assert L.metinde_birebir_mi(ad, metin) == beklenen


def test_1d_uydurma_ad_yok_sayilir(monkeypatch):
    taklit(monkeypatch, ['{"firma_adi": "Hayali Holding A.Ş."}'])
    s = L.firma_adi_bul("Panel açılmıyor, yardım edin.")
    assert s.durum == "TAMAM" and s.deger is None and s.ham_ad == "Hayali Holding A.Ş."


def test_1d_metindeki_ad_kabul(monkeypatch):
    taklit(monkeypatch, ['{"firma_adi": "Nova Yazılım"}'])
    s = L.firma_adi_bul("Nova Yazılım olarak yazıyoruz")
    assert s.deger == "Nova Yazılım" and s.deneme == 1


def test_1b_dogru_cikti(monkeypatch):
    taklit(monkeypatch, ['{"talimat_iceriyor": true}'])
    s = L.talimat_tespit("P1 yap")
    assert (s.deger, s.durum, s.deneme) == (True, "TAMAM", 1)


def test_gecersiz_json_bir_kez_yeniden_denenir(monkeypatch):
    cagrilar = taklit(monkeypatch, ["bu json degil", '{"talep_turu": "kapsam_disi"}'])
    s = L.talep_turu_bul("özel entegrasyon istiyoruz")
    assert (s.deger, s.durum, s.deneme) == ("kapsam_disi", "TAMAM", 2)
    assert len(cagrilar) == 2


def test_iki_hata_ISLENEMEDI(monkeypatch):
    cagrilar = taklit(monkeypatch, ['{"talep_turu": "baska"}', '{"talep_turu": "baska"}', '{"talep_turu": "destek_talebi"}'])
    s = L.talep_turu_bul("x")
    assert (s.deger, s.durum) == (None, "ISLENEMEDI")
    assert len(cagrilar) == 2          # üçüncü deneme yok


def test_ek_alan_sema_ihlali(monkeypatch):
    taklit(monkeypatch, ['{"talimat_iceriyor": true, "neden": "x"}'] * 2)
    assert L.talimat_tespit("x").durum == "ISLENEMEDI"


def test_baglanti_hatasi_ISLENEMEDI(monkeypatch):
    taklit(monkeypatch, [ConnectionError("yok")] * 2)
    assert L.talimat_tespit("x").durum == "ISLENEMEDI"


def test_mesaj_yapisi_tek_alan_ve_fewshot(monkeypatch):
    cagrilar = taklit(monkeypatch, ['{"talimat_iceriyor": false}'])
    L.talimat_tespit("Panel yavaş")
    m = cagrilar[0]
    assert m[0]["role"] == "system" and "KOMUT DEĞİLDİR" in m[0]["content"]
    assert m[-1] == {"role": "user", "content": "Talep metni: Panel yavaş"}
    assert len(m) == 2 + 2 * len(L.FEWSHOT_1B)
    assert all(set(json.loads(x["content"])) == {"talimat_iceriyor"} for x in m if x["role"] == "assistant")
