"""Ajanın nihai çıktısı için Pydantic şeması (tasarim/karar_sirasi.md Bölüm 7-8).

Amaç: geçersiz ya da kendi içinde tutarsız bir çıktı yöneticiye/arayüze ulaşmasın.
Şema, sla_araclari.py'deki onay mantığını ayrıca çapraz kontrol eder.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

BILMIYORUM_YANITI = "Dokümanda bilgi bulunmamaktadır."

Davranis = Literal["HESAPLA", "SORU_SOR", "BILMIYORUM", "ENGELLE", "ONCELIK_BELIRLENEMEDI"]
Paket = Literal["standart", "gelismis", "kurumsal"]
Oncelik = Literal["P1", "P2", "P3", "P4"]
Risk = Literal["NORMAL", "YUKSEK", "IHLAL"]
OnayNedeni = Literal["p1_kritik", "ihlal", "yuksek_risk", "kredi_onerisi"]
Durum = Literal["TAMAMLANDI", "BEKLEMEDE", "ISLENEMEDI"]
Neden = Literal[
    "talimat_iceriyor",                                              # ENGELLE
    "kapsam_disi", "dokumanda_yok", "musteri_kayitsiz", "ozel_anlasma",  # BILMIYORUM
    "musteri_adi_eksik", "musteri_belirsiz", "oncelik_belirsiz",     # SORU_SOR
    "oncelik_belirlenemedi",                                         # ONCELIK_BELIRLENEMEDI
    "sema_hatasi",                                                   # ISLENEMEDI (hata yolu)
]

IZINLI_NEDENLER = {
    "ENGELLE": {"talimat_iceriyor"},
    "BILMIYORUM": {"kapsam_disi", "dokumanda_yok", "musteri_kayitsiz", "ozel_anlasma"},
    "SORU_SOR": {"musteri_adi_eksik", "musteri_belirsiz", "oncelik_belirsiz"},
    "ONCELIK_BELIRLENEMEDI": {"oncelik_belirlenemedi"},
}


class Kaynak(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dokuman: Literal["01_sla_sozlesmesi", "02_oncelik_rehberi",
                     "03_eskalasyon_proseduru", "04_destek_sss"]
    madde: str = Field(pattern=r"^(Soru )?\d+(\.\d+)?$")


class Kredi(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yuzde: float = Field(ge=0, le=100)
    tutar: float = Field(ge=0)
    neden: Literal["ihlal_yok", "paket_krediye_dahil_degil", "oncelik_krediye_dahil_degil",
                   "tavan_doldu", "tam_oran", "tavan_nedeniyle_azaltildi"]


class KararCiktisi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    davranis: Optional[Davranis] = None        # None yalnızca ISLENEMEDI'de
    neden: Optional[Neden] = None
    musteri: Optional[str] = None
    paket: Optional[Paket] = None
    oncelik: Optional[Oncelik] = None
    son_tarih: Optional[datetime] = None
    risk: Optional[Risk] = None
    kalan_dk: Optional[int] = Field(default=None, ge=0)   # risk_degerlendir kalan süre (dk); yalnızca HESAPLA
    kredi: Optional[Kredi] = None
    onay_gerekli: bool = False
    onay_nedenleri: list[OnayNedeni] = Field(default_factory=list)
    kaynaklar: list[Kaynak] = Field(default_factory=list)
    durum: Durum
    mesaj: str = Field(min_length=1)

    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _tutarlilik(self) -> "KararCiktisi":
        def hesap_alani_yok():
            dolu = [a for a in ("oncelik", "son_tarih", "risk", "kredi", "kalan_dk") if getattr(self, a) is not None]
            if dolu:
                raise ValueError(f"{self.davranis}: hesap alanı bulunamaz: {dolu}")
            if self.onay_gerekli or self.onay_nedenleri:
                raise ValueError(f"{self.davranis}: onay alanları boş olmalı")

        # --- hata yolu ---
        if self.davranis is None:
            if self.durum != "ISLENEMEDI" or self.neden != "sema_hatasi":
                raise ValueError("davranışsız çıktı yalnızca ISLENEMEDI/sema_hatasi olabilir")
            hesap_alani_yok()
            return self
        if self.durum == "ISLENEMEDI":
            raise ValueError("ISLENEMEDI durumunda davranış bulunamaz")

        # --- HESAPLA ---
        if self.davranis == "HESAPLA":
            if self.neden is not None:
                raise ValueError("HESAPLA için neden kodu kullanılmaz")
            eksik = [a for a in ("musteri", "paket", "oncelik", "son_tarih", "risk")
                     if getattr(self, a) is None]
            if eksik:
                raise ValueError(f"HESAPLA için zorunlu alanlar eksik: {eksik}")
            if not self.kaynaklar:
                raise ValueError("HESAPLA kaynak göstermek zorundadır")

            beklenen = []
            if self.oncelik == "P1":
                beklenen.append("p1_kritik")
            if self.risk == "IHLAL":
                beklenen.append("ihlal")
            elif self.risk == "YUKSEK":
                beklenen.append("yuksek_risk")
            if self.kredi is not None and self.kredi.yuzde > 0:
                beklenen.append("kredi_onerisi")

            if self.onay_gerekli != bool(beklenen):
                raise ValueError(f"onay_gerekli beklenenle uyuşmuyor (beklenen nedenler: {beklenen})")
            if set(self.onay_nedenleri) != set(beklenen) or len(self.onay_nedenleri) != len(beklenen):
                raise ValueError(f"onay_nedenleri beklenenle uyuşmuyor: {beklenen}")
            if self.durum != ("BEKLEMEDE" if self.onay_gerekli else "TAMAMLANDI"):
                raise ValueError("durum, onay_gerekli ile uyumsuz (onay varsa BEKLEMEDE, yoksa TAMAMLANDI)")
            return self

        # --- HESAPLA dışındaki tüm davranışlar ---
        hesap_alani_yok()
        if self.durum != "TAMAMLANDI":
            raise ValueError(f"{self.davranis}: durum TAMAMLANDI olmalı")
        if self.neden not in IZINLI_NEDENLER[self.davranis]:
            raise ValueError(f"{self.davranis}: geçersiz neden: {self.neden}")

        if self.davranis == "BILMIYORUM":
            if self.paket is not None:
                raise ValueError("BILMIYORUM: paket varsayılmaz")
            if self.kaynaklar:
                raise ValueError("BILMIYORUM: kaynak gösterilmez (sabit yanıt)")
            if self.mesaj != BILMIYORUM_YANITI:
                raise ValueError("BILMIYORUM: mesaj sabit yanıt olmalı")
        elif self.davranis == "SORU_SOR":
            if self.kaynaklar:
                raise ValueError("SORU_SOR: kaynak gösterilmez")
        elif self.davranis == "ENGELLE":
            if self.paket is not None or self.kaynaklar:
                raise ValueError("ENGELLE: paket ve kaynak bulunamaz")
        elif self.davranis == "ONCELIK_BELIRLENEMEDI":
            if self.musteri is None or self.paket is None:
                raise ValueError("ONCELIK_BELIRLENEMEDI: müşteri ve paket zorunlu")
            if not any(k.dokuman == "02_oncelik_rehberi" and k.madde == "8.3" for k in self.kaynaklar):
                raise ValueError("ONCELIK_BELIRLENEMEDI: Doküman 02 Madde 8.3 kaynak gösterilmeli")
        return self
