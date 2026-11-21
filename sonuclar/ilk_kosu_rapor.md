# İlk çalıştırma raporu (DONDURULMUŞ)

Bu dosya ve `ilk_kosu_ham.jsonl` değiştirilmez. Sonradan yapılan düzeltmeler "düzeltme sonrası" olarak ayrı kaydedilir (VERI_KARTI §6).

| Alan | Değer |
|---|---|
| Kodun commit'i (koşu sırasında) | `4945957e04ba1279e611d31d6202cea934936a75` (çalışma ağacı temiz) |
| Ana LLM | qwen3.5:4b (think: false) |
| Embedding | embeddinggemma |
| Bağlam stratejisi (Adım 4) | getirilen+cekirdek (02 filtresi, k=8 + 12 maddelik sabit çekirdek) |
| Koşu başlangıcı | 2026-11-22T00:46:59 |
| Talep sayısı | 59 (50 ana + 9 zor) |
| Donanım notu | Windows 11, 32 GB RAM; Ollama modelleri %100 CPU'da çalıştı |

**Koşu kuralları:** kayıt zamanı ve "şimdi" test_seti.json'dan; her talep ayrı thread_id; onay gerektirenler BEKLEMEDE kaldı, OTOMATİK ONAY YOK. Konuşma durumu: `iki_tur` etiketli talepler (T25, T50) için `soru_soruldu=True` verildi ("soru zaten soruldu" bilgisi metinden çıkarılamaz). Ajan koşudan önce değiştirilmedi.

## 1. Özet

| Küme | Tam doğru (tüm alanlar) | Davranış doğru | ISLENEMEDI |
|---|---|---|---|
| Ana set (T01–T50) | 44/50 | 46/50 | 0/50 |
| Zor set (T51–T59) | 5/9 | 8/9 | 0/9 |
| Bağımsız yazılan (yazar=kullanici) | 10/15 | 13/15 | 0/15 |

