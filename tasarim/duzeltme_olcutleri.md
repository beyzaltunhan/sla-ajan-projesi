# Düzeltme ölçütleri (tek turluk düzeltme; denemeden ÖNCE yazıldı)

## 1c: talep türü (22 Kasım 2026)

**Sorun (ilk koşudan):** 5 talepte kullanım sorusu / bilgi isteği ya da "entegrasyon" kelimesi geçen gerçek bir arıza bildirimi `kapsam_disi` / `dokumanda_olmayan` sayıldı ve talep yanlışlıkla BILMIYORUM'a gitti. Gerçekten kapsam dışı ve dokümanda olmayan 6 talep ilk koşuda doğru yakalanmıştı; bu davranış bozulmamalı.

**Düzeltme yalnızca geliştirme setinde yapılır** (`deneme/gelistirme_seti.py`). Test setindeki hatalı taleplerin metinleri kopyalanmaz ve uyarlanmaz. Yeni geliştirme örnekleri: `GELISTIRME_1C_YENI` (16: kullanım sorusu/bilgi isteği 8, gerçek kapsam dışı 4, dokümanda olmayan 4; kullanım grubunun biri "entegrasyon" kelimeli gerçek bir arıza bildirimidir).

| Ölçüt | Eşik |
|---|---|
| Eski 1c geliştirme seti (25 örnek) | **25/25** korunur (regresyon yok) |
| Yeni 16 örnekte toplam hata | en fazla **1** |
| Gerçek kapsam dışı (4) + dokümanda olmayan (4) = 8 örnekte hata | **0** |
| Kullanım sorusu / bilgi isteği (8) örnekte hata | en fazla **1** |

**Yöntem:** (1) mevcut istemle yeni 16 örnek ölçülür (düzeltme öncesi referans), (2) düzeltme yapılır, (3) yeni 16 + eski 25 tekrar ölçülür. Ölçütler sonuçlar görüldükten sonra gevşetilmez. Ölçüt tutmazsa sıra: (a) istem/few-shot iyileştirme, (b) yalnızca 1c için Ollama'da yüklü daha büyük yerel model (RAM'e sığma ve gecikme raporlanır), (c) bir kısmını koda alma. En fazla 2 deneme turu. Bu parçada 59 talepli koşu yapılmaz, Adım 4'e dokunulmaz.

## Adım 4: öncelik önerisi (22 Kasım 2026; denemeden ÖNCE yazıldı)

### Hata analizi (ilk koşunun 5 hatası; metinler kopyalanmadı)
Hatalı beş talepte ilgili kuralların hepsi (3.1, 4.1, 5.1, 7.2, 7.3) modele verilen bağlamdaydı (sabit çekirdek listede). Yani **doğru kuralı görmedi** değil, **kuralı yanlış yorumladı**:
- **4 talep (T41, T53, T54, T58; P3 yerine P2):** model geçici çözümün var olduğunu kendi etki cümlesinde yazdı, ama yine de 4.1'i seçti. 4.1'in "geçici çözüm yoksa ya da çok zorsa" koşulunu ve 7.2'nin "kolay geçici çözüm bir alt seviyeye düşürür" kuralını uygulamadı; işlevi adından "önemli" saydı (7.3: önemli işlev = günlük işi engelleyen). T53 ve T58'in etiketi yoruma açık olduğundan bunlar düzeltme hedefi sayılmaz, kategori analizine dahildir.
- **1 talep (T40; P2 yerine P1):** tek bir işlev çalışmıyor ve geçici çözüm yok (4.1 = P2). Model 3.1'e atlayıp "hizmet tamamen kullanılamıyor, üretim ortamı etkilenmiş" yazdı; metinde bu yok. 02 Madde 2.2 (yalnızca açıkça yazılan bilgi) ve 3.1 ("açıkça belirtilmişse") ihlal edildi.

