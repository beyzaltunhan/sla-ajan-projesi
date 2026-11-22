"""Adım 4 (kaynaklı öncelik önerisi) GELİŞTİRME seti ve ayrı FEW-SHOT örnekleri.

Etiket: P1 / P2 / P3 / P4 / belirsiz — Doküman 02 kurallarından (3.1, 4.1, 5.1, 6.1, 7.x, 8.1).
Metinler data/test_seti.json'dan kopyalanmamıştır (tests/test_gelistirme_seti_oncelik.py kontrol eder).
İlk 15 örnek deneme/gelistirme_sorgulari.py'deki retrieval geliştirme sorgularıdır (öncelik etiketiyle tamamlandı).
"""
from deneme.gelistirme_sorgulari import SORGULAR as _RET

_ILK15_ETIKET = ["P1"] * 4 + ["P2"] * 4 + ["P3"] * 4 + ["P4"] * 3

GELISTIRME_ONCELIK = [(q, e) for (q, _), e in zip(_RET[:15], _ILK15_ETIKET)] + [
    # "acil" tuzağı (ifade önceliği yükseltmez, 2.3)
    ("ACİL!!! Rapor çıktısındaki tarih biçimi ters görünüyor, elle düzeltip kullanıyoruz ama çok önemli, hemen bakın.", "P3"),
    ("Acil acil acil, dil ayarının nerede olduğunu öğrenmem lazım! Sistemde bir sorun yok.", "P4"),
    ("Hemen bakın, çok önemli: tüm sistem açılmıyor, kimse giriş yapamıyor ve başka yolumuz yok.", "P1"),
    # kullanıcı sayısı yok / geçici çözüm
    ("Nehir Spor: belirli bir işlem sırasında hata alıyoruz, kaç kişinin etkilendiğini bilmiyorum ama kolay bir geçici çözümü var.", "P3"),
    ("Kale Yapı: tüm sistem durmuştu ama eski sürüme geçerek çalıştırabiliyoruz, geçici çözüm hazır.", "P2"),
    ("Orhan Ticaret'te fatura modülünün yalnızca bir bölümü çalışmıyor; ama kolay bir geçici yöntemle devam ediyoruz.", "P3"),
    # P2
    ("Çalışanlarımızın çoğu depo uygulamasına bağlanamıyor, tarayıcıdan da denedik, olmadı.", "P2"),
    ("Sipariş ekranı o kadar yavaş ki gün içinde sipariş girmek çok zor, başka bir yolumuz yok.", "P2"),
    # P1 veri / güvenlik
    ("Yanlışlıkla silinen kayıtlar için geri yükleme çalışmıyor, müşteri verilerimiz kayıp ve dönüş yolu yok.", "P1"),
    ("Hesabımıza yabancı biri girmiş görünüyor, yetkisiz işlemler yapılmış, güvenlik riski var.", "P1"),
    # belirsiz
    ("Sistem çalışmıyor, yardım edin.", "belirsiz"),
    ("Bir şey bozuldu, bakar mısınız?", "belirsiz"),
    ("Uygulama bugün tuhaf davranıyor, çok sinir bozucu.", "belirsiz"),
    ("Giriş sorunu var galiba.", "belirsiz"),
    # P4 / P3
    ("Faturalarımızı toplu indirmenin bir yolu var mı? Sistemde bir problem yok, sadece merak ettim.", "P4"),
    ("Bir çalışanımız şifre e-postasını alamıyor, ekranda görüntüleyebiliyor; diğer kullanıcılarda sorun yok.", "P3"),
]

