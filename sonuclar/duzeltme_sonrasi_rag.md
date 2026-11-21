# RAG düzeltme sonrası

Ayar: `dokuman="02_oncelik_rehberi"` filtresi + k=8 (geliştirme setinde seçildi; sonra test setinde BİR KEZ ölçüldü, sonrasında ayar yapılmadı).
Ölçüt: yalnızca beklenen_kaynak içindeki Doküman 02 maddeleri; sorgu = ham talep_metni. Hesap/onay (01, 03) ve 04 maddeleri RAG ile ölçülmez.
İlk ölçümle (`ilk_olcum_rag.md`) doğrudan karşılaştırılamaz: ölçüt farklı (yalnızca 02) ve ayar farklı. Referans: ilk ölçümde 02 maddeleri k=5 filtresiz 4/62.

| Küme | 02 beklenen talep | tümü | en az biri | madde |
|---|---|---|---|---|
| Ana set (T01–T50) | 36 | 11/36 | 15/36 | 15/44 |
| Zor set (T51–T59) | 7 | 1/7 | 5/7 | 6/18 |

## Kaçırılanlar (ana set, talep: eksik 02 maddeleri)

- T01: 5.1, 7.2
- T02: 6.1
- T03: 4.1
- T05: 5.1
- T07: 4.1
- T08: 6.1
- T09: 5.1, 7.2
- T10: 3.1
- T12: 4.1
- T13: 5.1, 7.2
- T14: 4.1
- T15: 5.1, 7.2
- T25: 8.3
- T27: 5.1
- T28: 6.1
- T29: 6.1
- T31: 6.1
- T32: 6.1
- T35: 6.1
- T36: 5.1
- T37: 6.1
- T38: 5.1
- T39: 4.1
- T40: 4.1
- T41: 5.1

## Kaçırılanlar (zor set, talep: eksik 02 maddeleri)

- T51: 10.1, 5.1
- T52: 6.1
- T53: 2.3, 5.1, 7.2
- T55: 2.3, 4.1
- T58: 5.1, 7.3
- T59: 4.1, 7.3
