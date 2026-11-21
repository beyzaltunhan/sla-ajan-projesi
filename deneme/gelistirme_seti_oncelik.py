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
]
