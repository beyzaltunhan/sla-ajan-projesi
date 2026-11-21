# Veri Kartı – SLA Uyum ve Eskalasyon Ajanı

Sürüm 1.0 · 21 Kasım 2026 · BTK Akademi / Entertech Yapay Zekâ Çözümleri Kariyer Geliştirme Atölyesi bireysel final projesi

## 1. Özet

Bu projede kullanılan **tüm veri kurgusal ve sentetiktir**. Gerçek bir firmaya, müşteriye, sözleşmeye veya kişiye ait bilgi içermez. Firma adı (Poyraz Bulut Yazılım A.Ş.), müşteri adları, rakamlar ve talepler eğitim amacıyla uydurulmuştur. Ad çakışması mümkün olduğunca kontrol edilmiştir ancak garanti edilemez; çakışma varsa tesadüftür.

Veri; bilgi tabanı (4 doküman), müşteri kayıtları, kural yapılandırması ve test setinden oluşur.

## 2. Veri varlıkları

| Varlık | Dosya | İçerik |
|---|---|---|
| SLA Sözleşmesi | `docs/01_sla_sozlesmesi.md` | 8 madde, ~880 kelime; ilk yanıt süreleri, mesai, sayaç, risk, kredi, kapsam dışı |
| Öncelik Belirleme Rehberi | `docs/02_oncelik_rehberi.md` | 10 madde, ~760 kelime; P1–P4 kuralları, örnekler, belirsizlik |
| Eskalasyon ve Onay Prosedürü | `docs/03_eskalasyon_proseduru.md` | 10 madde, ~550 kelime; onay şartları, onay süreci |
| Destek SSS | `docs/04_destek_sss.md` | 10 soru, ~390 kelime |
| Kural yapılandırması | `data/sla_config.json` | Süreler, mesai, tatiller, kredi oranları, risk eşiği (hesabın tek kaynağı) |
| Müşteri kayıtları | `data/musteriler.json` | 10 müşteri: paket, aylık ücret, bu ay kredi yüzdesi, özel anlaşma bayrağı |
| Test seti | `data/test_seti.json` | 59 talep ve elle hesaplanmış beklenen cevaplar |

Bilgi tabanı iki işi paylaşır: **hesaplar** `sla_config.json` ile Python araçlarında yapılır; **kaynak, gerekçe ve kapsam kararı** dokümanlardan (RAG) gelir. İki kaynağın rakamları `tutarlilik_kontrolu.py` ile otomatik karşılaştırılır.

## 3. Test seti

59 talep iki ayrı küme olarak raporlanır:

| Küme | Talep | Amaç |
|---|---|---|
| **Ana set** (T01–T50) | 50 | Dengeli dağılım; normal koşullarda başarıyı ölçer, başlık sonucu bu kümedir |
| **Zor set** (T51–T59) | 9 | Stres testi: yanlış engelleme, "acil" tuzağı, gürültülü metin, dolaylı komut, öncelik sınırı |

**Ana set dağılımı (50):** normal 9, mesai dışı/hafta sonu/tatil 7, kurumsal P1 7/24 4, ihlal ve risk 8, kredi 6, SORU_SOR 4, BILMIYORUM 6, ENGELLE 4, ÖNCELİK BELİRLENEMEDİ 2.

**Zor set dağılımı (9):** yanlış engelleme 2, "acil" tuzağı 1, gürültülü metin 2, dolaylı komut 2, öncelik sınırı 2.

**Beklenen davranış sınıfları:** HESAPLA, SORU_SOR, BILMIYORUM, ENGELLE, ÖNCELİK_BELİRLENEMEDİ. Hata yolu (ISLENEMEDI) ayrı bir hata türü olarak raporlanır, davranış sınıfı değildir.

**HESAPLA taleplerinde (41):** öncelik P1 8, P2 11, P3 13, P4 9; risk NORMAL 25, YUKSEK 5, IHLAL 11; paket Gelişmiş 17, Kurumsal 14, Standart 10.

**Yazar:** 59 talebin 15'i proje sahibi tarafından, 44'ü Claude tarafından yazılmıştır (`yazar` alanı). Bağımsız yazılan metinler ayrıca raporlanabilir.

**Alanlar:** her talepte kayıt zamanı, "şimdi", beklenen cevap (davranış, neden, müşteri, paket, öncelik, son tarih, risk, kredi, onay nedenleri), beklenen kaynak maddeler (geri çağırma ölçümü için), etiketler (örn. geçici çözüm, sınır değeri, tatil) ve elle yazılmış hesap notu bulunur. 48 talepte beklenen kaynak tanımlıdır; kalanlarda (SORU_SOR, ENGELLE, kayıtsız müşteri) kaynak getirme değerlendirilmez.

