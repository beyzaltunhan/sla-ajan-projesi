# Poyraz Bulut Yazılım A.Ş. – Destek Hizmeti SLA Dokümanı

> KURGUSAL DOKÜMAN: Poyraz Bulut Yazılım A.Ş. eğitim amacıyla uydurulmuş bir firmadır. Bu dokümandaki süreler, oranlar ve kurallar gerçek bir sözleşme değildir.

Doküman No: 01 – SLA Sözleşmesi | Sürüm: 1.0 | Yürürlük: 1 Ekim 2026

## Madde 1 – Amaç, Taraflar ve Paketler

1.1 Bu doküman, Poyraz Bulut Yazılım A.Ş. ("Poyraz") ile kurumsal müşterileri ("Müşteri") arasında, destek taleplerine verilecek **ilk yanıt süresini** düzenler. Çözüm süresi ve hizmetin çalışma süresi (uptime) bu dokümanın konusu değildir.

1.2 Poyraz üç destek paketi sunar: **Standart**, **Gelişmiş** ve **Kurumsal**. Müşterinin hangi pakete sahip olduğu müşteri kaydında yazılıdır.

1.3 Destek talepleri destek portalı veya e-posta ile iletilir.

## Madde 2 – Öncelik Seviyeleri

2.1 Her destek talebine, etkisine göre aşağıdaki dört seviyeden biri atanır:

| Seviye | Ad | Tanım |
|---|---|---|
| P1 | Kritik | Hizmet tamamen kullanılamıyor veya Müşteri'nin üretim ortamı durmuş durumda; veri kaybı ya da güvenlik riski var ve geçici çözüm yok. |
| P2 | Yüksek | Önemli bir işlev çalışmıyor ya da ciddi şekilde yavaş; hizmet kısmen kullanılabiliyor ve geçici çözüm yok veya çok zor. |
| P3 | Normal | Sınırlı bir işlevde hata var; geçici çözüm mevcut; az sayıda kullanıcı etkileniyor. |
| P4 | Düşük | Bilgi talebi veya kullanım sorusu; hizmette aksama yok. |

2.2 Öncelik seviyesi, talebi alan destek uzmanı tarafından Öncelik Belirleme Rehberi'ne (Doküman 02) göre atanır.

## Madde 3 – İlk Yanıt Süreleri

3.1 İlk yanıt süresi, paket ve öncelik seviyesine göre aşağıdaki gibidir:

| Paket | P1 Kritik | P2 Yüksek | P3 Normal | P4 Düşük |
|---|---|---|---|---|
| Standart | 4 saat | 8 saat | 16 saat | 24 saat |
| Gelişmiş | 2 saat | 4 saat | 8 saat | 16 saat |
| Kurumsal | 1 saat* | 2 saat | 4 saat | 8 saat |

3.2 \* Yalnızca **Kurumsal paketin P1 talepleri** 7/24 takvim saatiyle ölçülür: sayaç talebin kaydedildiği anda başlar ve hafta sonu ile tatil günleri dahil kesintisiz işler.

3.3 Tablodaki diğer tüm süreler **mesai saati** ile ölçülür (Madde 4 ve Madde 5).

## Madde 4 – Mesai Saatleri ve Tatil Günleri

4.1 Mesai saatleri Türkiye saatiyle Pazartesi–Cuma günleri 09:00–18:00 arasıdır. Mesai içinde ara verilmez, süre kesintisiz işler.

4.2 Cumartesi, Pazar ve 4.3'te sayılan tatil günleri mesai dışıdır.

4.3 Poyraz destek ekibi şu günlerde çalışmaz: 29 Ekim 2026, 1 Ocak 2027, 23 Nisan 2027 ve 1 Mayıs 2027. Bu listede yer almayan günler mesai günü sayılır; arife günlerinde de tam gün çalışılır.

## Madde 5 – Süre Sayacının İşleyişi

5.1 Sayaç, talebin destek sistemine kaydedildiği anda başlar. Kayıt zamanı destek sistemi tarafından atanır.

