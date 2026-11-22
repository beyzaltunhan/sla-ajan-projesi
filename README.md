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

## MCP sunucusu

`mcp_sunucusu.py`, SLA hesap araçlarını MCP (Model Context Protocol) üzerinden dışarı açar; böylece bir MCP istemcisi
(ör. Claude Desktop) müşteri arama ve SLA hesaplarını doğrudan çağırabilir. Ollama gerekmez, model çağrısı yapılmaz.

```
python mcp_sunucusu.py        # stdio üzerinden çalışır
```

| Araç | Ne yapar |
|---|---|
| `musteri_ara` | Firma adını kayıtlı müşterilerde arar (TEK / BELIRSIZ / YOK / BOS) |
| `son_tarih_hesapla` | Talep zamanı + paket + öncelikten ilk yanıt son tarihini hesaplar (mesai, tatil, 7/24) |
| `risk_degerlendir` | NORMAL / YUKSEK / IHLAL riskini ve kalan süreyi verir |
| `kredi_hesapla` | Hizmet kredisi önerisini (yüzde, tutar, neden) hesaplar; uygulamaz |

Neden yalnızca bunlar: ajanın LLM adımları (komut tespiti, talep türü, öncelik önerisi) küçük bir yerel modele ve istemlere
bağlıdır; dışarı açılırsa her çağrı yavaş ve belirsiz olur. Deterministik hesaplar ise aynı girdide hep aynı sonucu verir
ve güvenle paylaşılabilir. Araçlar `sla_araclari.py` fonksiyonlarını sarmalar, mantık kopyalanmaz.

Claude Desktop yapılandırma örneği (`claude_desktop_config.json`; yolları kendi kurulumunuza göre değiştirin):

```json
{
  "mcpServers": {
    "sla-hesap-araclari": {
      "command": "python",
      "args": ["C:/projeler/sla-ajan-projesi/proje/mcp_sunucusu.py"]
    }
  }
}
```

Not: Bu yapılandırma gerçek bir MCP istemcisiyle (Claude Desktop) denenmedi; sunucu yalnızca testlerde bir MCP istemci
oturumuyla ve ayrı süreç olarak stdio üzerinden doğrulandı.

## Ajan servisi

`servis.py`, ajanı HTTP üzerinden çağrılabilir yapar (n8n gibi dış otomasyonlar için); ajan kodu değişmez.
Model CPU'da bir talebi 15–95 sn'de işlediği için `POST /talep` **asenkrondur**: hemen 202 ve bir `talep_id` döner, sonuç
`GET /durum/{talep_id}` ile okunur. Model tek olduğundan talepler **sırayla** (aynı anda tek talep) işlenir.

```
python servis.py                          # 127.0.0.1:8000
python servis.py --host 0.0.0.0 --port 8000   # Docker'daki n8n'in erişebilmesi için
uvicorn servis:app                        # alternatif
```

| Uç nokta | Ne yapar |
|---|---|
| `POST /talep` | `{talep_metni, kayit_zamani?, simdi?, soru_soruldu?}` → 202 `{talep_id, durum:"ISLENIYOR"}` |
| `GET /durum/{talep_id}` | `ISLENIYOR` / `ONAY_BEKLIYOR` / `TAMAMLANDI` / `ISLENEMEDI`; bitince `KararCiktisi`, süre, adım süreleri |
| `POST /onay/{talep_id}` | `{karar:"onayla"\|"reddet", gerekce}`; reddette gerekçe zorunlu (422); yalnızca `ONAY_BEKLIYOR`'da (aksi 409) |
| `GET /bekleyen` | Onay bekleyen talepler |
| `GET /saglik` | Servis ve Ollama durumu |

Zamanlar ISO 8601 ve saat dilimsizdir (örn. `2026-11-19T10:00:00`); verilmezse kayıt zamanı = şimdi = sistem saati.
Etkileşimli dokümantasyon: `http://127.0.0.1:8000/docs`.

Örnek komutlar (PowerShell):

```powershell
$g = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/talep -ContentType "application/json" `
  -Body '{"talep_metni":"Marmara Perakende: Sipariş onay ekranı iki gündür çalışmıyor, başka yoldan işlem yapamıyoruz.","kayit_zamani":"2026-11-19T10:00:00","simdi":"2026-11-22T12:00:00"}'
Invoke-RestMethod http://127.0.0.1:8000/durum/$($g.talep_id)        # ISLENIYOR -> ONAY_BEKLIYOR
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/onay/$($g.talep_id) -ContentType "application/json" `
  -Body '{"karar":"reddet","gerekce":"Kredi oranı sözleşmeyle çelişiyor."}'
```

```
curl.exe -X POST http://127.0.0.1:8000/talep -H "Content-Type: application/json" -d "{\"talep_metni\":\"...\"}"
```

**Güvenlik notu:** Kimlik doğrulama yoktur; prototiptir. `--host 0.0.0.0` yalnızca güvenilir yerel ağda kullanılmalı,
internete açılmamalıdır.

**Streamlit ile birlikte çalıştırma:** Servis kendi checkpoint dosyasını (`servis_checkpoints.sqlite`, git dışı) kullanır;
Streamlit arayüzü `checkpoints.sqlite` kullanır. Dosyalar ayrı olduğu için ikisi birlikte çalışabilir, ancak model (Ollama)
tek ve CPU'da olduğundan aynı anda iki taraftan talep göndermek her ikisini de yavaşlatır; demoda birini kullanın. Servis
yeniden başlarsa bekleyen onaylar `servis_checkpoints.sqlite`'dan okunur (talep_id aynı kalır).
