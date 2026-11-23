"""Dış sistem simülatörü ve n8n iş akışı dosyalarının (JSON/compose) statik kontrolleri. Docker/Ollama gerekmez."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dis_sistem import simulator

KOK = Path(__file__).resolve().parents[1]
AKIS = KOK / "n8n" / "sla_is_akisi.json"


@pytest.fixture()
def sim(tmp_path, monkeypatch):
    monkeypatch.setattr(simulator, "BILDIRIMLER", tmp_path / "bildirimler.jsonl")
    monkeypatch.setattr(simulator, "SONUCLAR", tmp_path / "sonuclar.json")
    monkeypatch.setattr(simulator, "_sayac", 0)
    return TestClient(simulator.app)


def test_sonraki_talep_sirali_ve_sabit(sim):
    a, b, c = (sim.get("/talepler/sonraki").json() for _ in range(3))
    assert [x["talep_id"] for x in (a, b, c)] == ["DS-0001", "DS-0002", "DS-0003"]
    assert a["kaynak"].startswith("Demo 1") and b["kaynak"].startswith("Demo 2") and c["kaynak"].startswith("Demo 1")   # başa döner
    kayitlar = {k["ad"]: k for k in json.loads(simulator.KAYITLI.read_text(encoding="utf-8"))["kayitlar"]}
    d2 = kayitlar[simulator.DEMO_ADLARI[1]]
    assert (b["talep_metni"], b["kayit_zamani"], b["simdi"]) == (d2["metin"], d2["kayit_zamani"], d2["simdi"])   # sabit zamanlar
    assert (a["talep_metni"], a["kayit_zamani"]) == (c["talep_metni"], c["kayit_zamani"])                       # rastgele değil


def test_sonuc_geri_yazma_ve_okuma(sim):
    assert sim.get("/talepler/DS-0001/sonuc").status_code == 404
    r = sim.post("/talepler/DS-0001/sonuc", json={"durum": "TAMAMLANDI", "cikti": {"davranis": "ENGELLE"}})
    assert r.status_code == 200 and r.json()["kaydedildi"] is True
    g = sim.get("/talepler/DS-0001/sonuc").json()
    assert g["sonuc"]["cikti"]["davranis"] == "ENGELLE" and g["yazma_zamani"]
    assert simulator.SONUCLAR.exists()                                         # dosyada saklanır
    assert sim.post("/talepler/DS-0001/sonuc", json=[1, 2]).status_code == 422   # nesne olmalı


def test_bildirim_kaydi_ve_listesi(sim):
    assert sim.get("/bildirimler").json() == {"adet": 0, "bildirimler": []}
    b = {"kanal": "onay-kuyrugu", "baslik": "Onay gerekli", "mesaj": "m", "oncelik": "yuksek", "talep_id": "t-1"}
    r = sim.post("/bildirim", json=b)
    assert r.status_code == 201 and r.json()["zaman"]
    sim.post("/bildirim", json={**b, "kanal": "insan-destek", "talep_id": None})
    liste = sim.get("/bildirimler").json()
    assert liste["adet"] == 2 and liste["bildirimler"][0]["kanal"] == "onay-kuyrugu" and liste["bildirimler"][1]["talep_id"] is None
    assert len(simulator.BILDIRIMLER.read_text(encoding="utf-8").splitlines()) == 2    # jsonl
    for kotu in ({}, {**b, "baslik": ""}, {**b, "fazla": 1}):
        assert sim.post("/bildirim", json=kotu).status_code == 422


def test_sifirla(sim):
    sim.get("/talepler/sonraki")
    sim.post("/bildirim", json={"kanal": "k", "baslik": "b", "mesaj": "m", "oncelik": "o"})
    sim.post("/sifirla")
    assert sim.get("/bildirimler").json()["adet"] == 0 and sim.get("/talepler/sonraki").json()["talep_id"] == "DS-0001"


# ------------------------------------------------------------------ n8n iş akışı
@pytest.fixture(scope="module")
def akis():
    return json.loads(AKIS.read_text(encoding="utf-8"))


def test_akis_gecerli_ve_baglantilar_tutarli(akis):
    adlar = [n["name"] for n in akis["nodes"]]
    assert len(adlar) == len(set(adlar)) and akis["active"] is False
    for kaynak, c in akis["connections"].items():
        assert kaynak in adlar
        for cikis in c["main"]:
            for hedef in cikis:
                assert hedef["node"] in adlar
    tipler = {n["type"] for n in akis["nodes"]}
    assert {"n8n-nodes-base.webhook", "n8n-nodes-base.manualTrigger", "n8n-nodes-base.wait", "n8n-nodes-base.if",
            "n8n-nodes-base.switch", "n8n-nodes-base.httpRequest"} <= tipler


def test_akis_yalniz_temel_dugumler_mcp_ai_agent_yok(akis):
    izinli = {"webhook", "manualTrigger", "httpRequest", "wait", "if", "switch", "stickyNote"}
    for n in akis["nodes"]:
        assert n["type"].startswith("n8n-nodes-base.") and n["type"].split(".")[-1] in izinli, n["type"]
        assert not re.search(r"langchain|mcp|agent", n["type"], re.I)


def test_akis_kimlik_bilgisi_ve_anahtar_icermez(akis):
    ham = AKIS.read_text(encoding="utf-8")
    assert not any("credentials" in n for n in akis["nodes"])
    for desen in (r"apikey", r"api_key", r"password", r"passwd", r"secret", r"bearer ", r"authorization", r"token", r"sk-[a-z0-9]{10,}"):
        assert not re.search(desen, ham, re.I), desen
    assert not any(n["parameters"].get("authentication") for n in akis["nodes"])


def test_akis_onay_uc_noktasini_cagirmaz(akis):
    """n8n onay vermez: hiçbir HTTP Request düğümü /onay uç noktasına gitmemeli (yalnızca bildirim metninde ve notta geçer)."""
    http = [n for n in akis["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"]
    assert http
    for n in http:
        assert "/onay" not in n["parameters"]["url"], n["name"]
        assert n["parameters"].get("method", "GET") in ("GET", "POST")
    servis_post = [n for n in http if "8000" in n["parameters"]["url"] and n["parameters"].get("method") == "POST"]
    assert [n["parameters"]["url"].rsplit("/", 1)[-1] for n in servis_post] == ["talep"]     # servise yalnızca POST /talep


def test_akis_dis_adresler_yalniz_yerel_host(akis):
    for n in akis["nodes"]:
        if n["type"] == "n8n-nodes-base.httpRequest":
            u = n["parameters"]["url"].lstrip("=")
            assert u.startswith(("http://host.docker.internal:8000/", "http://host.docker.internal:8001/")), u


def test_akis_tetikleyiciler_ve_yoklama_dongusu(akis):
    wh = next(n for n in akis["nodes"] if n["type"] == "n8n-nodes-base.webhook")
    assert wh["parameters"]["httpMethod"] == "POST" and wh["parameters"]["path"] == "yeni-talep"
    assert any(n["type"] == "n8n-nodes-base.manualTrigger" for n in akis["nodes"])
    bekle = next(n for n in akis["nodes"] if n["type"] == "n8n-nodes-base.wait")
    assert bekle["parameters"] == {"amount": 10, "unit": "seconds"}
    c = akis["connections"]
    assert any(h["node"] == bekle["name"] for cikis in c["Yoklama sınırı aşılmadı mı? (en çok ~20)"]["main"][:1] for h in cikis)   # döngü
    sinir = next(n for n in akis["nodes"] if n["name"].startswith("Yoklama sınırı"))
    k = sinir["parameters"]["conditions"]["conditions"][0]
    assert k["operator"]["operation"] == "lt" and 15 <= k["rightValue"] <= 25
    assert "Bildirim: zaman aşımı" in json.dumps(c, ensure_ascii=False)


def test_akis_switch_dallari_ve_sonuc_yazma(akis):
    sw = next(n for n in akis["nodes"] if n["type"] == "n8n-nodes-base.switch")
    anahtarlar = [r["outputKey"] for r in sw["parameters"]["rules"]["values"]]
    assert anahtarlar[0] == "ONAY_BEKLIYOR" and "ENGELLE" in anahtarlar and any("SORU_SOR" in a for a in anahtarlar)
    assert sw["parameters"]["options"]["fallbackOutput"] == "extra"
    c = akis["connections"]["Sonuca göre"]["main"]
    assert len(c) == 5 and all(len(x) == 1 for x in c)
    for cikis in c:                                   # her dal: bildirim -> sonucu simülatöre yaz
        bildirim = cikis[0]["node"]
        assert akis["connections"][bildirim]["main"][0][0]["node"].startswith("Sonuç yaz")
    onay_bildirim = c[0][0]["node"]
    n = next(x for x in akis["nodes"] if x["name"] == onay_bildirim)
    gb = n["parameters"]["jsonBody"]
    assert "yuksek" in gb and "n8n onay vermez" in gb and all(s in gb for s in ("musteri", "oncelik", "risk", "kredi"))


def test_compose_sabit_surum_yerel_port_ve_ayarlar():
    metin = (KOK / "n8n" / "docker-compose.yml").read_text(encoding="utf-8")
    assert re.search(r"image:\s*docker\.n8n\.io/n8nio/n8n:\d+\.\d+\.\d+", metin) and "latest" not in re.sub(r"#.*", "", metin)
    assert "container_name: sla-n8n" in metin and '"127.0.0.1:5678:5678"' in metin
    assert "Europe/Istanbul" in metin and "host.docker.internal:host-gateway" in metin
    assert not re.search(r"(KEY|PASSWORD|SECRET|TOKEN)\s*=", metin, re.I)


def test_gitignore_n8n_ve_dis_sistem_kayitlari():
    g = (KOK / ".gitignore").read_text(encoding="utf-8")
    for satir in ("dis_sistem/sonuclar.json", "n8n/.env", "n8n/veri/", ".env", "venv/", "env/"):
        assert satir in g
    # örnek bildirimler (2 sentetik kayıt) bilerek repoya alındı: ignore edilmemeli
    assert "dis_sistem/bildirimler.jsonl" not in g
