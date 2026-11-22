# SLA Uyum ve Eskalasyon Ajanı (prototip)

Kurgusal firma Poyraz Bulut Yazılım A.Ş. için, sentetik veriyle çalışan SLA uyum ve eskalasyon ajanı prototipi.
(README'nin tamamı teslim aşamasında yazılacaktır; aşağıda yalnızca arayüz ve demo hazırlığı yer alır.)

## Arayüzü çalıştırma

```
pip install -r requirements.txt
streamlit run arayuz/uygulama.py
```

- **Ollama açık olmalı** ve modeller yüklü olmalı (`qwen3.5:4b`, `embeddinggemma`). Uygulama açılışta modelleri ısıtır;
  yan çubuktaki "Modeli ısıt" düğmesiyle tekrarlanabilir.
- Arayüz ajanı olduğu gibi kullanır (`ajan.talep_isle` / `ajan.onay_ver`). Bekleyen onaylar `checkpoints.sqlite` içinde
  tutulur; uygulama yeniden başlasa da listelenir.
- Sekmeler: **Talep İşle**, **Ölçüm Sonuçları**, **Mimari ve Sınırlamalar**, **Kayıtlı Çalıştırmalar**
  (önceden çalıştırılmış, canlı olmayan kayıtlar; `demo/kayitli_sonuclar.json`).
- Kayıtlı sonuçları yenilemek için: `python demo/kayit_al.py`.

## Demo hazırlık listesi

1. Bilgisayarı **prize takın**; Windows güç planını **En iyi performans** yapın (model CPU'da çalışır, pil modunda belirgin yavaşlar).
2. **Diğer uygulamaları kapatın** (tarayıcı sekmeleri, müzik, sohbet uygulamaları): CPU yükü gecikmeyi doğrudan artırır.
3. **Ollama'yı başlatın** (`ollama ps` / `ollama list` ile kontrol edin).
4. Ön kontrolü çalıştırın: `python demo/on_kontrol.py` — Ollama, modeller, ısınma ve Demo 1 / Demo 2 uçtan uca
   (3 tekrar, tutarlılık ve süreler). Tüm örnekler için: `python demo/on_kontrol.py --tumu`.
5. Deneme kayıtlarını temizleyin: `python demo/sifirla.py` — önce yedek alır, onay ister, sonra temiz kayıtla başlatır
   (yalnızca git'e girmeyen yerel `checkpoints.sqlite*` dosyalarına dokunur; yedek `demo/yedek/` altına gider).
6. Uygulamayı başlatın, yan çubukta "Model durumu: hazır" yazısını bekleyin, bir kez Demo 1'i deneyin.
7. Yedek plan: model/ağ sorunu olursa **Kayıtlı Çalıştırmalar** sekmesi (canlı değil, etiketli) gösterilebilir.

Süre beklentisi (ısınmış model, CPU): komutlu talep ~12 sn; hesaplı talep ~60–100 sn.