5.2 Mesai saati ile ölçülen bir talep mesai dışında kaydedilmişse sayaç, bir sonraki mesai başlangıcında başlar. Örnek: Gelişmiş paketten bir P2 talebi Cuma 22:00'de kaydedilirse sayaç Pazartesi 09:00'da başlar ve 4 saatlik süre Pazartesi 13:00'te dolar (Pazartesi tatil değilse).

5.3 Süre yalnızca mesai saatlerinde işler. Mesai bittiğinde sayaç durur, bir sonraki mesai gününün başında kaldığı yerden devam eder.

5.4 İlk yanıt, destek uzmanının Müşteri'ye gönderdiği ilk anlamlı cevaptır. "Talebiniz alındı" gibi otomatik e-postalar ilk yanıt sayılmaz.

5.5 İlk yanıt, sürenin bittiği anda veya öncesinde verilmişse süre aşılmış sayılmaz.

## Madde 6 – İhlal Riski, İhlal ve Üst Seviyeye Çıkarma

6.1 Kalan süre, ilgili talep için tanımlı toplam sürenin %25'inin altına düştüğünde talep **yüksek ihlal riski** taşır. Kalan süre tam %25 ise henüz yüksek risk oluşmaz.

6.2 İlk yanıt süresi aşıldığında **ihlal** gerçekleşmiş sayılır ve destek yöneticisine bildirilir.

6.3 P1 talepler, yüksek ihlal riski taşıyan talepler ve ihlal gerçekleşmiş talepler üst seviyeye çıkarılabilir. Üst seviyeye çıkarma kararı **destek yöneticisinin onayıyla** uygulanır. Süreç ayrıntıları Eskalasyon ve Onay Prosedürü'nde (Doküman 03) yer alır.

6.4 Bir talebin risk durumu üç seviyeden biridir: **NORMAL** (yüksek risk veya ihlal yok), **YUKSEK** (yüksek ihlal riski, Madde 6.1) ve **IHLAL** (ilk yanıt süresi aşılmış, Madde 6.2). Bu etiketler Eskalasyon ve Onay Prosedürü'nde de aynen kullanılır.

## Madde 7 – Hizmet Kredisi

7.1 Hizmet kredisi yalnızca **ilk yanıt süresinin aşılması** (ihlal) durumunda ve yalnızca **Gelişmiş ve Kurumsal** paketlerin **P1 ve P2** talepleri için söz konusudur.

7.2 Standart pakette hizmet kredisi yoktur. Tüm paketlerde P3 ve P4 taleplerinin ihlali için de hizmet kredisi yoktur.

7.3 Kredi, Müşteri'nin KDV hariç aylık destek paketi bedelinin yüzdesi olarak hesaplanır:

| Paket | P1 ihlali | P2 ihlali | Aylık toplam kredi tavanı |
|---|---|---|---|
| Gelişmiş | %3 | %1 | %10 |
| Kurumsal | %5 | %2 | %20 |

7.4 Bir takvim ayında uygulanan toplam kredi, ilgili tavanı aşamaz. Ay içinde tavana ulaşılmışsa yeni ihlaller için ek kredi verilmez; tavana kalan pay yeni ihlalin oranından azsa yalnızca kalan pay kadar kredi uygulanır.

7.5 Hizmet kredisi **destek yöneticisinin onayıyla** bir sonraki aylık faturadan düşülür. Nakit iade yapılmaz.

## Madde 8 – Kapsam Dışı Durumlar

8.1 Aşağıdaki konular bu dokümanın kapsamı dışındadır:

- Çözüm süresi, hizmetin çalışma süresi (uptime) ve performans taahhütleri
- Özel entegrasyon geliştirme, ek özellik veya iyileştirme talepleri, danışmanlık hizmetleri
- Eğitim ve oryantasyon talepleri
- Sözleşmesinde bu dokümandan farklı özel hükümler bulunan müşteriler
- Bu dokümanda tanımlanmamış her türlü hizmet veya durum

8.2 Kapsam dışı durumlar için bu dokümanda süre, öncelik veya kredi kuralı bulunmamaktadır. Bu nedenle bu konularda süre hesaplanmaz, öncelik atanmaz, kredi önerilmez ve kural varsayılmaz. Talebin nasıl ele alınacağına destek yöneticisi karar verir.
