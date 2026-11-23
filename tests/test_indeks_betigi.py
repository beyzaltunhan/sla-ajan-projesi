"""indeks_olustur.py betiği: Ollama/Chroma çağrılmadan (monkeypatch) davranışı doğrulanır."""
import indeks_olustur as ib


def test_dolu_klasore_dokunmaz(tmp_path, monkeypatch, capsys):
    (tmp_path / "x").write_text("a")
    monkeypatch.setattr("rag.indeks.indeks_olustur", lambda **k: (_ for _ in ()).throw(AssertionError("çağrılmamalı")))
    assert ib.calistir(False, tmp_path) == 0
    assert "dokunulmadı" in capsys.readouterr().out


def test_ollama_yoksa_anlasilir_hata(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ib, "ollama_hazir_mi", lambda: "Ollama'ya ulaşılamadı")
    assert ib.calistir(False, tmp_path / "yeni") == 1
    assert "HATA" in capsys.readouterr().out


def test_basarili_yol_parca_sayisini_yazar(tmp_path, monkeypatch, capsys):
    cagrilar = []
    monkeypatch.setattr(ib, "ollama_hazir_mi", lambda: None)
    monkeypatch.setattr("rag.indeks.indeks_olustur", lambda **k: cagrilar.append(k))
    hedef = tmp_path / "yeni"
    assert ib.calistir(False, hedef) == 0
    assert cagrilar == [{"db_dir": hedef, "sifirla": False}]
    cikti = capsys.readouterr().out
    assert "Tamam" in cikti and "parça" in cikti


def test_varsayilan_klasorde_sifirla_true(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(ib, "ollama_hazir_mi", lambda: None)
    monkeypatch.setattr(ib, "dolu_mu", lambda k: False)
    monkeypatch.setattr("rag.indeks.indeks_olustur", lambda **k: cagrilar.append(k))
    assert ib.calistir(False, None) == 0
    assert cagrilar == [{"db_dir": None, "sifirla": True}]
