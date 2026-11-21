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
