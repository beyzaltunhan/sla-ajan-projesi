"""İlk koşu ile düzeltme sonrası koşuyu karşılaştırır (mevcut degerlendirme/rapor.py ölçüm mantığını AYNEN kullanır).
Kullanım: python degerlendirme/karsilastir.py [ilk.jsonl] [sonra.jsonl] [cikti.md]"""
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "degerlendirme"))
import rapor as R  # noqa: E402  (ölçüm mantığı: degerlendir, hata_adimi, kaynak yardımcıları)

KUMELER = R.KUMELER
YORUMA_ACIK = R.YORUMA_ACIK
LLM = R.LLM_ADIMLAR


def kn(a, b):
    return f"{a}/{b}"


def tablo(baslik, satirlar):
    return R.tablo(baslik, satirlar)


class Kosu:
    """Bir koşunun değerlendirilmiş hâli."""

    def __init__(self, yol, ad):
        self.ad = ad
        self.meta, self.kayit, self.test = R.yukle(Path(yol))
        self.ids = sorted(self.kayit, key=lambda i: int(i[1:]))
        self.D = {i: R.degerlendir(self.test[i], self.kayit[i]) for i in self.ids}
        self.H = {i: R.hata_adimi(self.test[i], self.kayit[i], self.D[i]) for i in self.ids}
        self.supheli = self._supheli()

    def kume(self, k):
        return [i for i in self.ids if self.test[i]["set"] == k]

    def kisitla(self, idler):
        """Yalnızca ortak talepler (tam koşuda her ikisi de 59 talep: etkisiz)."""
        self.ids = [i for i in self.ids if i in idler]
        self.supheli = self._supheli()

    def exp_onc(self, i):
        b = self.test[i]["beklenen"]
        if b["davranis"] == "HESAPLA":
            return b["oncelik"]
        return "belirsiz" if (b["davranis"] == "ONCELIK_BELIRLENEMEDI" or b["neden"] == "oncelik_belirsiz") else None

    def got_onc(self, i):
        return (self.kayit[i].get("ara") or {}).get("oncelik") or "ulaşılmadı"

    def cikti(self, i):
        return self.kayit[i].get("cikti") or {}

    def _supheli(self):
        """Kesinti şüpheli: (a) süre aynı davranış medyanının 1.5 katı ve +30 sn üstü; (b) ardışık talepler arası duvar
        saati boşluğu, talebin kendi süresinden 20 sn'den fazla büyük (uyku / yeniden başlatma / duraklama)."""
        grup = defaultdict(list)
        for i in self.ids:
            grup[R.alinan(self.kayit[i])].append(self.kayit[i]["toplam_sn"])
        med = {g: statistics.median(v) for g, v in grup.items()}
        s = {}
        onceki = datetime.fromisoformat(self.meta["tarih"])
        for i in self.ids:
            k = self.kayit[i]
            z = datetime.fromisoformat(k["zaman"])
            neden = []
            m = med[R.alinan(k)]
            if k["toplam_sn"] > 1.5 * m and k["toplam_sn"] > m + 30:
                neden.append(f"süre {k['toplam_sn']:.0f} sn > 1,5× medyan ({m:.0f} sn)")
            bosluk = (z - onceki).total_seconds() - k["toplam_sn"]
            if bosluk > 20:
                neden.append(f"talepler arası {bosluk:.0f} sn boşluk")
            onceki = z
            if neden:
                s[i] = "; ".join(neden)
        return s

    # --- sayımlar
    def tam(self, idl):
        return sum(self.D[i]["tam"] for i in idl)

    def dav(self, idl):
        return sum(self.D[i]["dav"] for i in idl)

    def say(self, idl, f):
        n = [i for i in idl if f(i) is not None]
        return sum(1 for i in n if f(i)), len(n)


def sutun(a, b):
    return [a, b]


def fark(x, y):
    return "=" if x == y else ("▲" if y > x else "▼")


def lat_istat(v, nd=1):
    return ["—"] * 3 if not v else [f"{statistics.mean(v):.{nd}f}", f"{statistics.median(v):.{nd}f}", f"{max(v):.{nd}f}"]


def adimlar(k, i):
    return k.kayit[i].get("adim_sureleri") or []


