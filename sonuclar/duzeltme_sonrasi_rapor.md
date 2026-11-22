# Düzeltme sonrası koşu: ilk koşuyla karşılaştırmalı rapor

Yüzde değil "kaç/N" kullanılır. Ana set (T01–T50), zor set (T51–T59) ve bağımsız yazılan 15 talep ayrıdır. İlk koşu `ilk_kosu_ham.jsonl` (DONDURULMUŞ), bu koşu `duzeltme_sonrasi_ham.jsonl`. Bu rapor üretildikten sonra değiştirilmez.

| Alan | İlk koşu | Düzeltme sonrası koşu |
|---|---|---|
| Kodun commit'i (koşu sırasında) | `4945957e04ba` (temiz ağaç) | `036f3982efe8` (temiz ağaç) |
| Ana LLM | qwen3.5:4b (think: false) | qwen3.5:4b (think: false) |
| Embedding | embeddinggemma | embeddinggemma |
| Bağlam stratejisi | getirilen+cekirdek | getirilen+cekirdek |
| Koşu başlangıcı | 2026-11-22T00:46:59 | 2026-11-22T10:32:01 |
| Talep sayısı | 59 | 59 |

**Aynı koşullar:** kayıt zamanı ve "şimdi" test_seti.json'dan; her talep ayrı thread_id; OTOMATİK ONAY YOK; `iki_tur` etiketli talepler için `soru_soruldu=True`; beklenen müşteri/paket null olan alan hata sayılmaz; kayıtsız firma adı kısaltması kuralı aynı. Aynı ölçüm kodu (`degerlendirme/rapor.py`) iki koşuya da uygulandı. İkinci koşu, Windows'un uykuya geçmesini engelleyen bir başlatıcıyla çalıştırıldı (repo dışı; ajan ve koşucu kodu değişmedi).

**Düzeltmeler (ilk koşudan sonra):** (1) 1c talep türü istemi + few-shot (kullanım sorusu / mevcut hizmetle ilgili arıza ayrımı); (2) Adım 4 öncelik: çekirdek liste 12→14 madde (02:2.1, 2.2), istemde karar basamakları, few-shot 6→8. Ölçütler ve geliştirme setleri `tasarim/duzeltme_olcutleri.md` ve `deneme/` içindedir.

## 1. Özet (yan yana)

| Ölçü | İlk koşu | Düzeltme sonrası | Değişim |
|---|---|---|---|
| Tam doğru — Ana set (T01–T50) | 44/50 | 49/50 | ▲ |
| Tam doğru — Zor set (T51–T59) | 5/9 | 7/9 | ▲ |
| Tam doğru — bağımsız 15 | 10/15 | 12/15 | ▲ |
| Davranış doğru — Ana set (T01–T50) | 46/50 | 50/50 | ▲ |
| Davranış doğru — Zor set (T51–T59) | 8/9 | 9/9 | ▲ |
| Davranış doğru — bağımsız 15 | 13/15 | 15/15 | ▲ |
| Öncelik önerisi doğru (belirsiz dahil) — Ana set (T01–T50) | 31/37 | 37/37 | ▲ |
| Öncelik önerisi doğru (belirsiz dahil) — Zor set (T51–T59) | 3/7 | 5/7 | ▲ |

