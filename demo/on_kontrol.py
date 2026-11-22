"""Demo öncesi ön kontrol: Ollama açık mı, modeller yüklü mü, ısındı mı, demo örnekleri uçtan uca çalışıyor mu (süreler,
tekrarlar arası tutarlılık). Ajana dokunmaz; geçici checkpoint kullanır.
Kullanım: python demo/on_kontrol.py [--tekrar 3] [--tumu]   (varsayılan: Demo 1 ve Demo 2, 3'er kez)"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from arayuz import bicimle as B  # noqa: E402


def imza(r: dict) -> tuple:
    """Tutarlılık için karşılaştırılan alanlar (süre/zaman hariç)."""
    s = r["sonuc"]
    c = s.get("cikti") or {}
    return (c.get("davranis"), c.get("neden"), c.get("oncelik"), c.get("risk"), c.get("onay_gerekli"), s["durum"])


def tutarlilik_ozeti(kosular: dict[str, list[dict]]) -> list[dict]:
    """{örnek: [çalıştırma, ...]} -> örnek başına özet (tutarlı mı, beklenen davranış, süreler)."""
    ozet = []
    for ad, liste in kosular.items():
        imzalar = [imza(r) for r in liste]
        sureler = [r["sonuc"]["toplam_sn"] for r in liste]
        ozet.append({"ad": ad, "tekrar": len(liste), "farkli": len(set(imzalar)), "tutarli": len(set(imzalar)) == 1,
                     "davranis": imzalar[0][0], "oncelik": imzalar[0][2], "beklenen": liste[0]["beklenen"],
                     "beklenen_dogru": all(i[0] == liste[0]["beklenen"] for i in imzalar),
                     "sure_ort": round(sum(sureler) / len(sureler), 1), "sure_maks": max(sureler)})
    return ozet


def tablo_yaz(ozet: list[dict]) -> str:
    satir = [f"{'Örnek':44} {'Davranış':22} {'Öncelik':8} {'Tekrar':7} {'Tutarlı':8} {'Beklenen':9} {'Ort sn':7} {'Maks sn':7}"]
    for o in ozet:
        satir.append(f"{o['ad'][:43]:44} {str(o['davranis']):22} {str(o['oncelik'] or '-'):8} {o['tekrar']:<7} "
                     f"{'EVET' if o['tutarli'] else 'HAYIR':8} {'EVET' if o['beklenen_dogru'] else 'HAYIR':9} "
                     f"{o['sure_ort']:<7} {o['sure_maks']:<7}")
    return "\n".join(satir)


def model_var_mi(model: str, yuklu: list[str]) -> bool:
    """'qwen3.5:4b' tam eşleşir; etiketsiz ad ('embeddinggemma') 'embeddinggemma:latest' ile eşleşir."""
    return any(a == model or (":" not in model and a.split(":")[0] == model) for a in yuklu)


def ollama_kontrol() -> list[tuple[str, bool, str]]:
    import ollama
    sonuc = []
    try:
        liste = ollama.Client(host=config.OLLAMA_URL).list()
        adlar = [m.model for m in liste.models]
        sonuc.append(("Ollama açık", True, config.OLLAMA_URL))
    except Exception as e:  # noqa: BLE001
        return [("Ollama açık", False, f"{type(e).__name__}: {e}")]
    for m in (config.CHAT_MODEL, config.EMBED_MODEL):
        var = model_var_mi(m, adlar)
        sonuc.append((f"Model yüklü: {m}", var, "" if var else "ollama pull ile indirin"))
    return sonuc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tekrar", type=int, default=3)
    ap.add_argument("--tumu", action="store_true", help="tüm hazır örnekleri çalıştır")
    a = ap.parse_args(argv)
    tamam = True
    print("== Ortam ==")
    for ad, ok, ayr in ollama_kontrol():
        print(f"[{'OK' if ok else 'HATA'}] {ad} {ayr}")
        tamam = tamam and ok
    if not tamam:
        print("Ollama/model sorunu; kontrol durduruldu.")
        return 1
    from arayuz import model
    from demo.calistir import gecici_graf, ornek_calistir
    i = model.isit()
    print(f"[{'OK' if i['durum'] == 'hazir' else 'HATA'}] Model ısındı: {i['ayrinti']} ({i['sure_sn']} sn)")
    if i["durum"] != "hazir":
        return 1
    adlar = list(B.ornekler(datetime.now())) if a.tumu else [B.DEMO1, B.DEMO2]
    klasor, _ = gecici_graf()
    kosular: dict[str, list[dict]] = {ad: [] for ad in adlar}
    try:
        sayac = 0
        for tur in range(a.tekrar):
            for ad in adlar:
                sayac += 1
                r = ornek_calistir(ad, sayac)
                kosular[ad].append(r)
                s = r["sonuc"]
                c = s["cikti"] or {}
                print(f"  tur {tur + 1} | {ad[:40]:40} | {c.get('davranis')} {c.get('oncelik') or ''} | "
                      f"{s['durum']} | {s['toplam_sn']} sn", flush=True)
    finally:
        klasor.cleanup()
    ozet = tutarlilik_ozeti(kosular)
    print("\n== Özet ==")
    print(tablo_yaz(ozet))
    ok = all(o["tutarli"] and o["beklenen_dogru"] for o in ozet)
    print("\nSONUÇ:", "demo hazır" if ok else "TUTARSIZLIK / BEKLENMEYEN DAVRANIŞ VAR")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