def rapor(A, B):
    L = []
    ek = L.append
    ids = [i for i in A.ids if i in B.kayit]
    kume = lambda k: [i for i in ids if A.test[i]["set"] == k]  # noqa: E731
    bag = [i for i in ids if A.test[i]["yazar"] == "kullanici"]
    ek("# Düzeltme sonrası koşu: ilk koşuyla karşılaştırmalı rapor\n")
    ek("Yüzde değil \"kaç/N\" kullanılır. Ana set (T01–T50), zor set (T51–T59) ve bağımsız yazılan 15 talep ayrıdır. "
       "İlk koşu `ilk_kosu_ham.jsonl` (DONDURULMUŞ), bu koşu `duzeltme_sonrasi_ham.jsonl`. Bu rapor üretildikten sonra değiştirilmez.\n")
    ek(tablo(["Alan", "İlk koşu", "Düzeltme sonrası koşu"], [
        ["Kodun commit'i (koşu sırasında)", f"`{A.meta['commit'][:12]}` ({'kirli' if A.meta['kirli'] else 'temiz ağaç'})",
         f"`{B.meta['commit'][:12]}` ({'kirli' if B.meta['kirli'] else 'temiz ağaç'})"],
        ["Ana LLM", f"{A.meta['chat_model']} (think: false)", f"{B.meta['chat_model']} (think: false)"],
        ["Embedding", A.meta["embed_model"], B.meta["embed_model"]],
        ["Bağlam stratejisi", A.meta["strateji"], B.meta["strateji"]],
        ["Koşu başlangıcı", A.meta["tarih"], B.meta["tarih"]],
        ["Talep sayısı", len(A.ids), len(B.ids)]]))
    ek("**Aynı koşullar:** kayıt zamanı ve \"şimdi\" test_seti.json'dan; her talep ayrı thread_id; OTOMATİK ONAY YOK; `iki_tur` etiketli "
       "talepler için `soru_soruldu=True`; beklenen müşteri/paket null olan alan hata sayılmaz; kayıtsız firma adı kısaltması kuralı aynı. "
       "Aynı ölçüm kodu (`degerlendirme/rapor.py`) iki koşuya da uygulandı. İkinci koşu, Windows'un uykuya geçmesini engelleyen bir "
       "başlatıcıyla çalıştırıldı (repo dışı; ajan ve koşucu kodu değişmedi).\n")
    ek("**Düzeltmeler (ilk koşudan sonra):** (1) 1c talep türü istemi + few-shot (kullanım sorusu / mevcut hizmetle ilgili arıza ayrımı); "
       "(2) Adım 4 öncelik: çekirdek liste 12→14 madde (02:2.1, 2.2), istemde karar basamakları, few-shot 6→8. "
       "Ölçütler ve geliştirme setleri `tasarim/duzeltme_olcutleri.md` ve `deneme/` içindedir.\n")

    # 1. özet
    ek("## 1. Özet (yan yana)\n")
    satir = []
    for kod, ad in KUMELER:
        idl = kume(kod)
        satir.append([f"Tam doğru — {ad}", kn(A.tam(idl), len(idl)), kn(B.tam(idl), len(idl)), fark(A.tam(idl), B.tam(idl))])
    satir.append(["Tam doğru — bağımsız 15", kn(A.tam(bag), len(bag)), kn(B.tam(bag), len(bag)), fark(A.tam(bag), B.tam(bag))])
    for kod, ad in KUMELER:
        idl = kume(kod)
        satir.append([f"Davranış doğru — {ad}", kn(A.dav(idl), len(idl)), kn(B.dav(idl), len(idl)), fark(A.dav(idl), B.dav(idl))])
    satir.append(["Davranış doğru — bağımsız 15", kn(A.dav(bag), len(bag)), kn(B.dav(bag), len(bag)), fark(A.dav(bag), B.dav(bag))])
    for kod, ad in KUMELER:
        idl = kume(kod)
        n = [i for i in idl if A.exp_onc(i)]
        a, b = sum(A.got_onc(i) == A.exp_onc(i) for i in n), sum(B.got_onc(i) == B.exp_onc(i) for i in n)
        satir.append([f"Öncelik önerisi doğru (belirsiz dahil) — {ad}", kn(a, len(n)), kn(b, len(n)), fark(a, b)])
    ek(tablo(["Ölçü", "İlk koşu", "Düzeltme sonrası", "Değişim"], satir))
    ek("\"Tam doğru\": davranış, neden, müşteri, paket ve (HESAPLA'da) öncelik, son tarih, risk, kredi, onay gerekli ve nedenleri hepsi doğru. "
       "Kaynak maddeleri ayrıdır (§8).\n")

    # 2. davranış matrisleri
    ek("## 2. Davranış sınıfı karışıklık matrisleri\n")
    sut = R.DAVRANISLAR + ["ISLENEMEDI", "ISTISNA"]
    for kod, ad in KUMELER:
        idl = kume(kod)
        for K in (A, B):
            m = defaultdict(Counter)
            for i in idl:
                m[K.test[i]["beklenen"]["davranis"]][K.D[i]["got"]] += 1
            ek(f"**{ad} — {K.ad}** (doğru {kn(K.dav(idl), len(idl))})\n")
            ek(tablo(["beklenen \\ alınan"] + sut + ["toplam"],
                     [[b] + [m[b][s] or "" for s in sut] + [sum(m[b].values())] for b in R.DAVRANISLAR if m[b]]))

    # 3. öncelik
    ek("## 3. Öncelik önerisi (Adım 4): karışıklık matrisleri\n")
    ek("Alınan = LLM'in Adım 4'te önerdiği öncelik (`ara.oncelik`); önceki adımda durulduysa \"ulaşılmadı\". \"belirsiz\" satırı: beklenen "
       "ONCELIK_BELIRLENEMEDI veya SORU_SOR/oncelik_belirsiz.\n")
    sutp = ["P1", "P2", "P3", "P4", "belirsiz", "ulaşılmadı"]
    for kod, ad in KUMELER:
        n = [i for i in kume(kod) if A.exp_onc(i)]
        for K in (A, B):
            m = defaultdict(Counter)
            for i in n:
                m[K.exp_onc(i)][K.got_onc(i)] += 1
            ek(f"**{ad} — {K.ad}** (doğru {kn(sum(K.got_onc(i) == K.exp_onc(i) for i in n), len(n))})\n")
            ek(tablo(["beklenen \\ alınan"] + sutp + ["toplam"],
                     [[b] + [m[b][s] or "" for s in sutp] + [sum(m[b].values())] for b in ["P1", "P2", "P3", "P4", "belirsiz"] if m[b]]))
    ek("**Etiket kırılımı (öncelik; ana+zor birlikte, bir talep birden çok etiket taşıyabilir)**\n")
    et = defaultdict(lambda: [0, 0, 0])
    for i in A.ids:
        if not A.exp_onc(i):
            continue
        for e in A.test[i]["etiket"]:
            et[e][0] += 1
            et[e][1] += A.got_onc(i) == A.exp_onc(i)
            et[e][2] += B.got_onc(i) == B.exp_onc(i)
    ek(tablo(["etiket", "toplam", "ilk koşu doğru", "düzeltme sonrası doğru"],
             [[e, v[0], kn(v[1], v[0]), kn(v[2], v[0])] for e, v in sorted(et.items(), key=lambda x: (-x[1][0], x[0])) if v[1] != v[2] or v[0] - v[2] > 0]))
    ek("(Yalnızca bir koşuda yanlışı olan etiketler gösterilir.)\n")

    # 4. alan doğrulukları
    ek("## 4. Müşteri/paket, son tarih, risk, kredi, onay\n")
    satir = []
    for kod, ad in KUMELER:
        idl = kume(kod)
        mu = [i for i in idl if A.test[i]["beklenen"].get("musteri")]
        pk = [i for i in idl if A.test[i]["beklenen"].get("paket")]
        hs = [i for i in idl if A.test[i]["beklenen"]["davranis"] == "HESAPLA"]
        olmali = [i for i in hs if A.test[i]["beklenen"]["onay_gerekli"]]
        olmamali = [i for i in hs if not A.test[i]["beklenen"]["onay_gerekli"]]
        for etiket, f in [
            ("Müşteri doğru", lambda K: K.say(mu, lambda i: K.D[i]["musteri"])),
            ("Paket doğru", lambda K: K.say(pk, lambda i: K.D[i]["paket"])),
            ("Son tarih doğru (beklenen HESAPLA)", lambda K: K.say(hs, lambda i: K.D[i]["son_tarih"])),
            ("Risk doğru (beklenen HESAPLA)", lambda K: K.say(hs, lambda i: K.D[i]["risk"])),
            ("Kredi doğru (beklenen HESAPLA)", lambda K: K.say(hs, lambda i: K.D[i]["kredi"])),
            ("Onay gerekli doğru (beklenen HESAPLA)", lambda K: K.say(hs, lambda i: K.D[i]["onay"])),
            ("Onay nedenleri doğru (beklenen HESAPLA)", lambda K: K.say(hs, lambda i: K.D[i]["onay_neden"])),
            ("Onay yakalama (geri çağırma: onay gerekende onay istendi)", lambda K: (sum(1 for i in olmali if K.cikti(i).get("onay_gerekli")), len(olmali))),
            ("Yanlış alarm (onay gerekmezken onay istendi)", lambda K: (sum(1 for i in olmamali if K.cikti(i).get("onay_gerekli")), len(olmamali))),
        ]:
            x, y = f(A), f(B)
            satir.append([ad, etiket, kn(*x), kn(*y), fark(x[0], y[0])])
    ek(tablo(["Küme", "Ölçü", "İlk koşu", "Düzeltme sonrası", "Değişim"], satir))
    ek("Not: son tarih/risk/kredi/onay kod adımlarıdır; yanlış çıkmaları yukarı akıştan (müşteri, öncelik, yönlendirme) gelir.\n")

    # 5. bilmiyorum
    ek("## 5. \"Bilmiyorum\" doğruluğu ve fazladan BILMIYORUM\n")
    satir = []
    for kod, ad in KUMELER:
        idl = kume(kod)
        bek = [i for i in idl if A.test[i]["beklenen"]["davranis"] == "BILMIYORUM"]
        for K in (A, B):
            yak = [i for i in bek if K.D[i]["got"] == "BILMIYORUM"]
            fazla = [i for i in idl if K.D[i]["got"] == "BILMIYORUM" and K.test[i]["beklenen"]["davranis"] != "BILMIYORUM"]
            satir.append([ad, K.ad, kn(len(yak), len(bek)), kn(sum(1 for i in yak if K.D[i]["neden"]), len(yak)), ", ".join(fazla) or "—"])
    ek(tablo(["Küme", "Koşu", "Beklenen BILMIYORUM yakalandı", "Yakalananlarda neden kodu doğru", "Fazladan (yanlış) BILMIYORUM"], satir))

    # 6. talimat
    ek("## 6. Talimat tespiti (1b), iki yön\n")
    satir = []
    for kod, ad in KUMELER:
        idl = kume(kod)
        eng = [i for i in idl if A.test[i]["beklenen"]["davranis"] == "ENGELLE"]
        mas = [i for i in idl if A.test[i]["beklenen"]["davranis"] != "ENGELLE"]
        for K in (A, B):
            kac = [i for i in eng if K.D[i]["got"] != "ENGELLE"]
            yanl = [i for i in mas if K.D[i]["got"] == "ENGELLE"]
            satir.append([ad, K.ad, kn(len(kac), len(eng)), ", ".join(kac) or "—", kn(len(yanl), len(mas)), ", ".join(yanl) or "—"])
    ek(tablo(["Küme", "Koşu", "Komutu kaçırma", "Talepler", "Masum talebi engelleme", "Talepler"], satir))

    # 7. 1c ve hata türleri
    ek("## 7. Hata türleri (hata hangi adımda oluştu)\n")
    ek("Her hatalı talep ilk sapma adımına atanır (Bölüm 3-6 sırası). Kaynak maddesi eksikliği talep hatası sayılmaz.\n")

    def etiket_adim(K, i):
        a = K.H[i]
        if not a:
            return None
        if a[0] == "1b":
            return "1b " + ("(komutu kaçırma)" if a[1].startswith("komutu") else "(yanlış engelleme)")
        return a[0]
    adm = sorted({etiket_adim(K, i) for K in (A, B) for i in ids if K.H[i]})
    satir = []
    for kod, ad in KUMELER:
        idl = kume(kod)
        for a in adm:
            x, y = sum(etiket_adim(A, i) == a for i in idl), sum(etiket_adim(B, i) == a for i in idl)
            if x or y:
                satir.append([ad, a, x, y, fark(x, y)])
        satir.append([ad, "**Toplam hatalı talep**", kn(sum(1 for i in idl if A.H[i]), len(idl)), kn(sum(1 for i in idl if B.H[i]), len(idl)),
                      fark(sum(1 for i in idl if A.H[i]), sum(1 for i in idl if B.H[i]))])
    ek(tablo(["Küme", "Hata adımı", "İlk koşu", "Düzeltme sonrası", "Değişim"], satir))

    # 8. kaynak
    ek("## 8. Doğru kaynak maddeyi bulma (beklenen_kaynak ile)\n")
    ek("02 grubu = Adım 4'te modelin kullandığı maddeler (kodla süzülmüş); 01/03/04 grubu = hesap araçlarının kod atfı. BILMIYORUM/SORU_SOR/ENGELLE "
       "şema gereği kaynak taşımaz; bunlarla sonuçlanan talepler yapısal olarak \"bulunamadı\" sayılır.\n")
    satir = []
    for kod, ad in KUMELER:
        idl = [i for i in kume(kod) if A.test[i]["beklenen_kaynak"]]
        for ad2, filtre in (("02 maddeleri (öncelik kuralı)", lambda x: x[0] == "02"), ("01/03/04 maddeleri", lambda x: x[0] != "02")):
            hedef = [(i, {x for x in R.beklenen_kaynak(A.test[i]) if filtre(x)}) for i in idl]
            hedef = [(i, b) for i, b in hedef if b]
            r = []
            for K in (A, B):
                tum = sum(1 for i, b in hedef if b <= R.alinan_kaynak(K.kayit[i]))
                biri = sum(1 for i, b in hedef if b & R.alinan_kaynak(K.kayit[i]))
                mad = sum(len(b & R.alinan_kaynak(K.kayit[i])) for i, b in hedef)
                r.append((tum, biri, mad))
            top = sum(len(b) for _, b in hedef)
            satir.append([ad, ad2, len(hedef), f"{kn(r[0][0], len(hedef))} / {kn(r[0][1], len(hedef))} / {kn(r[0][2], top)}",
                          f"{kn(r[1][0], len(hedef))} / {kn(r[1][1], len(hedef))} / {kn(r[1][2], top)}"])
    ek(tablo(["Küme", "Madde grubu", "Talep", "İlk koşu: tümü / en az biri / madde", "Düzeltme sonrası: tümü / en az biri / madde"], satir))

    # 9. gecikme
    ek("## 9. Gecikme\n")
    ek("Süreler `adim_sureleri`'nden (LLM adımları ve kod adımları ayrı); insan onay bekleme süresi dahil değildir. Her ikisinde de Ollama CPU'da çalıştı. "
       "**Kesinti şüpheli** talepler (uyku/yeniden başlatma/duraklama olasılığı): süresi aynı davranış medyanının 1,5 katından ve +30 sn'den büyük, "
       "ya da ardışık talepler arasında talebin kendi süresinden 20 sn'den fazla boşluk olan talepler. Ortalamalar hem dahil hem hariç verilir.\n")
    for K in (A, B):
        ek(f"{K.ad}: şüpheli talep {len(K.supheli)} → " + ("; ".join(f"{i} ({n})" for i, n in K.supheli.items()) if K.supheli else "yok") + "\n")
    satir = []
    for etiket, f in [("Toplam (duvar saati)", lambda K, i: K.kayit[i]["toplam_sn"]),
                      ("LLM adımları toplamı", lambda K, i: sum(x["sure_sn"] for x in adimlar(K, i) if x["tur"] == "llm")),
                      ("Kod adımları toplamı", lambda K, i: sum(x["sure_sn"] for x in adimlar(K, i) if x["tur"] == "kod"))]:
        nd = 4 if etiket.startswith("Kod") else 1
        for dahil in (True, False):
            satir.append([etiket, "dahil" if dahil else "şüpheliler hariç"] +
                         lat_istat([f(A, i) for i in A.ids if dahil or i not in A.supheli], nd) +
                         lat_istat([f(B, i) for i in B.ids if dahil or i not in B.supheli], nd))
    ek(tablo(["Talep başına (sn)", "Küme", "İlk: ort", "medyan", "maks", "Sonra: ort", "medyan", "maks"], satir))
    ek("**Adım bazında (sn)**\n")
    satir = []
    adim_s = {K.ad: defaultdict(list) for K in (A, B)}
    for K in (A, B):
        for i in K.ids:
            for x in adimlar(K, i):
                adim_s[K.ad][(x["tur"], x["adim"])].append(x["sure_sn"])
    for (t, a) in sorted(set(adim_s[A.ad]) | set(adim_s[B.ad]), key=lambda x: (x[0] != "llm", x[1])):
        nd = 1 if t == "llm" else 4
        satir.append([a, t, len(adim_s[A.ad][(t, a)]), *lat_istat(adim_s[A.ad][(t, a)], nd), len(adim_s[B.ad][(t, a)]), *lat_istat(adim_s[B.ad][(t, a)], nd)])
    ek(tablo(["Adım", "tür", "İlk: n", "ort", "medyan", "maks", "Sonra: n", "ort", "medyan", "maks"], satir))
    ek("**Alınan davranışa göre toplam süre (sn)**\n")
    satir = []
    for d in sorted({K.D[i]["got"] for K in (A, B) for i in K.ids}):
        va = [A.kayit[i]["toplam_sn"] for i in A.ids if A.D[i]["got"] == d]
        vb = [B.kayit[i]["toplam_sn"] for i in B.ids if B.D[i]["got"] == d]
        satir.append([d, len(va), *lat_istat(va), len(vb), *lat_istat(vb)])
    ek(tablo(["Alınan davranış", "İlk: n", "ort", "medyan", "maks", "Sonra: n", "ort", "medyan", "maks"], satir))
    ta, tb = sum(A.kayit[i]["toplam_sn"] for i in A.ids) / 60, sum(B.kayit[i]["toplam_sn"] for i in B.ids) / 60
    ek(f"Toplam duvar süresi: ilk koşu {ta:.1f} dk, düzeltme sonrası {tb:.1f} dk.\n")

    # 10. talep bazında
    ek("## 10. Talep bazında: düzeldi / bozuldu / değişmedi\n")
    ek("Tanım: \"doğru\" = tam doğru (hata yok). Düzeldi = ilk koşuda hatalı, şimdi doğru. Bozuldu = ilk koşuda doğru, şimdi hatalı (REGRESYON). "
       "Değişmedi: iki koşuda da doğru ya da iki koşuda da hatalı.\n")
    grup = defaultdict(list)
    for i in ids:
        a, b = bool(A.H[i]), bool(B.H[i])
        grup["düzeldi" if a and not b else "bozuldu" if b and not a else "değişmedi (doğru)" if not a else "değişmedi (hâlâ hatalı)"].append(i)
    ek(tablo(["Durum", "Ana set", "Zor set", "Talepler"],
             [[g, sum(1 for i in v if A.test[i]["set"] == "ana"), sum(1 for i in v if A.test[i]["set"] == "zor"),
               ", ".join(v) if g != "değişmedi (doğru)" else f"{len(v)} talep"] for g, v in
              [(g, grup[g]) for g in ("düzeldi", "bozuldu", "değişmedi (hâlâ hatalı)", "değişmedi (doğru)")]]))

    def ozet(K, i):
        c = K.cikti(i)
        b = K.test[i]["beklenen"]
        return f"{K.D[i]['got']}" + (f"/{c['neden']}" if c.get("neden") else "") + (
            f" {c.get('oncelik')} {c.get('risk')} onay={c.get('onay_gerekli')}" if c.get("davranis") == "HESAPLA" else "")

    def beklenen(K, i):
        b = K.test[i]["beklenen"]
        return f"{b['davranis']}" + (f"/{b['neden']}" if b["neden"] else "") + (
            f" {b['oncelik']} {b['risk']} onay={b['onay_gerekli']}" if b["davranis"] == "HESAPLA" else "")

    def neden_ipucu(i):
        ara = B.kayit[i].get("ara") or {}
        h = B.H[i]
        s = f"adım {h[0]}: {h[1]}"
        if ara.get("etki") and h[0].startswith("4"):
            s += f"; model etkisi: {ara['etki']}; maddeler {ara.get('oncelik_maddeleri')}"
        return s[:260]
    ek("### 10.1 Düzelenler\n")
    ek(tablo(["Talep", "Beklenen", "İlk koşuda alınan (adım)", "Şimdi alınan", "Etiketler"],
             [[i, beklenen(A, i), f"{ozet(A, i)} ({A.H[i][0]})", ozet(B, i), ", ".join(A.test[i]["etiket"])] for i in grup["düzeldi"]]) if grup["düzeldi"] else "Yok.\n")
    ek("### 10.2 YENİ BOZULANLAR (regresyon)\n")
    if grup["bozuldu"]:
        ek(tablo(["Talep", "Beklenen", "İlk koşuda alınan", "Şimdi alınan", "Hatanın adımı ve olası neden", "Etiketler"],
                 [[i, beklenen(A, i), ozet(A, i), ozet(B, i), neden_ipucu(i), ", ".join(A.test[i]["etiket"])] for i in grup["bozuldu"]]))
    else:
        ek("**Yok.** İlk koşuda doğru olan hiçbir talep şimdi hatalı değil.\n")
    ek("### 10.3 Düzeltilmeyen hatalar (iki koşuda da hatalı)\n")
    if grup["değişmedi (hâlâ hatalı)"]:
        ek(tablo(["Talep", "Beklenen", "İlk koşuda alınan", "Şimdi alınan", "Hatanın adımı", "Yoruma açık etiket?"],
                 [[i, beklenen(A, i), ozet(A, i), ozet(B, i), f"{A.H[i][0]} → {B.H[i][0]}",
                   ("EVET: " + YORUMA_ACIK[i]) if i in YORUMA_ACIK else ""] for i in grup["değişmedi (hâlâ hatalı)"]]))
    else:
        ek("Yok.\n")
    ek("### 10.4 Yoruma açık etiketli talepler (VERI_KARTI §5: T53, T55, T58)\n")
    ek(tablo(["Talep", "Beklenen", "İlk koşu", "Düzeltme sonrası", "Not"],
             [[i, beklenen(A, i), ("doğru" if not A.H[i] else f"HATALI: {ozet(A, i)}"), ("doğru" if not B.H[i] else f"HATALI: {ozet(B, i)}"),
               YORUMA_ACIK[i]] for i in ("T53", "T55", "T58") if i in ids]))
    ek("### 10.5 Hatası olan tüm talepler (düzeltme sonrası koşu)\n")
    satir = [[i, A.test[i]["set"], beklenen(B, i), ozet(B, i), neden_ipucu(i), ", ".join(B.test[i]["etiket"]), B.test[i]["yazar"]] for i in ids if B.H[i]]
    ek(tablo(["Talep", "Küme", "Beklenen", "Alınan", "Hata adımı ve ayrıntı", "Etiketler", "Yazar"], satir) if satir else "Yok.\n")

    # 11. bağımsız 15
    ek("## 11. Bağımsız yazılan 15 talep ayrıca\n")
    satir = []
    for kod, ad in KUMELER:
        idl = [i for i in bag if A.test[i]["set"] == kod]
        satir.append([ad, len(idl), kn(A.tam(idl), len(idl)), kn(B.tam(idl), len(idl)),
                      ", ".join(f"{i}({A.H[i][0]})" for i in idl if A.H[i]) or "—", ", ".join(f"{i}({B.H[i][0]})" for i in idl if B.H[i]) or "—"])
    ek(tablo(["Küme", "Talep", "İlk koşu tam doğru", "Sonra tam doğru", "İlk koşu hatalıları", "Sonra hatalıları"], satir))
    ek("Not: 44 talep dokümanları yazan tarafça yazıldığından ana set skoru olduğundan yüksek görünebilir; ayrıca düzeltmeler ilk koşudaki hatalara "
       "bakılarak yapıldığı için \"düzeltme sonrası\" skor ilk koşuya göre iyimser bir kıyastır (test seti artık tamamen bağımsız değildir).\n")
    return "\n".join(L)


if __name__ == "__main__":
    a = Path(sys.argv[1]) if len(sys.argv) > 1 else KOK / "sonuclar" / "ilk_kosu_ham.jsonl"
    b = Path(sys.argv[2]) if len(sys.argv) > 2 else KOK / "sonuclar" / "duzeltme_sonrasi_ham.jsonl"
    c = Path(sys.argv[3]) if len(sys.argv) > 3 else KOK / "sonuclar" / "duzeltme_sonrasi_rapor.md"
    A, B = Kosu(a, "İlk koşu"), Kosu(b, "Düzeltme sonrası")
    ortak = set(A.ids) & set(B.ids)
    A.kisitla(ortak)
    B.kisitla(ortak)
    c.write_text(rapor(A, B), encoding="utf-8")
    print(f"{len(A.ids)} / {len(B.ids)} talep -> {c}")
