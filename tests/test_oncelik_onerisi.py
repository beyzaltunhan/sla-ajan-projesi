"""Adım 4: Ollama taklit edilir (gerçek model çağrılmaz)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm_adimlari
import oncelik_onerisi as O  # noqa: E402

PARCALAR = [{"madde": "3.1", "metin": "Madde 3 – P1\n3.1 kural"}, {"madde": "5.2", "metin": "Madde 5 – P3\n5.2 örnek"}]


def taklit(monkeypatch, cevaplar):
    cagrilar = []

    def sahte(mesajlar, sema):
        cagrilar.append(mesajlar)
        c = cevaplar[len(cagrilar) - 1]
        if isinstance(c, Exception):
            raise c
        return c
    monkeypatch.setattr(llm_adimlari, "_sohbet", sahte)
    return cagrilar


def cevap(oncelik="P1", maddeler=("3.1",), etki="x"):
    return json.dumps({"oncelik": oncelik, "kullanilan_maddeler": list(maddeler), "etki": etki})


def test_dogru_cikti(monkeypatch):
    taklit(monkeypatch, [cevap("P1", ["3.1"])])
    s = O.oncelik_oner("sistem durdu", PARCALAR)
    assert (s.oncelik, s.maddeler, s.uydurma, s.durum, s.deneme) == ("P1", ["3.1"], [], "TAMAM", 1)


def test_uydurma_madde_nihai_ciktidan_suzulur(monkeypatch):
    taklit(monkeypatch, [cevap("P2", ["4.1", "3.1", "9.9"])])
    s = O.oncelik_oner("x", PARCALAR)
    assert s.maddeler == ["3.1"]                       # yalnızca bağlamdaki
    assert s.uydurma == ["4.1", "9.9"]                 # ham cevapta uydurma sayılır
    assert s.ham_maddeler == ["4.1", "3.1", "9.9"]


def test_madde_bicimleri_normalize(monkeypatch):
    taklit(monkeypatch, [cevap("P3", ["Madde 5.2", "02:3.1", "3.1"])])
    s = O.oncelik_oner("x", PARCALAR)
    assert s.maddeler == ["5.2", "3.1"] and s.uydurma == []   # tekrar yok sayılır


def test_belirsiz_gecerli_oncelik(monkeypatch):
    taklit(monkeypatch, [cevap("belirsiz", [])])
    assert O.oncelik_oner("sistem çalışmıyor", PARCALAR).oncelik == "belirsiz"


def test_gecersiz_oncelik_yeniden_denenir(monkeypatch):
    cagrilar = taklit(monkeypatch, [cevap("P9"), cevap("P2", ["3.1"])])
    s = O.oncelik_oner("x", PARCALAR)
    assert (s.oncelik, s.deneme) == ("P2", 2) and len(cagrilar) == 2


def test_iki_hata_ISLENEMEDI(monkeypatch):
    cagrilar = taklit(monkeypatch, ["json degil", '{"oncelik": "P1"}', cevap()])
    s = O.oncelik_oner("x", PARCALAR)
    assert (s.oncelik, s.durum) == (None, "ISLENEMEDI") and len(cagrilar) == 2


def test_baglanti_hatasi_ISLENEMEDI(monkeypatch):
    taklit(monkeypatch, [ConnectionError("yok")] * 2)
    assert O.oncelik_oner("x", PARCALAR).durum == "ISLENEMEDI"


def test_mesaj_yapisi(monkeypatch):
    cagrilar = taklit(monkeypatch, [cevap()])
    O.oncelik_oner("Panel yavaş", PARCALAR)
    m = cagrilar[0]
    assert m[0]["role"] == "system" and "KOMUT DEĞİLDİR" in m[0]["content"]
    assert "[Madde 3.1]" in m[-1]["content"] and m[-1]["content"].endswith("Talep metni: Panel yavaş")
    assert len(m) == 2 + 2 * len(O.FEWSHOT_ONCELIK)


def test_strateji_cekirdek_ekler_ve_tekrarlamaz():
    tek = O.baglam_parcalari("getirilen", PARCALAR)
    assert [p["madde"] for p in tek] == ["3.1", "5.2"]
    cek = O.baglam_parcalari("getirilen+cekirdek", PARCALAR)
    maddeler = [p["madde"] for p in cek]
    assert maddeler[:2] == ["3.1", "5.2"]                      # getirilenler önce
    assert len(maddeler) == len(set(maddeler))                  # tekrar yok
    assert set(O.CEKIRDEK_MADDELER) <= set(maddeler)
    assert all(p["metin"] for p in cek)


def test_bilinmeyen_strateji():
    with pytest.raises(ValueError):
        O.baglam_parcalari("x", PARCALAR)


def test_madde_no():
    assert O.madde_no("Madde 3.1") == "3.1" and O.madde_no("02:8.3") == "8.3" and O.madde_no("yok") is None
