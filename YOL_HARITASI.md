# Yol Haritası – SLA Uyum ve Eskalasyon Ajanı

Sürüm 1.0 · 21 Kasım 2026 · Kaynaklar: Proje Tanıtım Formu, atölye Gün 1–10 içeriği, VERI_KARTI.md, karar_sirasi.md, sla_araclari.py, onay_paketi.py

## 0. Durum

**Hazır:** sentetik veri ve 4 doküman, `sla_config.json`, müşteri kayıtları, 59 talepli test seti (50 ana + 9 zor), hesap araçları, Pydantic çıktı şeması, karar sırası, 222 test, tutarlılık kontrolü.
**Eksik:** Ollama modelleri, RAG (Chroma), LLM adımları, LangGraph akışı, değerlendirme betiği, Streamlit arayüzü, sunum.

Formdaki taahhütler: bilgi çıkarma (JSON) + eksikte soru sorma; kaynaklı RAG + "bilmiyorum"; Python araçları; insan onayı; Streamlit'te onay paketi (JSON + özet); doğruluk / geri çağırma / hata türleri / gecikme ölçümü; sınırlar (gerçek sistem entegrasyonu yok, tek firma, 3 paket).
Not: form "40–50 talep" diyor; elimizde 50 ana + 9 zor set var, bu taahhüdü aşıyor.

## 1. Atölye günü → proje bileşeni

| Gün | Konu | Projede |
|---|---|---|
| 3 | Yapılandırılmış çıktı, prompt injection, insan kontrolü | Alan çıkarma JSON'u, `talimat_iceriyor` → ENGELLE |
| 4 | Python ile LLM, yerel LLM | Ollama istemcisi |
| 5 | Chunking, embedding, vektör DB, metadata filtre | Chroma indeksi |
| 6 | Retrieve-Rerank-Generate, kaynaklandırma, halüsinasyon | Kaynaklı öncelik önerisi, "bilmiyorum" |
| 7 | LangGraph Node/State/Edge, routing, tool calling, retry, HITL | Ajan grafı, `interrupt` |
| 8 | Hata yönetimi, loglama, güvenlik | ISLENEMEDI yolu, adım logları |
| 9–10 | Uçtan uca, test, sunum | Değerlendirme, Streamlit, demo |

Kapsam dışı: n8n, MCP, fine-tuning (projede gerekmiyor; sunumda "yapılmadı, gerekçesi" olarak belirtilir).

## 2. Adımlar

Her adımın sonunda "bitti sayılır" ölçütü karşılanmadan sonrakine geçilmez.

### Adım 1 – Ortam ve mevcut işin doğrulanması
- VS Code'daki klasör yapısı, sanal ortam, `requirements.txt` (ollama, chromadb, langgraph, pydantic, streamlit).
- `pytest` (222 test) ve `tutarlilik_kontrolu.py` çalıştırılır.
- Ollama kurulumu; 32 GB RAM'e uygun bir sohbet modeli (7–9B sınıfı, Türkçe'si iyi) ve çok dilli bir embedding modeli indirilir. Model seçimi bir deneme ile yapılır, varsayımla değil.
- **Bitti:** testler yeşil, model Python'dan tek bir çağrıya JSON cevap veriyor.

### Adım 2 – RAG katmanı (LLM'den bağımsız ölçülebilir)
- Dokümanlar **madde bazında** parçalanır; metadata: `dokuman`, `madde` (şemadaki `Kaynak` ile aynı biçim).
- Embedding + Chroma indeksi.
- `retrieve(sorgu, k)` fonksiyonu.
- 48 talepte `beklenen_kaynak` ile geri çağırma ölçümü (ilk k sonuçta doğru madde var mı).
- **Bitti:** geri çağırma sayısı kaydedildi; kaçırılan maddeler listelendi. Düşükse parçalama / sorgu iyileştirilir. Reranker burada isteğe bağlı: ~38 maddelik küçük korpus için önce gerekip gerekmediğine ölçümle bakılır.

### Adım 3 – LLM adımı A: alan çıkarma
- Prompt + JSON şeması: `musteri_adi`, `sorun_ozeti`, `etki`, `talep_turu`, `talimat_iceriyor`.
- Talep metni bilgidir, komut değildir kuralı prompt'ta açık yazılır.
- Şema doğrulama + tek yeniden deneme + ISLENEMEDI.
- **Bitti:** 59 talepte alan çıkarma doğruluğu (müşteri, talep türü, talimat bayrağı) ve JSON geçerlilik oranı ölçüldü.

