"""Demo öncesi temizlik: checkpoints.sqlite içindeki deneme thread'lerini (ve onlarla birlikte tutulan kredi/eskalasyon
KAYITLARINI; prototipte bunlar yalnızca bu veritabanındaki durumda tutulur) yedek alarak siler ve temiz bir kayıtla başlatır.
Yalnızca git'e girmeyen (yok sayılan) yerel dosyalara dokunur. Kullanım: python demo/sifirla.py [--evet]"""
import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

ADAY_DOSYALAR = ["checkpoints.sqlite", "checkpoints.sqlite-wal", "checkpoints.sqlite-shm", "checkpoints.db",
                 "checkpoints.db-wal", "checkpoints.db-shm"]


def git_yok_sayiyor_mu(dosya: Path, kok: Path = KOK) -> bool:
    """Dosya .gitignore ile yok sayılıyor mu? (git yoksa/hata varsa False: güvenli taraf)."""
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(dosya)], cwd=str(kok), capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def temizlenecekler(kok: Path = KOK, kontrol=git_yok_sayiyor_mu) -> tuple[list[Path], list[Path]]:
    """(silinecek, atlanan) — yalnızca var olan ve git tarafından yok sayılan dosyalar silinecekler arasına girer."""
    silinecek, atlanan = [], []
    for ad in ADAY_DOSYALAR:
        p = kok / ad
        if p.exists():
            (silinecek if kontrol(p, kok) else atlanan).append(p)
    return silinecek, atlanan


def yedekle(dosyalar: list[Path], yedek_kok: Path, zaman: datetime | None = None) -> Path:
    hedef = yedek_kok / f"{(zaman or datetime.now()):%Y%m%d-%H%M%S}"
    hedef.mkdir(parents=True, exist_ok=False)
    for d in dosyalar:
        shutil.copy2(d, hedef / d.name)
    return hedef


def sifirla(kok: Path = KOK, onay=lambda: True, kontrol=git_yok_sayiyor_mu, baslat=None) -> dict:
    """Önce yedek, sonra (onay verilirse) silme, sonra temiz kayıtla başlatma. Onay verilmezse hiçbir şey silinmez."""
    silinecek, atlanan = temizlenecekler(kok, kontrol)
    sonuc = {"silinecek": [p.name for p in silinecek], "atlanan": [p.name for p in atlanan], "yedek": None, "silindi": False}
    if not silinecek or not onay():
        return sonuc
    sonuc["yedek"] = str(yedekle(silinecek, kok / "demo" / "yedek"))
    for p in silinecek:
        p.unlink()
    sonuc["silindi"] = True
    if baslat:
        baslat()
    return sonuc


def _temiz_baslat():
    import ajan
    ajan.sqlite_checkpointer().setup()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evet", action="store_true", help="onay sormadan devam et")
    a = ap.parse_args(argv)
    silinecek, atlanan = temizlenecekler()
    print("Silinecek (git dışı, yerel):", [p.name for p in silinecek] or "—")
    if atlanan:
        print("ATLANDI (git tarafından yok sayılmıyor, dokunulmaz):", [p.name for p in atlanan])
    if not silinecek:
        print("Temizlenecek kayıt yok.")
        return 0

    def onay():
        return a.evet or input("Yedek alınıp silinecek. Devam edilsin mi? [e/H] ").strip().lower() in ("e", "evet", "y")
    r = sifirla(onay=onay, baslat=_temiz_baslat)
    if r["silindi"]:
        print(f"Yedek: {r['yedek']}\nSilindi ve temiz kayıt başlatıldı.")
    else:
        print("İptal edildi; hiçbir şey silinmedi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