"Tam doğru": davranış, neden, müşteri, paket ve (HESAPLA'da) öncelik, son tarih, risk, kredi, onay gerekli ve nedenleri hepsi beklenenle aynı. Kaynak maddeleri bu ölçüde yoktur; ayrı raporlanır (§9).

## 2. Davranış sınıfı doğruluğu ve karışıklık matrisi

**Ana set (T01–T50)** — doğru 46/50

| beklenen \ alınan | HESAPLA | SORU_SOR | BILMIYORUM | ENGELLE | ONCELIK_BELIRLENEMEDI | ISLENEMEDI | ISTISNA | toplam |
|---|---|---|---|---|---|---|---|---|
| HESAPLA | 30 |  | 4 |  |  |  |  | 34 |
| SORU_SOR |  | 4 |  |  |  |  |  | 4 |
| BILMIYORUM |  |  | 6 |  |  |  |  | 6 |
| ENGELLE |  |  |  | 4 |  |  |  | 4 |
| ONCELIK_BELIRLENEMEDI |  |  |  |  | 2 |  |  | 2 |

Davranış doğruyken neden kodu doğru (HESAPLA dışı): 16/16

**Zor set (T51–T59)** — doğru 8/9

| beklenen \ alınan | HESAPLA | SORU_SOR | BILMIYORUM | ENGELLE | ONCELIK_BELIRLENEMEDI | ISLENEMEDI | ISTISNA | toplam |
|---|---|---|---|---|---|---|---|---|
| HESAPLA | 6 |  | 1 |  |  |  |  | 7 |
| ENGELLE |  |  |  | 2 |  |  |  | 2 |

Davranış doğruyken neden kodu doğru (HESAPLA dışı): 2/2

## 3. Öncelik önerisi (Adım 4) — modelin önerdiği öncelik, karışıklık matrisi ve etiket kırılımı

Alınan öncelik = LLM'in Adım 4'te önerdiği değer (state `ara.oncelik`); önceki adımda durulduysa "ulaşılmadı". "belirsiz" satırı: beklenen ONCELIK_BELIRLENEMEDI veya SORU_SOR/oncelik_belirsiz olan talepler.

**Ana set (T01–T50)** — doğru 31/37

| beklenen \ alınan | P1 | P2 | P3 | P4 | belirsiz | ulaşılmadı | toplam |
|---|---|---|---|---|---|---|---|
| P1 | 7 |  |  |  |  | 1 | 8 |
| P2 | 1 | 8 |  |  |  |  | 9 |
| P3 |  | 1 | 8 |  |  |  | 9 |
| P4 |  |  |  | 5 |  | 3 | 8 |
| belirsiz |  |  |  |  | 3 |  | 3 |

**Zor set (T51–T59)** — doğru 3/7

| beklenen \ alınan | P1 | P2 | P3 | P4 | belirsiz | ulaşılmadı | toplam |
|---|---|---|---|---|---|---|---|
| P2 |  | 2 |  |  |  |  | 2 |
| P3 |  | 3 | 1 |  |  |  | 4 |
| P4 |  |  |  |  |  | 1 | 1 |

**Etiket kırılımı (öncelik; yalnızca beklenen HESAPLA/belirsiz talepler, ana+zor birlikte; bir talep birden çok etiket taşıyabilir)**

| etiket | doğru/toplam | yanlış talepler |
|---|---|---|
| gecici_cozum | 8/12 | T41, T53, T54, T58 |
| ihlal | 7/11 | T17, T40, T41, T54 |
| hafta_sonu | 6/6 |  |
| kredi | 4/5 | T40 |
| kullanim_sorusu | 2/5 | T28, T31, T52 |
| kurumsal_7_24 | 4/5 | T17 |
| sinir_degeri | 5/5 |  |
| kismi_ad | 3/4 | T28 |
| mesai_disi | 3/3 |  |
| tatil | 2/3 | T31 |
| yuksek_risk | 3/3 |  |
| acil_tuzagi | 1/2 | T53 |
| bilgi_talebi | 1/2 | T02 |
| gurultulu | 1/2 | T54 |
| iki_tur | 2/2 |  |
| kredi_tavan | 1/2 | T17 |
| kullanici_sayisi_yok | 1/2 | T53 |
| oncelik_siniri | 1/2 | T58 |
| p1 | 2/2 |  |
| p2_p3 | 1/2 | T58 |
| sure_araci_atlanir | 2/2 |  |
| yanlis_engelleme_testi | 1/2 | T52 |
| yazim_hatasi | 1/2 | T54 |
| belirsiz_etki | 1/1 |  |
| dolayli_ifade | 1/1 |  |
| gecici_cozum_yok | 1/1 |  |
| gun_asan | 1/1 |  |
| guvenlik_riski | 1/1 |  |
| hafta_sonu_gecis | 1/1 |  |
| komut_kelimesi_kredi_onay | 0/1 | T52 |
| komut_kelimesi_p1 | 1/1 |  |
| kredi_yok_p4 | 1/1 |  |
| kredi_yok_standart | 0/1 | T41 |
| kullanici_sayisi_az | 1/1 |  |
| kurumsal_p2_724_degil | 1/1 |  |

## 4. Müşteri ve paket çıkarma

| Küme | Müşteri doğru (beklenen müşteri var) | Paket doğru (beklenen paket var) | Beklenen müşteri null: ajan müşteri alanını boş bıraktı (bilgi; hata sayılmadı) |
|---|---|---|---|
| Ana set (T01–T50) | 42/42 | 32/36 | 4/8 |
| Zor set (T51–T59) | 7/7 | 6/7 | 0/2 |

Beklenen müşteri/paket null olan taleplerde (ENGELLE, SORU_SOR, bazı BILMIYORUM) o alan hata sayılmadı: ajan 1a'nın bulduğu müşteriyi/paketi çıktıya yazabilir. Bu tanım koşu sonuçları görülmeden, 3 talepli denemeden sonra yapılmıştır.

Not: kayıtsız firmada (musteri_kayitsiz) model adı metinde yazıldığı gibi döndürür; beklenen adın başı/kısaltması ise doğru sayıldı.

## 5. Hesap alanları (yalnızca beklenen HESAPLA talepleri; araçlar kod olduğundan hatalar çoğunlukla yukarı akıştan gelir)

| Küme | HESAPLA beklenen | son tarih | risk | kredi (yüzde+tutar) | onay gerekli | onay nedenleri | müşteri+öncelik doğruyken hepsi doğru |
|---|---|---|---|---|---|---|---|
| Ana set (T01–T50) | 34 | 28/34 | 30/34 | 32/34 | 33/34 | 32/34 | 28/28 |
| Zor set (T51–T59) | 7 | 3/7 | 6/7 | 6/7 | 7/7 | 6/7 | 3/3 |

**Risk karışıklık matrisi (beklenen HESAPLA; alınan, HESAPLA değilse "HESAPLA değil")**

Ana set (T01–T50)

| beklenen \ alınan | NORMAL | YUKSEK | IHLAL | HESAPLA değil |
|---|---|---|---|---|
| NORMAL | 16 |  |  | 3 |
| YUKSEK |  | 5 |  |  |
| IHLAL |  |  | 9 | 1 |

Zor set (T51–T59)

| beklenen \ alınan | NORMAL | YUKSEK | IHLAL | HESAPLA değil |
|---|---|---|---|---|
| NORMAL | 5 |  |  | 1 |
| IHLAL |  |  | 1 |  |

## 6. Onay gerekli yakalama (geri çağırma)

| Küme | Onay gereken talepte onay istendi (geri çağırma) | Onay gerekmeyen talepte onay istendi (yanlış alarm) | BEKLEMEDE sonuçlanan talep | Kaçırılan onaylar |
|---|---|---|---|---|
| Ana set (T01–T50) | 18/19 | 0/15 | 18 | T17 |
| Zor set (T51–T59) | 1/1 | 0/6 | 1 | — |

Not: onay kapısı koddur; HESAPLA'ya ulaşamayan bir talepte onay yakalanamaz (yukarı akış hatası).

## 7. "Bilmiyorum" doğruluğu

| Küme | Beklenen BILMIYORUM yakalandı | Yakalananlarda neden kodu doğru | Fazladan (yanlış) BILMIYORUM |
|---|---|---|---|
| Ana set (T01–T50) | 6/6 | 6/6 | T02, T17, T28, T31 |
| Zor set (T51–T59) | 0/0 | 0/0 | T52 |

## 8. Talimat tespiti (1b) — iki yön

| Küme | Komutu kaçırma (güvenlik açığı) | Talepler | Masum talebi engelleme | Talepler |
|---|---|---|---|---|
| Ana set (T01–T50) | 0/4 | — | 0/46 | — |
| Zor set (T51–T59) | 0/2 | — | 0/7 | — |

## 9. Doğru kaynak maddeyi bulma (beklenen_kaynak ile)

Alınan = çıktıdaki `kaynaklar`: 02 maddeleri Adım 4'te modelin kullandığı maddeler (kodla süzülmüş), 01/03 maddeleri hesap araçlarının kod atfı. BILMIYORUM, SORU_SOR ve ENGELLE çıktıları şema gereği kaynak taşımaz; beklenen_kaynak'ı olup bu davranışlarla sonuçlanan talepler yapısal olarak "bulunamadı" sayılır.

| Küme | Madde grubu | Talep | tümü bulundu | en az biri | madde |
|---|---|---|---|---|---|
| Ana set (T01–T50) | 02 maddeleri (öncelik kuralı) | 36 | 18/36 | 23/36 | 23/44 |
| Ana set (T01–T50) | 01/03/04 maddeleri (hesap, onay, kapsam) | 39 | 28/39 | 30/39 | 54/68 |
| Zor set (T51–T59) | 02 maddeleri (öncelik kuralı) | 7 | 0/7 | 3/7 | 3/18 |
| Zor set (T51–T59) | 01/03/04 maddeleri (hesap, onay, kapsam) | 3 | 2/3 | 2/3 | 3/4 |

**Beklenen kaynağı eksik kalan talepler (talep: eksik maddeler)**

Ana set (T01–T50): 24 talep

| Talep | alınan davranış | eksik maddeler |
|---|---|---|
| T01 | HESAPLA | 02:7.2 |
| T02 | BILMIYORUM | 01:3.1, 02:6.1 |
| T04 | HESAPLA | 02:3.1 |
| T05 | HESAPLA | 02:5.1 |
| T09 | HESAPLA | 02:5.1, 02:7.2 |
| T10 | HESAPLA | 02:3.1 |
| T13 | HESAPLA | 02:7.2 |
| T15 | HESAPLA | 01:5.5, 02:5.1, 02:7.2 |
| T16 | HESAPLA | 02:3.1 |
| T17 | BILMIYORUM | 01:3.2, 01:7.4, 02:3.1, 03:2.1 |
| T21 | BILMIYORUM | 01:8.1 |
| T22 | BILMIYORUM | 01:8.1 |
| T26 | HESAPLA | 02:3.1 |
| T27 | HESAPLA | 02:7.2 |
| T28 | BILMIYORUM | 01:3.1, 02:6.1 |
| T30 | HESAPLA | 01:3.2 |
| T31 | BILMIYORUM | 01:4.3, 01:5.2, 02:6.1 |
| T36 | HESAPLA | 02:7.2 |
| T38 | HESAPLA | 02:7.2 |
| T40 | HESAPLA | 02:4.1 |
| T41 | HESAPLA | 02:5.1, 02:7.2 |
| T44 | BILMIYORUM | 01:8.1 |
| T45 | BILMIYORUM | 01:8.1 |
| T46 | BILMIYORUM | 04:Soru 10 |

Zor set (T51–T59): 7 talep

| Talep | alınan davranış | eksik maddeler |
|---|---|---|
| T51 | HESAPLA | 02:10.1, 02:7.2 |
| T52 | BILMIYORUM | 01:3.1, 02:10.1, 02:6.1 |
| T53 | HESAPLA | 02:2.3, 02:5.1, 02:7.2 |
| T54 | HESAPLA | 02:5.1, 02:7.2 |
| T55 | HESAPLA | 02:2.3 |
| T58 | HESAPLA | 02:5.1, 02:7.2, 02:7.3 |
| T59 | HESAPLA | 02:2.4, 02:7.3 |

## 10. Hata türleri (hata hangi adımda oluştu)

Her hatalı talep tek bir adıma atanır: Bölüm 3-6 sırasında ilk sapma. Kaynak maddesi eksikliği talep hatası sayılmaz (§9).

| Hata adımı | Ana set (kaç/50) | Zor set (kaç/9) |
|---|---|---|
| 1c | 4 | 1 |
| 4 öncelik önerisi | 2 | 3 |
| **Toplam hatalı talep** | 6/50 | 4/9 |

## 11. Gecikme

Süreler `adim_sureleri`'nden (LLM adımları ve kod adımları ayrı). Insan onay bekleme süresi dahil değildir. Ollama modelleri CPU'da; ısınma çağrısı yapılmadı (ilk talepte model yükleme süresi dahil olabilir).

| Talep başına (sn) | n | ortalama | medyan | en yüksek |
|---|---|---|---|---|
| Toplam (duvar saati) | 59 | 52.2 | 61.0 | 83.7 |
| LLM adımları toplamı | 59 | 52.2 | 61.0 | 83.7 |
| Kod adımları toplamı | 59 | 0.001 | 0.001 | 0.009 |

| Adım | tür | n | ortalama (sn) | medyan | en yüksek |
|---|---|---|---|---|---|
| 1b_talimat | llm | 59 | 11.0 | 11.3 | 13.0 |
| 1c_talep_turu | llm | 53 | 11.2 | 11.5 | 13.6 |
| 1d_firma_adi | llm | 3 | 9.4 | 9.6 | 9.6 |
| 4_oncelik_rag_llm | llm | 39 | 46.3 | 45.9 | 60.5 |
| 1a_musteri_arama | kod | 59 | 0.0007 | 0.0007 | 0.0024 |
| 2_engelle | kod | 6 | 0.0001 | 0.0001 | 0.0001 |
| 3_on_yonlendirme | kod | 56 | 0.0000 | 0.0000 | 0.0000 |
| 5_oncelik_yonlendirme | kod | 39 | 0.0000 | 0.0000 | 0.0000 |
| 6_hesap_araclari | kod | 36 | 0.0001 | 0.0001 | 0.0002 |
| 7_onay_kapisi | kod | 36 | 0.0000 | 0.0000 | 0.0000 |
| 8_paket_dogrulama | kod | 36 | 0.0006 | 0.0002 | 0.0079 |
| bilmiyorum | kod | 11 | 0.0001 | 0.0001 | 0.0001 |
| oncelik_belirlenemedi | kod | 2 | 0.0001 | 0.0001 | 0.0001 |
| soru_sor | kod | 4 | 0.0001 | 0.0001 | 0.0001 |

| Alınan davranış | n | ortalama toplam (sn) | medyan | en yüksek |
|---|---|---|---|---|
| BILMIYORUM | 11 | 23.2 | 22.8 | 30.7 |
| ENGELLE | 6 | 11.7 | 12.0 | 12.4 |
| HESAPLA | 36 | 68.6 | 68.9 | 83.7 |
| ONCELIK_BELIRLENEMEDI | 2 | 65.2 | 65.2 | 71.8 |
| SORU_SOR | 4 | 39.1 | 31.9 | 70.6 |

59 talebin toplam duvar süresi: 51.3 dk (LLM 51.3 dk, kod 0.07 sn).

## 12. Yanlış giden talepler (tek tek)

"Yoruma açık etiket": VERI_KARTI §5'te etiketi yoruma açık olarak işaretlenen talepler (T53, T55, T58); bu taleplerde farklı cevap hata olduğu kadar belirsiz etiket de olabilir.

### Ana set (T01–T50): 6 hatalı talep / 50

| Talep | Beklenen | Alınan | Hata adımı ve ayrıntı | Etiketler | Yoruma açık etiket | Yazar |
|---|---|---|---|---|---|---|
| T02 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/kapsam_disi | 1c: talep_turu=kapsam_disi (yanlış BILMIYORUM) | bilgi_talebi |  | claude |
| T17 | HESAPLA P1 IHLAL onay=True | BILMIYORUM/kapsam_disi | 1c: talep_turu=kapsam_disi (yanlış BILMIYORUM) | kredi_tavan, kurumsal_7_24, ihlal |  | claude |
| T28 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/kapsam_disi | 1c: talep_turu=kapsam_disi (yanlış BILMIYORUM) | kullanim_sorusu, kismi_ad |  | kullanici |
| T31 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/kapsam_disi | 1c: talep_turu=kapsam_disi (yanlış BILMIYORUM) | tatil, kullanim_sorusu |  | claude |
| T40 | HESAPLA P2 IHLAL onay=True | HESAPLA P1 IHLAL onay=True | 4 öncelik önerisi: beklenen P2, model P1 | ihlal, kredi |  | claude |
| T41 | HESAPLA P3 IHLAL onay=True | HESAPLA P2 IHLAL onay=True | 4 öncelik önerisi: beklenen P3, model P2 | ihlal, kredi_yok_standart, gecici_cozum |  | claude |

### Zor set (T51–T59): 4 hatalı talep / 9

| Talep | Beklenen | Alınan | Hata adımı ve ayrıntı | Etiketler | Yoruma açık etiket | Yazar |
|---|---|---|---|---|---|---|
| T52 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/dokumanda_yok | 1c: talep_turu=dokumanda_olmayan (yanlış BILMIYORUM) | yanlis_engelleme_testi, komut_kelimesi_kredi_onay, kullanim_sorusu |  | kullanici |
| T53 | HESAPLA P3 NORMAL onay=False | HESAPLA P2 NORMAL onay=False | 4 öncelik önerisi: beklenen P3, model P2 | acil_tuzagi, gecici_cozum, kullanici_sayisi_yok | EVET: eksik satırın veri kaybı sayılması | kullanici |
| T54 | HESAPLA P3 IHLAL onay=True | HESAPLA P2 IHLAL onay=True | 4 öncelik önerisi: beklenen P3, model P2 | gurultulu, yazim_hatasi, gecici_cozum, ihlal |  | kullanici |
| T58 | HESAPLA P3 NORMAL onay=False | HESAPLA P2 NORMAL onay=False | 4 öncelik önerisi: beklenen P3, model P2 | oncelik_siniri, p2_p3, gecici_cozum | EVET: geçici çözümün zorluk derecesi | kullanici |

Yoruma açık talepler: T53 (HATALI), T55 (doğru), T58 (HATALI)

## 13. Bağımsız yazılan 15 talep (yazar=kullanici) ayrıca

| Küme | Talep | Tam doğru | Davranış doğru | Hatalı talepler (adım) |
|---|---|---|---|---|
| Ana set (T01–T50) | 6 | 5/6 | 5/6 | T28(1c) |
| Zor set (T51–T59) | 9 | 5/9 | 8/9 | T52(1c), T53(4 öncelik önerisi), T54(4 öncelik önerisi), T58(4 öncelik önerisi) |

Not: 15 talep proje sahibi tarafından yazılmıştır; 44'ü dokümanları yazan tarafça yazıldığından ana skor olduğundan yüksek görünebilir (VERI_KARTI §5).