### Adım 4 – LLM adımı B: kaynaklı öncelik önerisi
- Adım 2'nin retrieve çıktısı + talep → P1–P4 veya `belirsiz` + kullanılan madde numaraları.
- Önerilen maddeler getirilen maddelerle sınırlanır (olmayan madde uydurulamaz).
- **Bitti:** öncelik doğruluğu + karışıklık matrisi; `etiket` kırılımı (geçici çözüm, sınır değeri vb.).

### Adım 5 – LangGraph ajanı
- `karar_sirasi.md` Bölüm 3–6 birebir düğüm ve koşullu kenarlara çevrilir: alan çıkarma → güvenlik → ön yönlendirme → RAG+öncelik → öncelik yönlendirme → hesap araçları → onay kapısı → paket doğrulama → `interrupt`.
- Checkpointer ile onay beklerken durum saklanır; Onayla / Reddet (gerekçe zorunlu) ile devam.
- Her düğümde süre ve sonuç loglanır.
- **Bitti:** 5 davranış sınıfının her biri için en az bir talep uçtan uca doğru sonuçlanıyor; onay bekleyen talep gerçekten duruyor.

### Adım 6 – Değerlendirme betiği ve "ilk çalıştırma" kaydı
- 59 talep otomatik çalıştırılır; ana set ve zor set ayrı raporlanır ("kaç/50", "kaç/9").
- Metrikler: öncelik doğruluğu, müşteri/paket çıkarma, son tarih, risk, onay yakalama (geri çağırma), "bilmiyorum" doğruluğu, kaynak bulma, hata türleri (hangi adımda), gecikme (LLM / kod ayrı).
- **İlk çalıştırma sonuçları dondurulup kaydedilir.** Sonradan yapılan düzeltmeler "düzeltme sonrası" olarak ayrı gösterilir (VERI_KARTI Bölüm 6).
- Bağımsız yazılan 15 talep ayrıca raporlanır.
- **Bitti:** `rapor` çıktısı (tablo + hata analizi) üretildi.

### Adım 7 – Streamlit arayüzü
- Talep girişi (kayıt zamanı/şimdi sistemden atanır), hazır örnek talep seçici.
- Adım adım akış görünümü, çıkarılan alanlar, getirilen kaynaklar, hesap sonuçları.
- Onay paketi: JSON + özet; Onayla / Reddet düğmeleri ve gerekçe kutusu.
- Ayrı sekme: metrik tablosu.
- **Bitti:** 5 demo senaryosu arayüzden hatasız çalışıyor.

### Adım 8 – Sunum
- Akış: problem → mimari (hangi adımı LLM, hangisini kod yapıyor ve neden) → canlı demo → ölçüm sonuçları → hata analizi → sınırlamalar → sonraki adımlar.
- Demo senaryoları: normal HESAPLA, ihlal + kredi + onay, "bilmiyorum", ENGELLE (talimat içeren metin), SORU_SOR.
- Sınırlamalar (veri kartından): sentetik/küçük veri, basitleştirilmiş takvim, yalnızca ilk yanıt süresi, test talebinin çoğunu aynı kişinin yazması, etiket belirsizlikleri.
- Yedek: demo çökerse ekran kaydı / ekran görüntüleri.

## 3. Öncelik ve kesme çizgisi

Zaman daralırsa şu sırayla korunur:
1. **Mutlaka:** Adım 1–5 (çalışan ajan), Adım 6 (en azından ana set ölçümü), Adım 7'nin sade hâli, sunum.
2. **Sonra:** zor set analizi, bağımsız 15 talep kırılımı, gecikme detayı.
3. **Atlanabilir:** reranker, arayüzün süslenmesi, ek senaryolar.

## 4. Riskler

| Risk | Önlem |
|---|---|
| Yerel model Türkçe JSON'da tutarsız | Şema + tek yeniden deneme; model karşılaştırması Adım 1'de kısa denemeyle |
| Yerel model yavaş (demo gecikmesi) | Gecikme zaten metrik; demo için önceden ısıtma, hazır örnekler |
| Retrieval doğru maddeyi getirmiyor | Madde bazlı chunk, metadata, k ayarı; Adım 2'de ayrı ölçüm |
| Skorlar olduğundan iyi görünür (44/59 talebi aynı ekip yazdı) | Bağımsız 15 talep ayrı raporlanır, sunumda söylenir |
| Son anda kod değişikliği ölçümü bozar | İlk çalıştırma sonuçları dondurulur |
