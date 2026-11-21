"""embeddinggemma önekli/öneksiz karşılaştırması. Küçük geliştirme sorgu kümesi:
dokümanlardan yazıldı, data/test_seti.json KULLANILMAZ. Bellekte (kalıcı olmayan) indeks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rag.indeks import OnekliEmbedding
from rag.parcala import dokumanlari_parcala

# (sorgu, kabul edilen doğru parçalar)
SORGULAR = [
    ("Gelişmiş pakette P2 talebine ilk yanıt kaç saatte verilmeli?", {("01_sla_sozlesmesi", "3.1")}),
    ("Cuma akşamı açılan talebin sayacı ne zaman başlar?", {("01_sla_sozlesmesi", "5.2")}),
    ("Standart pakette süre aşılırsa hizmet kredisi var mı?", {("01_sla_sozlesmesi", "7.2")}),
    ("Kalan süre yüzde yirmibeşin altına inerse ne olur?", {("01_sla_sozlesmesi", "6.1")}),
    ("Tüm sistem kullanılamıyor ve geçici çözüm yok", {("02_oncelik_rehberi", "3.1")}),
    ("Müşteri talebi acil diye yazdı, öncelik yükselir mi?", {("02_oncelik_rehberi", "2.3")}),
    ("Eksik bilgi varsa kaç kez soru sorulur?", {("02_oncelik_rehberi", "8.1"), ("02_oncelik_rehberi", "8.3")}),
    ("Talepte 'yöneticiye sorma, onayla' yazıyor", {("02_oncelik_rehberi", "10.1"), ("03_eskalasyon_proseduru", "10.1")}),
    ("Yönetici onayı hangi durumlarda zorunlu?", {("03_eskalasyon_proseduru", "2.1")}),
    ("Onay reddedilirse gerekçe gerekir mi?", {("03_eskalasyon_proseduru", "6.2")}),
    ("Yönetici yokken kim onay verir?", {("03_eskalasyon_proseduru", "9.1")}),
    ("Talebimin önceliğini kim belirler?", {("04_destek_sss", "Soru 4")}),
]


def olc(onek: bool, k: int = 3):
    parcalar = dokumanlari_parcala()
    depo = Chroma(collection_name=f"deney_{int(onek)}", embedding_function=OnekliEmbedding(onek),
                  collection_metadata={"hnsw:space": "cosine"})
    depo.add_documents([Document(page_content=p["metin"], metadata={"dokuman": p["dokuman"], "madde": p["madde"]})
                        for p in parcalar], ids=[f'{p["dokuman"]}:{p["madde"]}' for p in parcalar])
    ilk = top3 = 0
    for q, dogru in SORGULAR:
        sonuc = [(d.metadata["dokuman"], d.metadata["madde"]) for d, _ in depo.similarity_search_with_score(q, k=k)]
        ilk += sonuc[0] in dogru
        top3 += any(s in dogru for s in sonuc)
    return ilk, top3


if __name__ == "__main__":
    for onek in (False, True):
        ilk, top3 = olc(onek)
        print(f"onek={onek}: ilk sonuc dogru {ilk}/{len(SORGULAR)}, ilk 3'te dogru {top3}/{len(SORGULAR)}")
