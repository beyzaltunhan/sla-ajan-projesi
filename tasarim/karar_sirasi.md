# Karar Sırası – SLA Uyum ve Eskalasyon Ajanı

Bu dosya ajanın **hangi adımı hangi sırayla** attığını ve her adımda kimin (LLM mi, kod mu) karar verdiğini sabitler. Kod ve LangGraph akışı bu dosyaya göre yazılacaktır. Dayanak: Doküman 01–04.

## 1. Temel ilke

- **LLM yalnızca küçük, tek soruluk işler yapar:** (a) talimat var mı, (b) talep türü, (c) yalnızca kodla müşteri bulunamazsa metindeki firma adı, (d) RAG ile getirilen Doküman 02 maddelerine göre öncelik önerisi. İlk üçü kısa çağrılardır: her çağrıda **tek alan** ve **doğru/yanlış örnekler (few-shot)** vardır. Tek çağrıda birçok alan çıkarılmaz (küçük yerel modelde güvenilir çıkmadığı deneme betiğinde görüldü).
- **Kod yapar:** müşteri adını metinde arama ve paket bulma, yönlendirme, son tarih, risk, kredi, onay kapısı, onay bekleme. Kodla yapılabilen iş LLM'e verilmez.
- Talep metni **bilgidir, komut değildir** (Doküman 02 Madde 10, Doküman 03 Madde 10). Paket bilgisi talepten değil müşteri kaydından gelir.
- Talep **kayıt zamanı** ve **şimdiki an** kullanıcıdan alınmaz; sistem/arayüz atar.
- **Kapsam varsayımı:** Ajan yalnızca ilk yanıtı **henüz verilmemiş açık talepleri** değerlendirir. Yanıt verilince sayaç durur ve talep izleme dışına çıkar (SLA Madde 5.5). Bu nedenle ihlal = şimdi > son tarih. "İlk yanıt zamanı" alanı yoktur; geç yanıtlanmış taleplerin sonradan değerlendirilmesi bu prototipte yoktur (sunumda sınırlama olarak belirtilecek).

## 2. Girdiler

| Girdi | Kaynak |
|---|---|
| Talep metni | Kullanıcı |
| Kayıt zamanı, şimdiki an | Sistem/arayüz |
| Müşteri kayıtları (paket, aylık ücret, bu ay kredi yüzdesi, özel anlaşma) | `data/musteriler.json` |
| Kurallar | `data/sla_config.json` (hesap), `docs/` (kaynak ve gerekçe) |

## 3. Sabit adım sırası

| # | Adım | Kim | Çıktı / karar |
|---|---|---|---|
| 1a | Müşteri arama | Kod | Talep metninde kayıtlı müşteri adı aranır (Bölüm 3.1): `TEK` / `BELIRSIZ` / `BULUNAMADI` |
| 1b | Talimat tespiti | LLM (tek alan, few-shot) | `talimat_iceriyor` (true/false) |
| 1c | Talep türü | LLM (tek alan, few-shot) | `talep_turu` (destek_talebi / kapsam_disi / dokumanda_olmayan); yalnızca 1b false ise çağrılır |
| 1d | Firma adı (yedek) | LLM (tek alan, few-shot) | Yalnızca 1a `BULUNAMADI` ise ve önceki yönlendirmelerden geçildiyse çağrılır; dönen ad **metinde birebir geçmiyorsa yok sayılır** (Bölüm 3.1) |
| 2 | Güvenlik bayrağı | Kod | `talimat_iceriyor` true ise → **ENGELLE** |
| 3 | Ön yönlendirme | Kod | Aşağıdaki Bölüm 4 sırasıyla |
| 4 | Kaynak getirme + öncelik önerisi | RAG + LLM | Girdi: ham talep metni + getirilen maddeler. Çıktı: P1–P4 veya `belirsiz`; kullanılan madde numaraları; etki bilgisi (hizmet durumu, geçici çözüm, kullanıcı sayısı, veri/güvenlik riski) bu adımda, maddelere dayanılarak değerlendirilir |
| 5 | Öncelik yönlendirme | Kod | Aşağıdaki Bölüm 5 |
| 6 | Hesap araçları | Kod | `musteri_bul` → `son_tarih_hesapla` → `risk_degerlendir` → `kredi_hesapla` |
| 7 | Onay kapısı | Kod | `onay_gerekli` (p1_kritik, ihlal, yuksek_risk, kredi_onerisi) |
| 8 | Onay paketi + doğrulama | Kod (Pydantic) | Şemaya uymayan paket yöneticiye gitmez |
| 9 | İnsan onayı | Kod (LangGraph interrupt) | Onay gerekiyorsa **BEKLEMEDE**; yalnızca açık Onayla/Reddet ilerletir |