# Few-shot (geliştirme setinden AYRI)
FEWSHOT_ONCELIK = [
    ("Üretim ortamımız durdu, hiçbir kullanıcı sisteme giremiyor ve elimizde başka bir çözüm yok.", "P1"),
    ("Tahsilat ekranı hata veriyor, başka yoldan tahsilat yapamıyoruz, diğer ekranlar çalışıyor.", "P2"),
    ("Listede bir sütunun adı yanlış, elle düzeltip devam ediyoruz, yalnızca iki kişi kullanıyor.", "P3"),
    ("Kullanıcı profilinde şifre nasıl değiştirilir? Sistem normal çalışıyor.", "P4"),
    ("ÇOK ACİL, HEMEN! Ana sayfadaki logo biraz kaymış, işimiz aksamıyor.", "P3"),
    ("Çalışmıyor, bakın lütfen.", "belirsiz"),
    ("Sevk planı ekranındaki kaydet düğmesi hata veriyor, planı e-postayla ileterek işi yürütüyoruz, diğer ekranlar çalışıyor.", "P3"),
    ("Müşteri kayıt modülü çalışmıyor, yeni müşteri ekleyemiyoruz ve başka bir yolumuz yok; sistemin diğer bölümleri sağlam.", "P2"),
]


# ---------------------------------------------------------------- Düzeltme turu (22 Kasım 2026)
# Yeni özgün örnekler (ilk koşudaki hata KATEGORİSİNDEN esinlenildi; test metinleri kopyalanmadı/uyarlanmadı).
# (metin, öncelik, grup)  grup: gecici_cozum (6: P3, biri P4 tuzağı) | gecici_cozum_yok (4: P2; aşırı düzeltmeyi yakalar)
GELISTIRME_ONCELIK_YENI = [
    ("Ilgın Boya olarak yazıyoruz: müşteri bakiye raporunda bir sütunun toplamı hatalı çıkıyor, hesap makinesiyle kontrol edip devam ediyoruz, diğer ekranlar normal.", "P3", "gecici_cozum"),
    ("Sevkiyat çıktısı ekranı bugün açılmıyor ama depodan gelen dosyadan elle çıktı alıp işi sürdürüyoruz, yalnızca iki kişi kullanıyor. Bulut Kâğıt.", "P3", "gecici_cozum"),
    ("Çiçek Market: ödeme özeti sayfasında tutar bazen sıfır görünüyor, sayfayı yenileyince düzeliyor, satışlarımız etkilenmiyor.", "P3", "gecici_cozum"),
    ("Dağ Elektrik, fatura gönderme düğmesi çalışmıyor; faturaları e-postayla gönderip kayda elle işliyoruz, bu yol bize sorun olmuyor.", "P3", "gecici_cozum"),
    ("Kumsal Otel: stok sayım ekranı çok yavaş açılıyor, yirmi saniye kadar bekleyince açılıyor ve işimiz aksamıyor.", "P3", "gecici_cozum"),
    ("Yıldızlı Sigorta: raporları şimdilik elle derleyip gönderiyoruz, otomatik zamanlama özelliği olup olmadığını öğrenmek istiyoruz; sistemde hata yok.", "P4", "gecici_cozum"),
    ("Alp Kimya: sipariş onay ekranı hiç çalışmıyor, onay veremiyoruz ve başka yoldan da işlem yapamıyoruz, diğer modüller sorunsuz.", "P2", "gecici_cozum_yok"),
    ("Sedir Ambalaj'dan yazıyoruz: ihracat belgesi oluşturma modülü açılmıyor, belge çıkaramıyoruz ve alternatif yöntemimiz yok; sistemin geri kalanı çalışıyor.", "P2", "gecici_cozum_yok"),
    ("Sipariş takip sayfası her denemede zaman aşımına düşüyor, kargo durumunu göremiyoruz ve başka yerden de bakamıyoruz; diğer sayfalar açık. Tuzla Denizcilik.", "P2", "gecici_cozum_yok"),
    ("Mercan Tekstil: cari hesap ekstresi alınamıyor, ekstre ekranı hata veriyor ve muhasebe kapanışı için başka bir yolumuz yok, uygulamanın diğer bölümleri çalışıyor.", "P2", "gecici_cozum_yok"),
]
