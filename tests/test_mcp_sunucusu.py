"""MCP sunucusu: süreç içinde gerçek bir MCP istemci oturumuyla (bellek içi taşıma) test edilir. Ollama gerekmez."""
import asyncio
import json

from mcp.shared.memory import create_connected_server_and_client_session

import mcp_sunucusu


def _calistir(korutin_fn):
    async def ana():
        async with create_connected_server_and_client_session(mcp_sunucusu.mcp._mcp_server) as istemci:
            return await korutin_fn(istemci)
    return asyncio.run(ana())


def _cagir(arac, **arg):
    async def f(i):
        return await i.call_tool(arac, arg)
    return _calistir(f)


def _sonuc(r) -> dict:
    assert not r.isError, r.content
    return json.loads(r.content[0].text)


def test_dort_arac_listelenir_ve_aciklamalari_var():
    async def f(i):
        return await i.list_tools()
    araclar = {t.name: t for t in _calistir(f).tools}
    assert set(araclar) == {"musteri_ara", "son_tarih_hesapla", "risk_degerlendir", "kredi_hesapla"}
    for t in araclar.values():
        assert len(t.description) > 80
        assert t.inputSchema["properties"]
    assert araclar["son_tarih_hesapla"].inputSchema["properties"]["paket"]["enum"] == ["standart", "gelismis", "kurumsal"]


def test_musteri_ara_dogru():
    r = _sonuc(_cagir("musteri_ara", ad="marmara perakende"))
    assert r["durum"] == "TEK" and r["kayit"]["ad"] == "Marmara Perakende A.Ş." and r["kayit"]["paket"] == "kurumsal"
    assert r["kayit"]["aylik_ucret"] == 90000
    assert _sonuc(_cagir("musteri_ara", ad="Anadolu"))["durum"] == "BELIRSIZ"
    assert _sonuc(_cagir("musteri_ara", ad="Zümrüt Bilişim")) == {"durum": "YOK", "kayit": None}
    assert _sonuc(_cagir("musteri_ara", ad="  "))["durum"] == "BOS"


def test_son_tarih_elle_dogrulanmis():
    # Kurumsal P2 = 2 saat (mesai). Perşembe 19.11.2026 10:00 -> aynı gün 12:00
    r = _sonuc(_cagir("son_tarih_hesapla", talep_zamani="2026-11-19T10:00:00", paket="kurumsal", oncelik="P2"))
    assert r["son_tarih"] == "2026-11-19T12:00:00" and r["takvim"] == "mesai" and r["sure_dk"] == 120
    # Mesai dışı: Perşembe 17:00 + 2 saat mesai = 1 saat (17-18) + ertesi gün (Cuma) 09:00-10:00
    r = _sonuc(_cagir("son_tarih_hesapla", talep_zamani="2026-11-19T17:00:00", paket="kurumsal", oncelik="P2"))
    assert r["son_tarih"] == "2026-11-20T10:00:00"
    # Kurumsal P1: 7/24, 1 saat
    r = _sonuc(_cagir("son_tarih_hesapla", talep_zamani="2026-11-21T23:30:00", paket="kurumsal", oncelik="P1"))
    assert r["takvim"] == "7/24" and r["son_tarih"] == "2026-11-22T00:30:00"


def test_risk_sinirlari_elle_dogrulanmis():
    kos = dict(talep_zamani="2026-11-19T10:00:00", paket="kurumsal", oncelik="P2")   # son tarih 12:00, toplam 120 dk
    assert _sonuc(_cagir("risk_degerlendir", simdi="2026-11-19T11:30:00", **kos))["risk"] == "NORMAL"   # tam %25 kalan
    r = _sonuc(_cagir("risk_degerlendir", simdi="2026-11-19T11:31:00", **kos))
    assert r["risk"] == "YUKSEK" and r["kalan_dk"] == 29
    assert _sonuc(_cagir("risk_degerlendir", simdi="2026-11-19T12:00:00", **kos))["risk"] != "IHLAL"   # bitiş anı ihlal değil
    r = _sonuc(_cagir("risk_degerlendir", simdi="2026-11-19T12:01:00", **kos))
    assert r["risk"] == "IHLAL" and r["asim_dk"] == 1 and r["kalan_dk"] == 0