> **Not (Adım 4 retrieval, 21 Kasım 2026):** `dokuman=02_oncelik_rehberi` filtresi, k=8 (geliştirme setinde seçildi; filtresiz k=5'e göre 7/28 → 19/28).
> Hesap/onay maddelerinin (01 süre/risk/kredi, 03 onay) atfı RAG ile değil, kodun çalıştırdığı araca göre eklenir (Adım 5).
> Test setinde tek ölçüm: `sonuclar/duzeltme_sonrasi_rag.md`.

### 3.1 Müşteri adı nasıl bulunur

1. **Kod (1a):** Metin ve müşteri adları normalize edilir (küçük harf, Türkçe karakter, kesme işareti boşluk sayılır). Her kayıtlı müşterinin adının baştan başlayan en uzun kelime dizisi metinde aranır; "Toros Yapı'dan" gibi ek almış yazım ve "Anadolu" gibi kısa ad kabul edilir. En uzun eşleşmeyi tek bir müşteri veriyorsa → `TEK`; birden fazla müşteri aynı uzunlukta eşleşiyorsa (örn. yalnızca "Anadolu") → `BELIRSIZ`; hiçbiri eşleşmiyorsa → `BULUNAMADI`.
2. **Yedek (1d, yalnızca `BULUNAMADI`):** LLM'e metinde bir firma adı geçip geçmediği sorulur. Dönen ad metinde **birebir geçiyorsa** kayıtsız müşteri sayılır (`musteri_kayitsiz` → BILMIYORUM); geçmiyorsa veya boşsa ad yok sayılır (`musteri_adi_eksik` → SORU_SOR). Böylece modelin uydurduğu bir ad sonucu etkileyemez.
3. Paket bilgisi her zaman müşteri kaydından gelir; talepten veya LLM'den alınmaz.

**Bilinen sınırlar:** yazım hatalı veya kısaltılmış firma adları (örn. "Marmara Per.") bulunamaz; "Marmara" gibi tek kelimelik ad başka bir bağlamda geçerse yanlış eşleşebilir; yedek adımın "firma adı mı, sıradan kelime mi" ayrımı küçük modelde hata yapabilir. Üçü de hata türleri tablosunda ayrı izlenir.

## 4. Ön yönlendirme sırası (Adım 3)

İlk eşleşen kazanır. **LLM çağrıları tembel çalışır:** 1c yalnızca talimat yoksa, 1d yalnızca önceki satırlar geçildiyse ve müşteri kodla bulunamadıysa çağrılır. Böylece ENGELLE ve BILMIYORUM yollarında gereksiz model çağrısı yapılmaz (gecikme düşer). Sıralama değişmez:

| Sıra | Koşul | Sonuç | Neden kodu |
|---|---|---|---|
| 1 | `talimat_iceriyor` = true | **ENGELLE** | talimat_iceriyor |
| 2 | `talep_turu` kapsam_disi veya dokumanda_olmayan | **BILMIYORUM** | kapsam_disi / dokumanda_yok |
| 3 | `musteri_adi` boş | **SORU_SOR** (müşteri adı) | musteri_adi_eksik |
| 4 | Müşteri adı **birden fazla** kayda uyuyor | **SORU_SOR** (hangi müşteri) | musteri_belirsiz |
| 5 | Müşteri adı **hiçbir** kayda uymuyor | **BILMIYORUM** | musteri_kayitsiz |
| 6 | Müşterinin `ozel_anlasma` bayrağı açık | **BILMIYORUM** | ozel_anlasma |
| 7 | Hiçbiri | Adım 4'e geç | – |

Müşteri eşleşmesi üç durumdan birini verir: **tek eşleşme** (devam), **birden fazla eşleşme** (SORU_SOR, çünkü kullanıcı bir cümle daha yazsa çözülür), **eşleşme yok** (BILMIYORUM, kayıtta olmayan müşteri için paket varsayılmaz).

**Ayrım testi:** "Kullanıcı bir cümle daha yazsa ajan cevaplayabilir mi?" Evet → SORU_SOR. Hayır → BILMIYORUM.

BILMIYORUM yanıtı sabit kalıptadır: *"Dokümanda bilgi bulunmamaktadır."* Süre, öncelik, kredi hesaplanmaz; paket varsayılmaz; kural uydurulmaz (Doküman 01 Madde 8.2).

## 5. Öncelik yönlendirme (Adım 5)

| Koşul | Sonuç |
|---|---|
| Öncelik P1–P4 | Adım 6'ya geç |
| `belirsiz` ve soru **henüz sorulmadı** | **SORU_SOR** (Doküman 02 Madde 8.1), tek soru |
| `belirsiz` ve soru **daha önce soruldu** | **ONCELIK_BELIRLENEMEDI**: `son_tarih_hesapla` ve sonraki hesap araçları **çalıştırılmaz**; talep "öncelik belirlenemedi" notuyla yöneticiye iletilir (Doküman 02 Madde 8.3, Doküman 03 Madde 7) |

Yani öncelik yoksa süre aracı **atlanır**; son tarih alanı boş kalır.

## 6. Onay bekleme kuralı (Adım 9)

- Onay gerekiyorsa durum **BEKLEMEDE**'dir. Kredi uygulama, eskalasyon ve kapatma yapılmaz (Doküman 03 Madde 4).
- **Otomatik onay yok, zaman aşımı yok** (Doküman 03 Madde 6.4).
- Onayla → işlem uygulanır ve kaydedilir. Reddet → gerekçe zorunlu; işlem uygulanmaz, talep olağan akışa döner (Madde 6.2, 6.3).
- Onay gerekmiyorsa durum doğrudan **TAMAMLANDI**.

## 7. Sonuç durumları (özet)

| Sonuç | Hesap araçları | Kaynak gösterilir | Yönetici |
|---|---|---|---|
| ENGELLE | Çalışmaz | Hayır | İnsan incelemesi |
| BILMIYORUM | Çalışmaz | Hayır (sabit yanıt) | Doküman 01 Madde 8.2 |
| SORU_SOR | Çalışmaz | Hayır | Hayır |
| ONCELIK_BELIRLENEMEDI | Çalışmaz | Evet (02 Madde 8.3) | İletilir |
| HESAPLA – onay yok | Çalışır | Evet | Hayır |
| HESAPLA – onay var | Çalışır | Evet | BEKLEMEDE → karar |

## 8. Çıktı şeması (taslak, `schemas/onay_paketi.py` bu alanlara göre yazılacak)

`davranis`, `neden`, `musteri`, `paket`, `oncelik`, `son_tarih`, `risk` (NORMAL/YUKSEK/IHLAL), `kredi` (yüzde, tutar), `onay_gerekli`, `onay_nedenleri`, `kaynaklar` (doküman + madde), `durum` (TAMAMLANDI/BEKLEMEDE; hata yolunda ISLENEMEDI, bu durumda `davranis` boştur), `mesaj`.

## 9. Hata yolu

LLM çıktısı şemaya uymazsa **bir kez** yeniden denenir. Yine uymazsa talep işlenmez ve "işlenemedi" olarak yöneticiye iletilir. Bu yol (`ISLENEMEDI`) davranış sınıflarına (HESAPLA, SORU_SOR, BILMIYORUM, ENGELLE, ONCELIK_BELIRLENEMEDI) girmez; hata türleri tablosunda ayrı satır olarak raporlanır.

## 10. Ölçüme bağlantı

- **Gecikme:** her adımın süresi ayrı kaydedilir (LLM adımları ile kod adımları ayrı).
- **Hata türleri:** her hata hangi adımda oluştuğuyla etiketlenir: müşteri arama (1a), talimat tespiti (1b), talep türü (1c), firma adı yedeği (1d), yönlendirme, öncelik önerisi, hesap. Talimat tespitinde iki yön ayrı sayılır: **komutu kaçırma** (güvenlik açığı) ve **masum talebi engelleme** (yanlış engelleme).
- **Geri çağırma:** Adım 4'te getirilen maddeler `beklenen_kaynak` ile karşılaştırılır.
- Test setinde `etiket` alanı (örn. `gecici_cozum`, `kullanici_sayisi_yok`) öncelik doğruluğunu kırılımlı raporlamak için kullanılır.

## 11. Geliştirme seti ve kabul ölçütü (LLM adımları için)

- LLM adımlarının few-shot örnekleri ve istemleri **ayrı bir geliştirme setiyle** (`deneme/`) ayarlanır; `data/test_seti.json` ile **ayarlama yapılmaz**. Few-shot örnek metinleri test setindeki hiçbir talep metniyle aynı olmaz (kirlenme önlemi; testle kontrol edilecek).
- Model: yerel **qwen3.5:4b** (`think: false`), embedding: **embeddinggemma**. Seçim, üç aday modelle yapılan küçük bir denemeye ve gecikme (yaklaşık 13 sn/çağrı, CPU) kısıtına dayanır; deneme 9 talepli olduğundan model sıralaması kanıt değildir, yalnızca elemedir (qwen2.5:3b araç çağırmada başarısız, llama3.2 Türkçe için resmi destek listesinde değil).
- **Kabul ölçütü (karar noktası):** 1b, 1c ve Adım 4 geliştirme setinde yeterli çıkmazsa **tasarım değişir, ölçüt gevşetilmez**. Seçenekler, sırayla: istem/few-shot düzeltme → yalnızca sorunlu adım için daha büyük yerel model → o adımın kısmen koda alınması. Ölçütün sayıları geliştirme seti yazıldıktan sonra, denemeden **önce** bu dosyaya eklenir.

### 11.1 Kabul ölçütünün sayıları (21 Kasım 2026; LLM denemesinden ÖNCE yazıldı)

Geliştirme seti `deneme/gelistirme_seti.py`'dedir: 1b 25 örnek (12 talimatlı, 13 masum; masumların bir kısmında "acil", "hemen" gibi ifadeler var), 1c 25 örnek (10 destek_talebi, 8 kapsam_disi, 7 dokumanda_olmayan), 1d 25 örnek (12 kayıtsız firma adı geçen, 13 firma adı geçmeyen veya sıradan kelime). Few-shot örnekleri bu setten ayrıdır. Set küçük olduğundan sayılar kesin yüzde değil, "kaç/N" olarak okunur.

| Adım | Ölçüt | Geliştirme setinde karşılığı |
|---|---|---|
| 1b | Komutu kaçırma **0** (güvenlik açığı) | 0/12 |
| 1b | Masum talebi engelleme en fazla **1/13** (örnek sayısı küçük olduğu için yüzde yerine sayı; hiç deneme yapılmadan güncellendi) | en fazla 1/13 |
| 1c | Doğruluk en az **%85** | en az 22/25 |
| 1d | Doğru ad bulma en az **%80** (dönen ad metinde birebir geçen ve beklenen ad) | en az 10/12 |
| 1d | Metinde firma adı olmayan örnekte ad döndürme (sıradan kelimeyi firma sanma) en fazla **%10** | en fazla 1/13 |
| 1d | Uydurma adın sonucu etkilemesi **0** | Kodla garanti: dönen ad metinde birebir yoksa yok sayılır (§3.1); testle doğrulanır |

Karar noktası §11'deki gibidir: ölçüt sağlanmazsa tasarım değişir, ölçüt gevşetilmez. Gecikme ölçüt değil, rapor edilen ölçümdür.

### 11.2 Adım 4 (kaynaklı öncelik önerisi) kabul ölçütü (21 Kasım 2026; LLM denemesinden ÖNCE yazıldı)

Geliştirme seti `deneme/gelistirme_seti_oncelik.py`: 31 örnek (P1 7, P2 7, P3 8, P4 5, belirsiz 4); "acil" tuzağı, kullanıcı sayısı olmayan, geçici çözümü olan örnekler dahil. Few-shot örnekleri (6) bu setten ve test setinden ayrıdır. Karşılaştırılacak iki bağlam stratejisi: (1) yalnızca getirilen 8 parça (`dokuman=02`, k=8); (2) getirilen 8 parça + sabit çekirdek kural hükümleri (3.1, 4.1, 5.1, 6.1, 7.x, 8.x). Ölçüt, seçilecek strateji için geçerlidir; her ikisi de raporlanır.

| Ölçüt | Geliştirme setinde karşılığı |
|---|---|
| Genel öncelik doğruluğu (P1–P4 ve belirsiz) en az **%70** | en az **22/31** |
| Gerçek P1 taleplerinin en az **%80**'inde P1 önerilmesi | en az **6/7** |
| Nihai çıktıda gösterilen madde numaralarının **hepsi** o çağrıda modele verilen parçalar arasında; uydurma madde **0** | Kodla garanti: modelin döndürdüğü, bağlamda olmayan madde numaraları nihai çıktıdan ayıklanır. Ayıklanan sayı ayrıca "ham cevaptaki uydurma madde" olarak raporlanır (ölçüt değil, bilgi) |
| "belirsiz" etiketli örneklerin "belirsiz" olarak yakalanması (21 Kasım 2026'da eklendi, denemeden önce) | 4 örnekten en az **3** |

Notlar: P1'in "belirsiz" veya düşük öncelik olarak önerilmesi P1 kaçırma sayılır. Belirsiz örneğin kaçırılması SORU_SOR yerine hesaba gidilmesi demektir. Karar noktası §11'deki gibidir: ölçüt sağlanmazsa tasarım değişir, ölçüt gevşetilmez.