### Planlanan değişiklik (deneme öncesi)
1. **Çekirdek listeye eklenecek:** 02 Madde **2.1** (öncelik üç soruya bakar: hizmet durumu, geçici çözüm, veri/güvenlik riski) ve **2.2** (yalnızca açıkça yazılan bilgi esas alınır, eksik bilgi tahmin edilmez). Neden: ilki geçici çözümü karar basamağı olarak, ikincisi T40'taki aşırı çıkarımı doğrudan hedefler. **2.3 ve 2.4 eklenmeyecek:** ilk koşudaki hataları açıklamıyorlar (T53 düzeltme hedefi değil). Çekirdek 12 → 14 madde.
2. **İstem (SISTEM) — "karar basamakları":** (a) P1 yalnızca metinde AÇIKÇA yazıyorsa: hizmetin tamamı kullanılamıyor / üretim ortamı durmuş / veri kaybı veya güvenlik riski ve geçici çözüm yok; tek bir ekran veya işlev çalışmıyorsa P1 değildir, yazmayan durumu varsayma. (b) Geçici çözüm varsa (elle yapabiliyoruz, eski yöntem, yenileyince düzeliyor vb.) seviye bir alt düşer (7.2): sınırlı/kısmi sorun + geçici çözüm = P3; P2 yalnızca günlük işi engelleyen işlev ve geçici çözüm yok ya da çok zor ise. (c) `etki` cümlesine yalnızca talepte yazan bilgi yazılır.
3. **Few-shot:** 6 → 8 örnek (yeni metinler): (i) önemli görünen bir işlevde sorun + geçici çözüm var → P3 [5.1, 7.2]; (ii) tek işlev çalışmıyor, geçici çözüm yok, diğer modüller sağlam → P2, P1 değil [4.1]. Mevcut P3 örneklerinin maddeleri 7.2'yi de içerecek.
4. Bağlam stratejisi, k=8, 02 filtresi ve 1c'ye dokunulmaz.

### Ölçütler
Geliştirme seti: eski 31 örnek (`GELISTIRME_ONCELIK`) + yeni 10 örnek (`GELISTIRME_ONCELIK_YENI`: geçici çözümlü 6 → 5×P3 + 1×P4; geçici çözümsüz 4 → P2).

| Ölçüt | Eşik |
|---|---|
| Eski öncelik geliştirme seti (31 örnek) | **31/31** korunur |
| Yeni 10 örnekte hata | en fazla **1** |
| Uydurma/geçersiz madde | **0** (modelin ham cevabında bağlam dışı madde yok; P1–P4 verip geçerli madde göstermeyen çağrı yok) |
| Çağrı süresi artışı | ölçülür ve raporlanır (tek başına ret sebebi değil) |

Yöntem: (1) mevcut yapıyla yeni 10 ölçülür (düzeltme öncesi referans), (2) düzeltme, (3) yeni 10 + eski 31 tekrar ölçülür. Ölçüt tutmazsa sıra: (a) istem/few-shot/çekirdek iyileştirme, (b) yalnızca bu adım için daha büyük yerel model (RAM ve gecikme raporlanır), (c) kısmen koda alma. En fazla 2 deneme turu. Bu çalışmada 59 talepli koşu yapılmaz.

### Tur 1 sonucu ve Tur 2 planı (22 Kasım 2026; Tur 2 ölçümünden ÖNCE yazıldı; ölçütler değişmedi)
Tur 1 (çekirdek +2.1/2.2, karar basamakları, +2 few-shot): yeni 10 → 9/10 (düzeltme öncesi de 9/10), **eski 31 → 30/31 (ölçüt 31/31 TUTMADI)**. Gerileme: görünüm hatası bildirimi + geçici çözüm olan bir P3 talebi P4 verildi; kural (b) "geçici çözüm = bir alt seviye" fazla uygulandı. Dokümanda (6.1) P4 yalnızca bilgi isteği/kullanım sorusudur; hata bildirimi en az P3'tür.
Tur 2 değişikliği (yalnızca istem, başka bir şey değişmez): karar basamağı (b)'ye "Sorun/hata bildirimi hiçbir zaman P4 olmaz (en düşük seviye P3); P4 yalnızca bilgi isteği ya da kullanım sorusudur (Madde 6.1)" cümlesi eklenecek.