## 4. Doğrulama

- Beklenen değerlerin **tamamı elle hesaplanmıştır**; kodun çıktısından türetilmemiştir.
- Her HESAPLA talebi için son tarih, risk, kredi ve onay nedenleri araçlarla çapraz kontrol edilir.
- Her beklenen çıktı Pydantic şemasına (`schemas/onay_paketi.py`) uygunluk açısından doğrulanır.
- Kaynak madde numaralarının dokümanlarda gerçekten bulunduğu otomatik kontrol edilir.
- `tutarlilik_kontrolu.py`: süre tablosu, kredi tablosu, tatiller, mesai, %25 eşiği, risk etiketleri, madde atıfları ve firma adı için doküman–config–kod uyumu.
- Test paketi: 222 test (hesap araçları, şema, test seti, tutarlılık). Testlerin hata yakaladığı, beklenen değerler bilerek bozularak denenmiştir.

## 5. Varsayımlar ve sınırlamalar

**Takvim ve süre**
- Tatil takvimi **basitleştirilmiştir**: yalnızca 4 gün (29 Ekim 2026, 1 Ocak, 23 Nisan, 1 Mayıs 2027). Dini bayramlar ve diğer resmî tatiller dahil değildir.
- Mesai hafta içi 09:00–18:00, öğle arası yok. Saat dilimi ve yaz saati yoktur.
- Yalnızca **ilk yanıt süresi** vardır; çözüm süresi ve uptime kapsam dışıdır.

**Kapsam varsayımı**
- Ajan yalnızca **ilk yanıtı henüz verilmemiş açık talepleri** değerlendirir. "İlk yanıt zamanı" alanı yoktur; ihlal = şimdi > son tarih. Geç yanıtlanmış taleplerin sonradan değerlendirilmesi bu prototipte yoktur.
- Talep kayıt zamanı ve "şimdi" kullanıcıdan değil sistemden gelir.

**Kredi**
- Hizmet kredisi her sözleşmede bulunmaz; bu kurgusal sözleşmeye özgüdür ve ikincil bir bölümdür.
- Özel hükümlü müşterilerin kuralları dokümanlarda yoktur; ajan bu müşteriler için "Dokümanda bilgi bulunmamaktadır" der.

**Veri ve ölçüm**
- Müşteri sayısı (10) ve test seti (59) küçüktür. Sonuçlar yüzde olarak değil **"kaç/50" ve "kaç/9"** olarak raporlanır; küçük farklar yorumlanmaz.
- Test taleplerinin çoğu (44/59) dokümanları yazan kişi tarafından yazılmıştır; bu skorları olduğundan yüksek gösterebilir. Bu yüzden bağımsız yazılmış 15 talep işaretlenmiştir.
- Bazı beklenen etiketler yoruma açıktır (örn. T53 eksik satırın veri kaybı sayılmaması, T55 tam %25 sınırı, T58 geçici çözümün zorluk derecesi). Bu taleplerde farklı cevap bir hata olduğu kadar "belirsiz etiket" de olabilir; hata türleri analizinde ayrıca yorumlanır.
- P1/P2 sınırı ve dolaylı komut örnekleri sınırlı sayıdadır.
- Bu projenin senaryosu (SLA süre ve eskalasyon yönetimi) Entertech firmalarındaki gerçek bir sorunun kanıtı değildir; **makul bir kurumsal senaryo** olarak sunulur ve doğrulanmamıştır.

## 6. Raporlama kuralları

- Ana set ve zor set **ayrı satırlarda** raporlanır; ikisi karıştırılmaz.
- Ajanın **ilk çalıştırma** sonuçları kaydedilir ve sunumda gösterilir. Sonradan yapılan düzeltmelerle elde edilen sonuç ayrıca "düzeltme sonrası" olarak belirtilir.
- Ölçümler: öncelik doğruluğu (karışıklık matrisiyle), müşteri/paket çıkarma, son tarih doğruluğu, risk sınıfı, onay gerekli yakalama (geri çağırma), "bilmiyorum" doğruluğu, doğru kaynak maddeyi bulma, hata türleri (hangi adımda), gecikme (LLM ve kod adımları ayrı).

## 7. Gizlilik ve etik

Veri setinde kişisel veri yoktur. Hiçbir gerçek müşteri sözleşmesi veya destek kaydı kullanılmamıştır. Talepler tamamen kurgusaldır.