"Tam doğru": davranış, neden, müşteri, paket ve (HESAPLA'da) öncelik, son tarih, risk, kredi, onay gerekli ve nedenleri hepsi doğru. Kaynak maddeleri ayrıdır (§8).

## 2. Davranış sınıfı karışıklık matrisleri

**Ana set (T01–T50) — İlk koşu** (doğru 46/50)

| beklenen \ alınan | HESAPLA | SORU_SOR | BILMIYORUM | ENGELLE | ONCELIK_BELIRLENEMEDI | ISLENEMEDI | ISTISNA | toplam |
|---|---|---|---|---|---|---|---|---|
| HESAPLA | 30 |  | 4 |  |  |  |  | 34 |
| SORU_SOR |  | 4 |  |  |  |  |  | 4 |
| BILMIYORUM |  |  | 6 |  |  |  |  | 6 |
| ENGELLE |  |  |  | 4 |  |  |  | 4 |
| ONCELIK_BELIRLENEMEDI |  |  |  |  | 2 |  |  | 2 |

**Ana set (T01–T50) — Düzeltme sonrası** (doğru 50/50)

| beklenen \ alınan | HESAPLA | SORU_SOR | BILMIYORUM | ENGELLE | ONCELIK_BELIRLENEMEDI | ISLENEMEDI | ISTISNA | toplam |
|---|---|---|---|---|---|---|---|---|
| HESAPLA | 34 |  |  |  |  |  |  | 34 |
| SORU_SOR |  | 4 |  |  |  |  |  | 4 |
| BILMIYORUM |  |  | 6 |  |  |  |  | 6 |
| ENGELLE |  |  |  | 4 |  |  |  | 4 |
| ONCELIK_BELIRLENEMEDI |  |  |  |  | 2 |  |  | 2 |

**Zor set (T51–T59) — İlk koşu** (doğru 8/9)

| beklenen \ alınan | HESAPLA | SORU_SOR | BILMIYORUM | ENGELLE | ONCELIK_BELIRLENEMEDI | ISLENEMEDI | ISTISNA | toplam |
|---|---|---|---|---|---|---|---|---|
| HESAPLA | 6 |  | 1 |  |  |  |  | 7 |
| ENGELLE |  |  |  | 2 |  |  |  | 2 |

**Zor set (T51–T59) — Düzeltme sonrası** (doğru 9/9)

| beklenen \ alınan | HESAPLA | SORU_SOR | BILMIYORUM | ENGELLE | ONCELIK_BELIRLENEMEDI | ISLENEMEDI | ISTISNA | toplam |
|---|---|---|---|---|---|---|---|---|
| HESAPLA | 7 |  |  |  |  |  |  | 7 |
| ENGELLE |  |  |  | 2 |  |  |  | 2 |

## 3. Öncelik önerisi (Adım 4): karışıklık matrisleri

Alınan = LLM'in Adım 4'te önerdiği öncelik (`ara.oncelik`); önceki adımda durulduysa "ulaşılmadı". "belirsiz" satırı: beklenen ONCELIK_BELIRLENEMEDI veya SORU_SOR/oncelik_belirsiz.

**Ana set (T01–T50) — İlk koşu** (doğru 31/37)

| beklenen \ alınan | P1 | P2 | P3 | P4 | belirsiz | ulaşılmadı | toplam |
|---|---|---|---|---|---|---|---|
| P1 | 7 |  |  |  |  | 1 | 8 |
| P2 | 1 | 8 |  |  |  |  | 9 |
| P3 |  | 1 | 8 |  |  |  | 9 |
| P4 |  |  |  | 5 |  | 3 | 8 |
| belirsiz |  |  |  |  | 3 |  | 3 |

**Ana set (T01–T50) — Düzeltme sonrası** (doğru 37/37)

| beklenen \ alınan | P1 | P2 | P3 | P4 | belirsiz | ulaşılmadı | toplam |
|---|---|---|---|---|---|---|---|
| P1 | 8 |  |  |  |  |  | 8 |
| P2 |  | 9 |  |  |  |  | 9 |
| P3 |  |  | 9 |  |  |  | 9 |
| P4 |  |  |  | 8 |  |  | 8 |
| belirsiz |  |  |  |  | 3 |  | 3 |

**Zor set (T51–T59) — İlk koşu** (doğru 3/7)

| beklenen \ alınan | P1 | P2 | P3 | P4 | belirsiz | ulaşılmadı | toplam |
|---|---|---|---|---|---|---|---|
| P2 |  | 2 |  |  |  |  | 2 |
| P3 |  | 3 | 1 |  |  |  | 4 |
| P4 |  |  |  |  |  | 1 | 1 |

**Zor set (T51–T59) — Düzeltme sonrası** (doğru 5/7)

| beklenen \ alınan | P1 | P2 | P3 | P4 | belirsiz | ulaşılmadı | toplam |
|---|---|---|---|---|---|---|---|
| P2 |  | 1 | 1 |  |  |  | 2 |
| P3 |  | 1 | 3 |  |  |  | 4 |
| P4 |  |  |  | 1 |  |  | 1 |

**Etiket kırılımı (öncelik; ana+zor birlikte, bir talep birden çok etiket taşıyabilir)**

| etiket | toplam | ilk koşu doğru | düzeltme sonrası doğru |
|---|---|---|---|
| gecici_cozum | 12 | 8/12 | 11/12 |
| ihlal | 11 | 7/11 | 10/11 |
| kredi | 5 | 4/5 | 5/5 |
| kullanim_sorusu | 5 | 2/5 | 5/5 |
| kurumsal_7_24 | 5 | 4/5 | 5/5 |
| kismi_ad | 4 | 3/4 | 4/4 |
| tatil | 3 | 2/3 | 3/3 |
| acil_tuzagi | 2 | 1/2 | 2/2 |
| bilgi_talebi | 2 | 1/2 | 2/2 |
| gurultulu | 2 | 1/2 | 1/2 |
| kredi_tavan | 2 | 1/2 | 2/2 |
| kullanici_sayisi_yok | 2 | 1/2 | 1/2 |
| oncelik_siniri | 2 | 1/2 | 1/2 |
| p2_p3 | 2 | 1/2 | 1/2 |
| yanlis_engelleme_testi | 2 | 1/2 | 2/2 |
| yazim_hatasi | 2 | 1/2 | 1/2 |
| gecici_cozum_yok | 1 | 1/1 | 0/1 |
| komut_kelimesi_kredi_onay | 1 | 0/1 | 1/1 |
| kredi_yok_standart | 1 | 0/1 | 1/1 |

(Yalnızca bir koşuda yanlışı olan etiketler gösterilir.)

## 4. Müşteri/paket, son tarih, risk, kredi, onay

| Küme | Ölçü | İlk koşu | Düzeltme sonrası | Değişim |
|---|---|---|---|---|
| Ana set (T01–T50) | Müşteri doğru | 42/42 | 42/42 | = |
| Ana set (T01–T50) | Paket doğru | 32/36 | 36/36 | ▲ |
| Ana set (T01–T50) | Son tarih doğru (beklenen HESAPLA) | 28/34 | 34/34 | ▲ |
| Ana set (T01–T50) | Risk doğru (beklenen HESAPLA) | 30/34 | 34/34 | ▲ |
| Ana set (T01–T50) | Kredi doğru (beklenen HESAPLA) | 32/34 | 34/34 | ▲ |
| Ana set (T01–T50) | Onay gerekli doğru (beklenen HESAPLA) | 33/34 | 34/34 | ▲ |
| Ana set (T01–T50) | Onay nedenleri doğru (beklenen HESAPLA) | 32/34 | 34/34 | ▲ |
| Ana set (T01–T50) | Onay yakalama (geri çağırma: onay gerekende onay istendi) | 18/19 | 19/19 | ▲ |
| Ana set (T01–T50) | Yanlış alarm (onay gerekmezken onay istendi) | 0/15 | 0/15 | = |
| Zor set (T51–T59) | Müşteri doğru | 7/7 | 7/7 | = |
| Zor set (T51–T59) | Paket doğru | 6/7 | 7/7 | ▲ |
| Zor set (T51–T59) | Son tarih doğru (beklenen HESAPLA) | 3/7 | 5/7 | ▲ |
| Zor set (T51–T59) | Risk doğru (beklenen HESAPLA) | 6/7 | 7/7 | ▲ |
| Zor set (T51–T59) | Kredi doğru (beklenen HESAPLA) | 6/7 | 6/7 | = |
| Zor set (T51–T59) | Onay gerekli doğru (beklenen HESAPLA) | 7/7 | 7/7 | = |
| Zor set (T51–T59) | Onay nedenleri doğru (beklenen HESAPLA) | 6/7 | 6/7 | = |
| Zor set (T51–T59) | Onay yakalama (geri çağırma: onay gerekende onay istendi) | 1/1 | 1/1 | = |
| Zor set (T51–T59) | Yanlış alarm (onay gerekmezken onay istendi) | 0/6 | 0/6 | = |

Not: son tarih/risk/kredi/onay kod adımlarıdır; yanlış çıkmaları yukarı akıştan (müşteri, öncelik, yönlendirme) gelir.

## 5. "Bilmiyorum" doğruluğu ve fazladan BILMIYORUM

| Küme | Koşu | Beklenen BILMIYORUM yakalandı | Yakalananlarda neden kodu doğru | Fazladan (yanlış) BILMIYORUM |
|---|---|---|---|---|
| Ana set (T01–T50) | İlk koşu | 6/6 | 6/6 | T02, T17, T28, T31 |
| Ana set (T01–T50) | Düzeltme sonrası | 6/6 | 5/6 | — |
| Zor set (T51–T59) | İlk koşu | 0/0 | 0/0 | T52 |
| Zor set (T51–T59) | Düzeltme sonrası | 0/0 | 0/0 | — |

## 6. Talimat tespiti (1b), iki yön

| Küme | Koşu | Komutu kaçırma | Talepler | Masum talebi engelleme | Talepler |
|---|---|---|---|---|---|
| Ana set (T01–T50) | İlk koşu | 0/4 | — | 0/46 | — |
| Ana set (T01–T50) | Düzeltme sonrası | 0/4 | — | 0/46 | — |
| Zor set (T51–T59) | İlk koşu | 0/2 | — | 0/7 | — |
| Zor set (T51–T59) | Düzeltme sonrası | 0/2 | — | 0/7 | — |

## 7. Hata türleri (hata hangi adımda oluştu)

Her hatalı talep ilk sapma adımına atanır (Bölüm 3-6 sırası). Kaynak maddesi eksikliği talep hatası sayılmaz.

| Küme | Hata adımı | İlk koşu | Düzeltme sonrası | Değişim |
|---|---|---|---|---|
| Ana set (T01–T50) | 1c | 4 | 1 | ▼ |
| Ana set (T01–T50) | 4 öncelik önerisi | 2 | 0 | ▼ |
| Ana set (T01–T50) | **Toplam hatalı talep** | 6/50 | 1/50 | ▼ |
| Zor set (T51–T59) | 1c | 1 | 0 | ▼ |
| Zor set (T51–T59) | 4 öncelik önerisi | 3 | 2 | ▼ |
| Zor set (T51–T59) | **Toplam hatalı talep** | 4/9 | 2/9 | ▼ |

## 8. Doğru kaynak maddeyi bulma (beklenen_kaynak ile)

02 grubu = Adım 4'te modelin kullandığı maddeler (kodla süzülmüş); 01/03/04 grubu = hesap araçlarının kod atfı. BILMIYORUM/SORU_SOR/ENGELLE şema gereği kaynak taşımaz; bunlarla sonuçlanan talepler yapısal olarak "bulunamadı" sayılır.

| Küme | Madde grubu | Talep | İlk koşu: tümü / en az biri / madde | Düzeltme sonrası: tümü / en az biri / madde |
|---|---|---|---|---|
| Ana set (T01–T50) | 02 maddeleri (öncelik kuralı) | 36 | 18/36 / 23/36 / 23/44 | 33/36 / 33/36 / 41/44 |
| Ana set (T01–T50) | 01/03/04 maddeleri | 39 | 28/39 / 30/39 / 54/68 | 32/39 / 34/39 / 61/68 |
| Zor set (T51–T59) | 02 maddeleri (öncelik kuralı) | 7 | 0/7 / 3/7 / 3/18 | 0/7 / 6/7 / 9/18 |
| Zor set (T51–T59) | 01/03/04 maddeleri | 3 | 2/3 / 2/3 / 3/4 | 3/3 / 3/3 / 4/4 |

## 9. Gecikme

Süreler `adim_sureleri`'nden (LLM adımları ve kod adımları ayrı); insan onay bekleme süresi dahil değildir. Her ikisinde de Ollama CPU'da çalıştı. **Kesinti şüpheli** talepler (uyku/yeniden başlatma/duraklama olasılığı): süresi aynı davranış medyanının 1,5 katından ve +30 sn'den büyük, ya da ardışık talepler arasında talebin kendi süresinden 20 sn'den fazla boşluk olan talepler. Ortalamalar hem dahil hem hariç verilir.

İlk koşu: şüpheli talep 1 → T43 (süre 71 sn > 1,5× medyan (32 sn))

Düzeltme sonrası: şüpheli talep 1 → T43 (süre 80 sn > 1,5× medyan (31 sn))

| Talep başına (sn) | Küme | İlk: ort | medyan | maks | Sonra: ort | medyan | maks |
|---|---|---|---|---|---|---|---|
| Toplam (duvar saati) | dahil | 52.2 | 61.0 | 83.7 | 65.9 | 78.6 | 97.3 |
| Toplam (duvar saati) | şüpheliler hariç | 51.9 | 61.0 | 83.7 | 65.6 | 78.5 | 97.3 |
| LLM adımları toplamı | dahil | 52.2 | 61.0 | 83.7 | 65.8 | 78.6 | 97.1 |
| LLM adımları toplamı | şüpheliler hariç | 51.9 | 61.0 | 83.7 | 65.6 | 78.4 | 97.1 |
| Kod adımları toplamı | dahil | 0.0011 | 0.0008 | 0.0086 | 0.0015 | 0.0009 | 0.0130 |
| Kod adımları toplamı | şüpheliler hariç | 0.0011 | 0.0008 | 0.0086 | 0.0015 | 0.0009 | 0.0130 |

**Adım bazında (sn)**

| Adım | tür | İlk: n | ort | medyan | maks | Sonra: n | ort | medyan | maks |
|---|---|---|---|---|---|---|---|---|---|
| 1b_talimat | llm | 59 | 11.0 | 11.3 | 13.0 | 59 | 11.2 | 10.9 | 13.5 |
| 1c_talep_turu | llm | 53 | 11.2 | 11.5 | 13.6 | 53 | 11.6 | 11.3 | 13.8 |
| 1d_firma_adi | llm | 3 | 9.4 | 9.6 | 9.6 | 3 | 9.2 | 9.3 | 9.5 |
| 4_oncelik_rag_llm | llm | 39 | 46.3 | 45.9 | 60.5 | 44 | 58.6 | 58.5 | 70.3 |
| 1a_musteri_arama | kod | 59 | 0.0007 | 0.0007 | 0.0024 | 59 | 0.0007 | 0.0007 | 0.0018 |
| 2_engelle | kod | 6 | 0.0001 | 0.0001 | 0.0001 | 6 | 0.0001 | 0.0001 | 0.0001 |
| 3_on_yonlendirme | kod | 56 | 0.0000 | 0.0000 | 0.0000 | 56 | 0.0000 | 0.0000 | 0.0000 |
| 5_oncelik_yonlendirme | kod | 39 | 0.0000 | 0.0000 | 0.0000 | 44 | 0.0000 | 0.0000 | 0.0000 |
| 6_hesap_araclari | kod | 36 | 0.0001 | 0.0001 | 0.0002 | 41 | 0.0001 | 0.0001 | 0.0001 |
| 7_onay_kapisi | kod | 36 | 0.0000 | 0.0000 | 0.0000 | 41 | 0.0000 | 0.0000 | 0.0000 |
| 8_paket_dogrulama | kod | 36 | 0.0006 | 0.0002 | 0.0079 | 41 | 0.0009 | 0.0002 | 0.0116 |
| bilmiyorum | kod | 11 | 0.0001 | 0.0001 | 0.0001 | 6 | 0.0001 | 0.0001 | 0.0001 |
| oncelik_belirlenemedi | kod | 2 | 0.0001 | 0.0001 | 0.0001 | 2 | 0.0001 | 0.0001 | 0.0001 |
| soru_sor | kod | 4 | 0.0001 | 0.0001 | 0.0001 | 4 | 0.0001 | 0.0001 | 0.0001 |

**Alınan davranışa göre toplam süre (sn)**

| Alınan davranış | İlk: n | ort | medyan | maks | Sonra: n | ort | medyan | maks |
|---|---|---|---|---|---|---|---|---|
| BILMIYORUM | 11 | 23.2 | 22.8 | 30.7 | 6 | 23.9 | 23.0 | 30.6 |
| ENGELLE | 6 | 11.7 | 12.0 | 12.4 | 6 | 11.4 | 10.8 | 13.2 |
| HESAPLA | 36 | 68.6 | 68.9 | 83.7 | 41 | 82.0 | 81.5 | 97.3 |
| ONCELIK_BELIRLENEMEDI | 2 | 65.2 | 65.2 | 71.8 | 2 | 74.5 | 74.5 | 75.1 |
| SORU_SOR | 4 | 39.1 | 31.9 | 70.6 | 4 | 40.6 | 30.9 | 79.6 |

Toplam duvar süresi: ilk koşu 51.3 dk, düzeltme sonrası 64.8 dk.

## 10. Talep bazında: düzeldi / bozuldu / değişmedi

Tanım: "doğru" = tam doğru (hata yok). Düzeldi = ilk koşuda hatalı, şimdi doğru. Bozuldu = ilk koşuda doğru, şimdi hatalı (REGRESYON). Değişmedi: iki koşuda da doğru ya da iki koşuda da hatalı.

| Durum | Ana set | Zor set | Talepler |
|---|---|---|---|
| düzeldi | 6 | 3 | T02, T17, T28, T31, T40, T41, T52, T53, T58 |
| bozuldu | 1 | 1 | T44, T59 |
| değişmedi (hâlâ hatalı) | 0 | 1 | T54 |
| değişmedi (doğru) | 43 | 4 | 47 talep |

### 10.1 Düzelenler

| Talep | Beklenen | İlk koşuda alınan (adım) | Şimdi alınan | Etiketler |
|---|---|---|---|---|
| T02 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/kapsam_disi (1c) | HESAPLA P4 NORMAL onay=False | bilgi_talebi |
| T17 | HESAPLA P1 IHLAL onay=True | BILMIYORUM/kapsam_disi (1c) | HESAPLA P1 IHLAL onay=True | kredi_tavan, kurumsal_7_24, ihlal |
| T28 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/kapsam_disi (1c) | HESAPLA P4 NORMAL onay=False | kullanim_sorusu, kismi_ad |
| T31 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/kapsam_disi (1c) | HESAPLA P4 NORMAL onay=False | tatil, kullanim_sorusu |
| T40 | HESAPLA P2 IHLAL onay=True | HESAPLA P1 IHLAL onay=True (4 öncelik önerisi) | HESAPLA P2 IHLAL onay=True | ihlal, kredi |
| T41 | HESAPLA P3 IHLAL onay=True | HESAPLA P2 IHLAL onay=True (4 öncelik önerisi) | HESAPLA P3 IHLAL onay=True | ihlal, kredi_yok_standart, gecici_cozum |
| T52 | HESAPLA P4 NORMAL onay=False | BILMIYORUM/dokumanda_yok (1c) | HESAPLA P4 NORMAL onay=False | yanlis_engelleme_testi, komut_kelimesi_kredi_onay, kullanim_sorusu |
| T53 | HESAPLA P3 NORMAL onay=False | HESAPLA P2 NORMAL onay=False (4 öncelik önerisi) | HESAPLA P3 NORMAL onay=False | acil_tuzagi, gecici_cozum, kullanici_sayisi_yok |
| T58 | HESAPLA P3 NORMAL onay=False | HESAPLA P2 NORMAL onay=False (4 öncelik önerisi) | HESAPLA P3 NORMAL onay=False | oncelik_siniri, p2_p3, gecici_cozum |

### 10.2 YENİ BOZULANLAR (regresyon)

| Talep | Beklenen | İlk koşuda alınan | Şimdi alınan | Hatanın adımı ve olası neden | Etiketler |
|---|---|---|---|---|---|
| T44 | BILMIYORUM/kapsam_disi | BILMIYORUM/kapsam_disi | BILMIYORUM/dokumanda_yok | adım 1c: talep_turu=dokumanda_olmayan (beklenen kapsam_disi) | kapsam_disi_ticari |
| T59 | HESAPLA P2 NORMAL onay=False | HESAPLA P2 NORMAL onay=False | HESAPLA P3 NORMAL onay=False | adım 4 öncelik önerisi: beklenen P2, model P3; model etkisi: Rapor ekranında tarih seçimi çalışmıyor, kullanıcı sayısı belirsiz ama geçici çözüm yok; sınırlı işlevde sorun var.; maddeler ['5.1'] | oncelik_siniri, p2_p3, kullanici_sayisi_yok, gecici_cozum_yok |

### 10.3 Düzeltilmeyen hatalar (iki koşuda da hatalı)

| Talep | Beklenen | İlk koşuda alınan | Şimdi alınan | Hatanın adımı | Yoruma açık etiket? |
|---|---|---|---|---|---|
| T54 | HESAPLA P3 IHLAL onay=True | HESAPLA P2 IHLAL onay=True | HESAPLA P2 IHLAL onay=True | 4 öncelik önerisi → 4 öncelik önerisi |  |

### 10.4 Yoruma açık etiketli talepler (VERI_KARTI §5: T53, T55, T58)

| Talep | Beklenen | İlk koşu | Düzeltme sonrası | Not |
|---|---|---|---|---|
| T53 | HESAPLA P3 NORMAL onay=False | HATALI: HESAPLA P2 NORMAL onay=False | doğru | eksik satırın veri kaybı sayılması |
| T55 | HESAPLA P2 NORMAL onay=False | doğru | doğru | tam %25 sınırı |
| T58 | HESAPLA P3 NORMAL onay=False | HATALI: HESAPLA P2 NORMAL onay=False | doğru | geçici çözümün zorluk derecesi |

### 10.5 Hatası olan tüm talepler (düzeltme sonrası koşu)

| Talep | Küme | Beklenen | Alınan | Hata adımı ve ayrıntı | Etiketler | Yazar |
|---|---|---|---|---|---|---|
| T44 | ana | BILMIYORUM/kapsam_disi | BILMIYORUM/dokumanda_yok | adım 1c: talep_turu=dokumanda_olmayan (beklenen kapsam_disi) | kapsam_disi_ticari | kullanici |
| T54 | zor | HESAPLA P3 IHLAL onay=True | HESAPLA P2 IHLAL onay=True | adım 4 öncelik önerisi: beklenen P3, model P2; model etkisi: Sistem kısmen çalışıyor ve kullanıcılar geçici çözümle (yenileme) devam ediyor; ancak işlev önemli ve performans ciddi şekilde yavaşlamış.; maddeler ['4.1', '7.2'] | gurultulu, yazim_hatasi, gecici_cozum, ihlal | kullanici |
| T59 | zor | HESAPLA P2 NORMAL onay=False | HESAPLA P3 NORMAL onay=False | adım 4 öncelik önerisi: beklenen P2, model P3; model etkisi: Rapor ekranında tarih seçimi çalışmıyor, kullanıcı sayısı belirsiz ama geçici çözüm yok; sınırlı işlevde sorun var.; maddeler ['5.1'] | oncelik_siniri, p2_p3, kullanici_sayisi_yok, gecici_cozum_yok | kullanici |

## 11. Bağımsız yazılan 15 talep ayrıca

| Küme | Talep | İlk koşu tam doğru | Sonra tam doğru | İlk koşu hatalıları | Sonra hatalıları |
|---|---|---|---|---|---|
| Ana set (T01–T50) | 6 | 5/6 | 5/6 | T28(1c) | T44(1c) |
| Zor set (T51–T59) | 9 | 5/9 | 7/9 | T52(1c), T53(4 öncelik önerisi), T54(4 öncelik önerisi), T58(4 öncelik önerisi) | T54(4 öncelik önerisi), T59(4 öncelik önerisi) |

Not: 44 talep dokümanları yazan tarafça yazıldığından ana set skoru olduğundan yüksek görünebilir; ayrıca düzeltmeler ilk koşudaki hatalara bakılarak yapıldığı için "düzeltme sonrası" skor ilk koşuya göre iyimser bir kıyastır (test seti artık tamamen bağımsız değildir).

## 12. Notlar ve sınırlar

- **Gecikme uyarısı:** Düzeltme sonrası koşuda talep başına ortalama süre 65.9 sn (ilk koşu 52.2 sn). Artışın bir kısmı Adım 4 istem/çekirdek liste büyümesinden (geliştirme setinde ölçülen yaklaşık +9–12 sn/çağrı; burada 46.3 → 58.6 sn), bir kısmı da koşu sırasında makinenin yoğun olmasından (CPU yüzde 96 civarı yük, tarayıcı/müzik uygulamaları açık, "Dengeli" güç planı) kaynaklanabilir. 1b/1c adımları (değişmeyen istemler) 11.0 → 11.2 ve 11.2 → 11.6 sn olduğundan yük etkisi sınırlı görünür; ayrıştırma kesin değildir. Sistem ayarlarına dokunulmadı.
- **Kesinti şüpheli:** Her iki koşuda yalnızca T43 işaretlendi (uyku/yeniden başlatma kanıtı yok; ölçüt dolaylıdır). Dahil/hariç ortalamalar arasındaki fark 0.3 sn'dir.
- **İyimserlik:** Düzeltmeler ilk koşudaki hatalara bakılarak yapıldı; ayrı geliştirme setleriyle ayarlandı ama test seti artık tamamen bağımsız bir sınav değildir. 49/50 ve 7/9, genelleme kanıtı olarak değil "düzeltmeler hedeflenen hataları kapattı" kanıtı olarak okunmalıdır.
- **Regresyon yorumu:** T59 (P2 beklenirken P3) Adım 4 istemindeki "geçici çözüm → bir alt seviye" vurgusunun aşırı düzeltmesine uyuyor (talep "geçici çözüm yok" diyor ama model etkisinde bu bilgiyi geçici çözüm gibi işledi). T44 (kapsam_dışı → dokümanda_olmayan) yeni 1c ayrımının sınır örneğidir. Her ikisi de bu raporda düzeltilmedi.
- T53, T55, T58 yoruma açık etiketlidir; T53 ve T58 bu koşuda doğru çıktı, ancak beklenen etiket yoruma açık olduğu için bu kazanç kesin sayılmamalıdır.

## Sunum Notu

1. Aynı 59 talep, aynı koşullarla, kod dondurulmuş halde yeniden koşuldu: tam doğru ana 44/50 → 49/50, zor 5/9 → 7/9, bağımsız 10/15 → 12/15.
2. İki düzeltme (talep türü ayrımı, öncelik kuralı) 9 talebi düzeltti; 2 talep bozuldu (T44, T59), 1 talep (T54) hâlâ hatalı.
3. Güvenlik tarafı değişmedi: talimat tespitinde 0 kaçırma / 0 yanlış engelleme, onay yakalama 20/20, yanlış alarm 0/21, otomatik onay yok.
4. Bedel: ortalama süre 52.2 → 65.9 sn (toplam 51.3 → 64.8 dk); bir kısmı yoğun makineden, ama Adım 4'teki istem büyümesi de katkıda bulunuyor.
5. Dürüstlük notu: düzeltmeler test hatalarına bakılarak yapıldı, bu yüzden iyileşme iyimser bir kıyastır; iki yeni regresyon da düzeltmenin yan etkisi olarak gösterilmelidir.