def test_kredi_elle_dogrulanmis():
    r = _sonuc(_cagir("kredi_hesapla", paket="kurumsal", oncelik="P2", ihlal_var=True, aylik_ucret=90000))
    assert r == {"yuzde": 2.0, "tutar": 1800.0, "neden": "tam_oran"}
    r = _sonuc(_cagir("kredi_hesapla", paket="gelismis", oncelik="P1", ihlal_var=True, aylik_ucret=30000, bu_ay_uygulanan_yuzde=10))
    assert r["yuzde"] == 0 and r["neden"] == "tavan_doldu"
    assert _sonuc(_cagir("kredi_hesapla", paket="standart", oncelik="P1", ihlal_var=True, aylik_ucret=1000))["neden"] == "paket_krediye_dahil_degil"
    assert _sonuc(_cagir("kredi_hesapla", paket="kurumsal", oncelik="P2", ihlal_var=False, aylik_ucret=90000))["neden"] == "ihlal_yok"


def test_hatali_girdi_anlasilir_hata():
    r = _cagir("son_tarih_hesapla", talep_zamani="dün akşam", paket="kurumsal", oncelik="P2")
    assert r.isError and "ISO 8601" in r.content[0].text and "dün akşam" in r.content[0].text
    r = _cagir("son_tarih_hesapla", talep_zamani="2026-11-19T10:00:00+03:00", paket="kurumsal", oncelik="P2")
    assert r.isError and "saat dilimi" in r.content[0].text
    r = _cagir("son_tarih_hesapla", talep_zamani="2026-11-19T10:00:00", paket="platin", oncelik="P2")
    assert r.isError and "platin" in r.content[0].text
    r = _cagir("risk_degerlendir", talep_zamani="2026-11-19T10:00:00", simdi="yarın", paket="kurumsal", oncelik="P2")
    assert r.isError and "simdi" in r.content[0].text
    r = _cagir("kredi_hesapla", paket="kurumsal", oncelik="P2", ihlal_var=True, aylik_ucret=-5)
    assert r.isError and "negatif" in r.content[0].text
    r = _cagir("kredi_hesapla", paket="kurumsal", oncelik="P2", ihlal_var=True, aylik_ucret=100, bu_ay_uygulanan_yuzde=150)
    assert r.isError and "0-100" in r.content[0].text
    r = _cagir("musteri_ara")                    # zorunlu parametre eksik
    assert r.isError


def test_sarmalayici_mantik_kopyalamaz():
    import inspect
    kaynak = inspect.getsource(mcp_sunucusu)
    assert "timedelta" not in kaynak and "s.son_tarih_hesapla(" in kaynak and "s.kredi_hesapla(" in kaynak


def test_stdio_alt_surec_gercek_calistirma():
    """`python mcp_sunucusu.py` komutuyla ayrı süreç olarak başlatılır, stdio üzerinden araç çağrılır."""
    import sys
    from pathlib import Path
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def ana():
        p = StdioServerParameters(command=sys.executable, args=[str(Path(mcp_sunucusu.__file__))],
                                  cwd=str(Path(mcp_sunucusu.__file__).parent))
        async with stdio_client(p) as (o, y):
            async with ClientSession(o, y) as i:
                await i.initialize()
                adlar = {t.name for t in (await i.list_tools()).tools}
                r = await i.call_tool("kredi_hesapla", {"paket": "kurumsal", "oncelik": "P2", "ihlal_var": True, "aylik_ucret": 90000})
                return adlar, json.loads(r.content[0].text)
    adlar, kredi = asyncio.run(asyncio.wait_for(ana(), 60))
    assert len(adlar) == 4 and kredi["tutar"] == 1800.0
