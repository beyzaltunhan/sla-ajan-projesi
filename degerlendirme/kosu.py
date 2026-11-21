"""59 talepli (T01-T59) ölçüm koşusu: her talebi ajana verir, ham sonucu JSONL'e ekler (kesintiye dayanıklı).

Kullanım:
  python degerlendirme/kosu.py                       # tam koşu -> sonuclar/ilk_kosu_ham.jsonl (tamamlananları atlar)
  python degerlendirme/kosu.py --ids T01,T19 --cikti <yol> --ilerleme <yol>   # kısa deneme

Kurallar: her talep için test_seti.json'daki kayit_zamani ve simdi kullanılır; her talep ayrı thread_id;
onay gerektirenler BEKLEMEDE kalır (OTOMATİK ONAY YOK). "soru zaten soruldu" bilgisi metinden çıkarılamaz;
test setinde 'iki_tur' etiketli talepler için soru_soruldu=True verilir (konuşma durumu girdisi, model görmez).
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
import ajan  # noqa: E402
import config  # noqa: E402

ARA_ALANLAR = ["musteri_durum", "musteri", "talimat", "talep_turu", "firma_adi", "firma_1d_yapildi", "yon", "neden",
               "oncelik", "oncelik_maddeleri", "etki", "hesap"]


def git_ozet() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=KOK, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "kirli": bool(g("status", "--porcelain"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=None)
    ap.add_argument("--cikti", default=str(KOK / "sonuclar" / "ilk_kosu_ham.jsonl"))
    ap.add_argument("--ilerleme", default=str(KOK / "sonuclar" / "ilk_kosu_ilerleme.txt"))
    a = ap.parse_args()
    cikti, ilerleme = Path(a.cikti), Path(a.ilerleme)
    talepler = json.loads((config.DATA_DIR / "test_seti.json").read_text(encoding="utf-8"))["talepler"]
    if a.ids:
        secili = set(a.ids.split(","))
        talepler = [t for t in talepler if t["id"] in secili]
    biten = set()
    if cikti.exists():
        biten = {json.loads(s)["id"] for s in cikti.read_text(encoding="utf-8").splitlines() if s.strip() and '"_meta"' not in s}
    else:
        cikti.write_text(json.dumps({"_meta": {**git_ozet(), "tarih": datetime.now().isoformat(timespec="seconds"),
                                              "chat_model": config.CHAT_MODEL, "embed_model": config.EMBED_MODEL,
                                              "strateji": ajan.STRATEJI}}, ensure_ascii=False) + "\n", encoding="utf-8")
    ajan.graf(yeni=True, checkpointer=ajan.sqlite_checkpointer(Path(tempfile.mkdtemp()) / "kosu.sqlite"))

    def yaz(p: Path, satir: str):
        with p.open("a", encoding="utf-8") as f:
            f.write(satir + "\n")

    kalan = [t for t in talepler if t["id"] not in biten]
    yaz(ilerleme, f"# {datetime.now().isoformat(timespec='seconds')} basladi: {len(kalan)} talep kaldi ({len(biten)} atlandi)")
    for t in kalan:
        soru = "iki_tur" in t["etiket"]
        t0 = time.perf_counter()
        kayit = {"id": t["id"], "set": t["set"], "yazar": t["yazar"], "soru_soruldu": soru}
        try:
            r = ajan.talep_isle(t["talep_metni"], t["kayit_zamani"], t["simdi"], f"ilk-kosu-{t['id']}", soru_soruldu=soru)
            durum = ajan.graf().get_state({"configurable": {"thread_id": f"ilk-kosu-{t['id']}"}}).values
            kayit.update({"durum": r["durum"], "cikti": r["cikti"], "onay_sonucu": r["onay_sonucu"],
                          "bekleyen_onay": bool(r["bekleyen_onay"]), "adim_sureleri": r["adim_sureleri"], "hata": r["hata"],
                          "ara": {k: durum.get(k) for k in ARA_ALANLAR}})
        except Exception as e:  # harness/ajan istisnası da kaydedilir
            kayit.update({"durum": "ISTISNA", "istisna": f"{type(e).__name__}: {e}"})
        kayit["toplam_sn"] = round(time.perf_counter() - t0, 3)
        kayit["zaman"] = datetime.now().isoformat(timespec="seconds")
        yaz(cikti, json.dumps(kayit, ensure_ascii=False, default=str))
        yaz(ilerleme, f"{kayit['zaman']} {t['id']} {kayit['durum']} {((kayit.get('cikti') or {}).get('davranis'))} {kayit['toplam_sn']}s")
    yaz(ilerleme, f"# {datetime.now().isoformat(timespec='seconds')} bitti")


if __name__ == "__main__":
    main()
