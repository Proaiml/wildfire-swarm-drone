# Yangın ve artçı yangın arama karşılaştırması

## Güncel sonuç (26 Eylül 2026): hibrit arama, iki senaryo, ayarda kullanılmamış tohumlar

**Kurulum.** 800 × 800 m alan, 4 drone (85 m, 10 m/s), 600 s. Her senaryoda 4 gizli yangın: 2'si başta, artçılar 180. ve 360. saniyede tutuşur. Sensör geometriktir: 40 m menzil, 2 s'de bir gözlem, %20 kaçırma, yanlış alarm yok (YOLO değil). Uçuş fiziği üretimdeki `SimulatedDrone`, kısıtlar üretimdeki `PSOEngine`. Kütüphane yöntemleri (MEALPY 3.0.3) her 30 s'de 200 değerlendirmeyle gözlenmiş kapsama haritası üzerinde hedef seçer; hub yöntemleri uçtan uca çalışır. Gizli yangın konumları yalnızca sensör ve değerlendirmede okunur.

- **Rastgele konumlu yangınlar:** rüzgâr yok, bütün yangınlar alanda rastgele.
- **Rüzgâr altı artçı yangınlar:** 5 m/s rüzgâr (yönü tohuma göre rastgele, operatör girdisi olarak hub'a verilir); artçılar ilk yangının 150–450 m rüzgâr altında, ±25° içinde tutuşur.

**Tohum disiplini.** Hibrit yöntemin tasarımı ve eşikleri 101–120 tohumlarında seçildi. 201–240 tohumları bir kez değerlendirildi; rüzgârsız senaryodaki zayıflığı (eski hibrit, rüzgâr yokken en eski hücreleri yeniden ziyaret ediyordu) bu değerlendirme gösterdi. Düzeltme yeniden 101–120 üzerinde seçildi ve aşağıdaki sayılar **hiç kullanılmamış 241–280** tohumlarından gelir (senaryo başına 40 tohum × 21 yöntem = 840 koşu, hata yok).

**Ölçüler.** *Bulunan*: 160 yangından bulunan oran. *Artçı tespit süresi*: tutuşmadan tespite; bulunamayan artçıya ufka kadar geçen süre yazılır. *Ortalama gecikme*: tüm yangınlar için aynı ceza kuralıyla. *En az ayrılma*: tüm koşulardaki en yakın iki drone (30 m altı güvenlik ihlali sayılır; hiçbir yöntemde yok).

### Rüzgâr altı artçı yangınlar

| Sıra | Yöntem | İlk yangın (s) | Bulunan | Artçı bulunan | Artçı tespit süresi (s) | Ortalama gecikme (s) | En az ayrılma (m) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1/21 | **Hub hibrit (yeni varsayılan)** | 70.7 | %99.4 | %98.8 | 75.5 | 103.4 | 44.4 |
| 2/21 | Hub tam uyarlanır | 88.2 | %98.8 | %98.8 | 112.8 | 136.2 | 61.4 |
| 3/21 | Hub şerit (sensöre uygun aralık) | 70.7 | %93.1 | %86.2 | 133.6 | 135.2 | 72.2 |
| 4/21 | DE (MEALPY) | 68.9 | %91.9 | %83.8 | 139.1 | 134.8 | 46.5 |
| 5/21 | SSA (MEALPY) | 67.8 | %91.9 | %83.8 | 162.2 | 148.4 | 47.2 |
| 6/21 | GWO (MEALPY) | 93.3 | %90.0 | %80.0 | 155.7 | 159.4 | 50.3 |
| 7/21 | FFA (MEALPY) | 68.1 | %89.4 | %78.8 | 157.8 | 136.7 | 48.3 |
| 8/21 | HCO (MEALPY) | 64.5 | %89.4 | %78.8 | 157.7 | 144.6 | 49.1 |
| 9/21 | PSO (MEALPY) | 81.5 | %89.4 | %81.2 | 152.8 | 152.0 | 46.7 |
| 10/21 | BA (MEALPY) | 64.0 | %88.8 | %78.8 | 166.5 | 149.6 | 48.0 |
| 11/21 | HHO (MEALPY) | 69.2 | %88.8 | %80.0 | 159.7 | 149.7 | 46.6 |
| 12/21 | CMA-ES | 64.8 | %88.1 | %77.5 | 157.7 | 146.0 | 48.3 |
| 13/21 | FFO (MEALPY) | 64.7 | %88.1 | %78.8 | 157.9 | 148.0 | 46.9 |
| 14/21 | CEM (MEALPY) | 75.2 | %87.5 | %76.2 | 160.4 | 151.6 | 45.7 |
| 15/21 | SFO (MEALPY) | 62.2 | %86.9 | %73.8 | 161.2 | 147.2 | 46.7 |
| 16/21 | WHO (MEALPY) | 56.3 | %86.2 | %73.8 | 169.1 | 150.5 | 50.1 |
| 17/21 | Hub şerit (yayımlanan eski) | 73.3 | %85.6 | %85.0 | 120.4 | 152.7 | 66.2 |
| 18/21 | TOA (MEALPY) | 49.8 | %85.0 | %71.2 | 166.3 | 147.3 | 47.7 |
| 19/21 | GA (MEALPY) | 67.0 | %84.4 | %70.0 | 190.3 | 165.4 | 49.3 |
| 20/21 | DO (MEALPY) | 73.0 | %84.4 | %68.8 | 193.2 | 165.5 | 46.6 |
| 21/21 | Rastgele hedef | 118.3 | %70.6 | %52.5 | 196.3 | 213.3 | 45.4 |

### Rastgele konumlu yangınlar

| Sıra | Yöntem | İlk yangın (s) | Bulunan | Artçı bulunan | Artçı tespit süresi (s) | Ortalama gecikme (s) | En az ayrılma (m) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1/21 | DO (MEALPY) | 70.2 | %96.9 | %93.8 | 119.1 | 128.5 | 46.6 |
| 2/21 | **Hub hibrit (yeni varsayılan)** | 70.7 | %96.9 | %95.0 | 117.4 | 128.9 | 53.1 |
| 3/21 | Hub şerit (sensöre uygun aralık) | 70.7 | %96.9 | %95.0 | 117.4 | 128.9 | 53.1 |
| 4/21 | GA (MEALPY) | 66.8 | %95.6 | %92.5 | 131.1 | 135.8 | 49.3 |
| 5/21 | SSA (MEALPY) | 66.9 | %94.4 | %88.8 | 139.0 | 136.8 | 47.2 |
| 6/21 | SFO (MEALPY) | 64.0 | %93.8 | %87.5 | 130.4 | 131.8 | 46.7 |
| 7/21 | TOA (MEALPY) | 49.8 | %93.1 | %87.5 | 141.8 | 135.0 | 47.7 |
| 8/21 | DE (MEALPY) | 72.9 | %93.1 | %86.2 | 143.2 | 136.9 | 46.5 |
| 9/21 | HCO (MEALPY) | 64.5 | %92.5 | %85.0 | 127.0 | 129.3 | 49.1 |
| 10/21 | CMA-ES | 66.2 | %92.5 | %86.2 | 142.1 | 138.2 | 48.3 |
| 11/21 | CEM (MEALPY) | 75.0 | %92.5 | %86.2 | 134.2 | 138.4 | 45.7 |
| 12/21 | FFA (MEALPY) | 68.1 | %91.9 | %83.8 | 143.4 | 129.5 | 48.3 |
| 13/21 | BA (MEALPY) | 64.0 | %91.2 | %83.8 | 131.2 | 131.9 | 48.0 |
| 14/21 | WHO (MEALPY) | 57.0 | %91.2 | %83.8 | 148.2 | 140.1 | 50.1 |
| 15/21 | PSO (MEALPY) | 77.9 | %91.2 | %85.0 | 155.7 | 153.4 | 46.7 |
| 16/21 | FFO (MEALPY) | 64.7 | %90.6 | %83.8 | 160.6 | 149.3 | 46.9 |
| 17/21 | HHO (MEALPY) | 69.6 | %90.0 | %82.5 | 133.4 | 136.6 | 46.6 |
| 18/21 | GWO (MEALPY) | 94.7 | %89.4 | %78.8 | 150.4 | 156.8 | 50.3 |
| 19/21 | Hub tam uyarlanır | 88.2 | %88.1 | %78.8 | 137.7 | 145.6 | 74.0 |
| 20/21 | Hub şerit (yayımlanan eski) | 72.9 | %81.9 | %75.0 | 157.0 | 166.0 | 66.3 |
| 21/21 | Rastgele hedef | 110.2 | %81.2 | %73.8 | 143.9 | 187.2 | 45.4 |

Sıra: önce bulunan oran, sonra ortalama gecikme. Rüzgârsız senaryoda hibrit tanım gereği şerit taramayla aynı koşar (bilinen yangın rüzgâr altı konisi oluşturmaz). Bu sonuçlar yangın algılama modelinin sahadaki doğruluğunu veya fiziksel uçuş yeterliliğini göstermez.

Yeniden üretim:

```powershell
py -3.11 scripts/compare_swarm_search.py --families all --scenario spotting --seeds 241 242 ... 280 --algorithms Hub-Hybrid-PSO ... --output artifacts/search_v2/parts/spotting_0
py -3.11 scripts/merge_search_parts.py
py -3.11 scripts/make_search_report.py
```

Ham sonuçlar: `artifacts/search_v2/final_uniform/`, `artifacts/search_v2/final_spotting/`.

---

## Önceki tarama (19 Eylül 2026, tarihsel)

**137 yöntem / 685 koşu tamamlandı.** 5 koşu hata verdi; bunlar başarı tablosuna çevrilmedi. Liste MEALPY 3.0.3 içindeki 134 Original uygulama + CMA-ES + hub PSO ve rastgele referanstan oluşur. Bu, dünyadaki bütün optimizasyon teknikleri değildir.

İlk yangını ortalamada en erken gören: **FFO.OriginalFFO — 35.6 s**; toplam keşfi %90.0. Keşif oranı, ardından kaçırmalar dahil gecikme sıralamasında önde: **SFO.OriginalSFO**. Bunlar yalnızca aşağıdaki beş sentetik senaryonun sonuçlarıdır; bağımsız saha doğrulaması veya evrensel kazanan değildir.

## Deneyin gerçekte ölçtüğü

- Tohumlar: 101–105. Aynı tohumda tüm yöntemlere aynı 4 hedef, başlangıç ve sensör koşulları. Alan 800×800 m, 4 drone, 600 saniye. İki hedef başlangıçta, artçı hedefler 180 ve 360. saniyede tutuşur.
- Fizik 0.5 s adımlı üretim `SimulatedDrone`; yol/ayrılma/hız kısıtları üretim `PSOEngine`. 10 m/s hız ve 2.5 m/s² nominal ivme sınırı. Başlangıç 85 m. Bu bir aerodinamik/rüzgâr/terrain/HIL modeli değildir.
- Sensör özellikle SENTETİK: 40 m menzil, 2 s gözlem aralığı, %20 kaçırma olasılığı. Yanlış pozitif yok. YOLO sonucuyla karıştırılmamalı. Rastgele sensör çekilişi senaryo/hedef/drone/zamana bağlıdır.
- Gizli koordinatlar sadece sensör ve değerlendirmede okunur. Optimizasyon hedef fonksiyonu gözlenmiş kapsama haritasını ve drone konumlarını alır; gelecekteki tutuşmaları bilmez.
- Kütüphane yöntemlerinde her 30 s yeniden planlama, aynı 50 başlangıç adayı ve en çok 200 hedef fonksiyonu değerlendirmesi. En iyi değerlendirilmiş aday kullanılır. Epoch sayısını eşit bütçe gibi göstermiyoruz. Ham kayıtta gerçek değerlendirme sayısı var.
- Hub PSO uçtan uca referanstır; kütüphane yöntemleri ortak kapsama vekil amaç fonksiyonunu optimize eder. Hub algoritmasına kütüphane eşit hesap bütçesi atanmış değildir. Bu yöntem aileleri arasında arama stratejisi taramasıdır.
- İlk keşif: hiç bulunmazsa 600 s. Gecikme: her hedefin tutuşma→tespit süresi; bulunamayan hedefe tutuşma→600 s atanır. Kaçırılanlar ortalamadan silinmez. Keşif oranı toplam bulunan / toplam 20 hedeftir.
- Beş tohum bir ön taramadır. Aynı senaryolardan yöntem seçildiği için seçim yanlılığı vardır. Ayrı doğrulama senaryosu, hiperparametre bütçesi çalışması ve güven aralığı olmadan kesin en iyi iddiası yoktur.
- Güvenlik sütunu yalnızca kayıttaki en az 30 m ayrılma ve sıfır sınır aşımıdır. Radyo kaybı, gerçek engel, hava durumu, batarya doğruluğu veya fiziksel uçuş yeterliliği değildir. Güvenlik ihlalli yöntemler varsa alta taşınır; sonuçları silinmez.

## Karşılaştırmalı tablo

| Yöntem | İlk keşif ort. (s) | Tüm yangın keşfi | Artçı keşfi | Kaçırmalar dahil gecikme (s) | En az ayrılma (m) | Kısıt testi |
|---|---:|---:|---:|---:|---:|---|
| SFO.OriginalSFO | 40.0 | %100.0 | %100.0 | 86.2 | 52.8 | Geçti |
| FFA.OriginalFFA | 64.8 | %100.0 | %100.0 | 90.5 | 51.9 | Geçti |
| WHO.OriginalWHO | 57.2 | %100.0 | %100.0 | 95.2 | 55.5 | Geçti |
| DO.OriginalDO | 62.8 | %100.0 | %100.0 | 99.2 | 50.1 | Geçti |
| SSA.OriginalSSA | 67.6 | %100.0 | %100.0 | 104.7 | 52.1 | Geçti |
| HCO.OriginalHCO | 91.6 | %100.0 | %100.0 | 105.1 | 49.4 | Geçti |
| TOA.OriginalTOA | 56.4 | %100.0 | %100.0 | 106.5 | 55.4 | Geçti |
| HHO.OriginalHHO | 65.2 | %100.0 | %100.0 | 108.6 | 52.0 | Geçti |
| CEM.OriginalCEM | 83.6 | %100.0 | %100.0 | 111.0 | 54.5 | Geçti |
| BA.OriginalBA | 89.6 | %100.0 | %100.0 | 112.7 | 51.5 | Geçti |
| ARO.OriginalARO | 128.4 | %100.0 | %100.0 | 114.2 | 50.5 | Geçti |
| EVO.OriginalEVO | 73.6 | %100.0 | %100.0 | 119.6 | 50.6 | Geçti |
| BRO.OriginalBRO | 58.4 | %100.0 | %100.0 | 122.6 | 47.2 | Geçti |
| CA.OriginalCA | 72.8 | %100.0 | %100.0 | 127.6 | 54.0 | Geçti |
| AO.OriginalAO | 99.6 | %100.0 | %100.0 | 128.7 | 48.2 | Geçti |
| CDO.OriginalCDO | 41.6 | %100.0 | %100.0 | 130.2 | 53.9 | Geçti |
| SBO.OriginalSBO | 84.8 | %100.0 | %100.0 | 132.7 | 53.6 | Geçti |
| EFO.OriginalEFO | 91.6 | %100.0 | %100.0 | 133.1 | 51.3 | Geçti |
| ZOA.OriginalZOA | 76.4 | %100.0 | %100.0 | 136.5 | 57.6 | Geçti |
| BBO.OriginalBBO | 119.2 | %100.0 | %100.0 | 136.7 | 55.9 | Geçti |
| ArchOA.OriginalArchOA | 100.4 | %100.0 | %100.0 | 140.4 | 48.1 | Geçti |
| CHIO.OriginalCHIO | 95.6 | %100.0 | %100.0 | 141.0 | 55.2 | Geçti |
| LCO.OriginalLCO | 84.8 | %100.0 | %100.0 | 144.9 | 47.4 | Geçti |
| FBIO.OriginalFBIO | 70.0 | %100.0 | %100.0 | 146.5 | 57.1 | Geçti |
| AVOA.OriginalAVOA | 152.8 | %100.0 | %100.0 | 150.1 | 55.9 | Geçti |
| ACOR.OriginalACOR | 109.6 | %100.0 | %100.0 | 158.4 | 48.4 | Geçti |
| ESOA.OriginalESOA | 99.6 | %100.0 | %100.0 | 171.9 | 49.7 | Geçti |
| SARO.OriginalSARO | 110.0 | %100.0 | %100.0 | 178.9 | 52.5 | Geçti |
| WaOA.OriginalWaOA | 146.0 | %100.0 | %100.0 | 180.5 | 49.4 | Geçti |
| SLO.OriginalSLO | 50.8 | %95.0 | %90.0 | 97.4 | 52.5 | Geçti |
| EHO.OriginalEHO | 76.8 | %95.0 | %90.0 | 97.9 | 49.5 | Geçti |
| SSpiderO.OriginalSSpiderO | 60.4 | %95.0 | %90.0 | 99.3 | 50.8 | Geçti |
| ES.CMA_ES | 39.2 | %95.0 | %90.0 | 101.9 | 53.5 | Geçti |
| BSA.OriginalBSA | 51.6 | %95.0 | %90.0 | 102.4 | 54.3 | Geçti |
| BeesA.OriginalBeesA | 84.8 | %95.0 | %90.0 | 105.2 | 52.9 | Geçti |
| HGS.OriginalHGS | 78.0 | %95.0 | %90.0 | 106.8 | 47.2 | Geçti |
| BFO.OriginalBFO | 84.8 | %95.0 | %90.0 | 107.5 | 50.4 | Geçti |
| FA.OriginalFA | 84.8 | %95.0 | %90.0 | 107.5 | 50.4 | Geçti |
| GA.OriginalGA | 84.8 | %95.0 | %90.0 | 107.5 | 50.4 | Geçti |
| ABC.OriginalABC | 42.0 | %95.0 | %90.0 | 111.7 | 54.9 | Geçti |
| EP.OriginalEP | 92.4 | %95.0 | %90.0 | 117.6 | 53.0 | Geçti |
| WDO.OriginalWDO | 84.8 | %95.0 | %90.0 | 117.8 | 52.1 | Geçti |
| SSpiderA.OriginalSSpiderA | 56.8 | %95.0 | %90.0 | 118.2 | 46.6 | Geçti |
| ES.OriginalES | 90.0 | %95.0 | %90.0 | 119.2 | 57.0 | Geçti |
| CSO.OriginalCSO | 80.8 | %95.0 | %90.0 | 120.4 | 52.0 | Geçti |
| ASO.OriginalASO | 57.6 | %95.0 | %90.0 | 122.7 | 51.2 | Geçti |
| HBO.OriginalHBO | 57.2 | %95.0 | %90.0 | 124.2 | 54.5 | Geçti |
| MSA.OriginalMSA | 52.8 | %95.0 | %90.0 | 126.1 | 57.8 | Geçti |
| EOA.OriginalEOA | 92.8 | %95.0 | %90.0 | 131.2 | 54.5 | Geçti |
| TDO.OriginalTDO | 90.8 | %95.0 | %90.0 | 131.4 | 51.4 | Geçti |
| CSA.OriginalCSA | 95.2 | %95.0 | %90.0 | 131.5 | 54.5 | Geçti |
| SCA.OriginalSCA | 58.8 | %95.0 | %90.0 | 134.0 | 53.3 | Geçti |
| FPA.OriginalFPA | 61.6 | %95.0 | %90.0 | 135.1 | 52.4 | Geçti |
| SquirrelSA.OriginalSquirrelSA | 44.8 | %95.0 | %90.0 | 136.2 | 48.2 | Geçti |
| SHIO.OriginalSHIO | 75.2 | %95.0 | %90.0 | 137.6 | 53.2 | Geçti |
| SPBO.OriginalSPBO | 64.8 | %95.0 | %90.0 | 137.9 | 49.8 | Geçti |
| ServalOA.OriginalServalOA | 86.0 | %95.0 | %90.0 | 138.4 | 48.3 | Geçti |
| SOA.OriginalSOA | 97.2 | %95.0 | %90.0 | 141.7 | 52.2 | Geçti |
| CoatiOA.OriginalCoatiOA | 62.4 | %95.0 | %100.0 | 141.9 | 54.0 | Geçti |
| IWO.OriginalIWO | 124.0 | %95.0 | %90.0 | 142.9 | 51.9 | Geçti |
| RUN.OriginalRUN | 100.0 | %95.0 | %90.0 | 144.7 | 51.4 | Geçti |
| AOA.OriginalAOA | 120.4 | %95.0 | %90.0 | 145.6 | 45.3 | Geçti |
| CDDO.OriginalCDDO | 88.0 | %95.0 | %100.0 | 148.2 | 58.4 | Geçti |
| NRO.OriginalNRO | 102.0 | %95.0 | %100.0 | 148.4 | 54.7 | Geçti |
| AGTO.OriginalAGTO | 132.0 | %95.0 | %100.0 | 150.2 | 52.9 | Geçti |
| SOS.OriginalSOS | 80.0 | %95.0 | %90.0 | 150.6 | 52.3 | Geçti |
| HGSO.OriginalHGSO | 69.2 | %95.0 | %90.0 | 150.9 | 50.6 | Geçti |
| OOA.OriginalOOA | 98.0 | %95.0 | %90.0 | 151.6 | 55.9 | Geçti |
| BBOA.OriginalBBOA | 85.2 | %95.0 | %90.0 | 152.1 | 54.0 | Geçti |
| HS.OriginalHS | 88.8 | %95.0 | %90.0 | 156.9 | 53.4 | Geçti |
| CGO.OriginalCGO | 126.4 | %95.0 | %90.0 | 160.7 | 51.3 | Geçti |
| COA.OriginalCOA | 101.2 | %95.0 | %90.0 | 164.4 | 54.5 | Geçti |
| STO.OriginalSTO | 123.6 | %95.0 | %90.0 | 166.9 | 50.3 | Geçti |
| MFO.OriginalMFO | 100.0 | %95.0 | %100.0 | 179.2 | 52.3 | Geçti |
| SeaHO.OriginalSeaHO | 181.2 | %95.0 | %100.0 | 184.8 | 57.1 | Geçti |
| MVO.OriginalMVO | 97.2 | %95.0 | %90.0 | 187.3 | 53.7 | Geçti |
| TWO.OriginalTWO | 123.6 | %95.0 | %90.0 | 192.0 | 47.7 | Geçti |
| POA.OriginalPOA | 218.4 | %95.0 | %100.0 | 200.9 | 57.7 | Geçti |
| SSDO.OriginalSSDO | 39.6 | %90.0 | %80.0 | 110.3 | 48.3 | Geçti |
| TS.OriginalTS | 84.8 | %90.0 | %80.0 | 110.3 | 53.5 | Geçti |
| CircleSA.OriginalCircleSA | 66.8 | %90.0 | %80.0 | 111.1 | 52.2 | Geçti |
| EO.OriginalEO | 69.2 | %90.0 | %80.0 | 112.8 | 49.4 | Geçti |
| MRFO.OriginalMRFO | 53.6 | %90.0 | %80.0 | 114.7 | 50.8 | Geçti |
| FFO.OriginalFFO | 35.6 | %90.0 | %80.0 | 115.8 | 51.3 | Geçti |
| BES.OriginalBES | 69.2 | %90.0 | %80.0 | 119.1 | 51.1 | Geçti |
| ESO.OriginalESO | 75.6 | %90.0 | %90.0 | 121.5 | 51.9 | Geçti |
| BSO.OriginalBSO | 90.4 | %90.0 | %80.0 | 127.0 | 51.6 | Geçti |
| MA.OriginalMA | 90.8 | %90.0 | %80.0 | 133.7 | 54.5 | Geçti |
| GWO.OriginalGWO | 45.6 | %90.0 | %80.0 | 134.0 | 49.2 | Geçti |
| TSA.OriginalTSA | 96.0 | %90.0 | %80.0 | 136.3 | 55.4 | Geçti |
| INFO.OriginalINFO | 73.6 | %90.0 | %80.0 | 139.5 | 54.3 | Geçti |
| FOX.OriginalFOX | 84.8 | %90.0 | %80.0 | 140.9 | 52.8 | Geçti |
| SHADE.OriginalSHADE | 79.6 | %90.0 | %80.0 | 145.6 | 52.0 | Geçti |
| PFA.OriginalPFA | 102.0 | %90.0 | %80.0 | 147.3 | 52.5 | Geçti |
| GBO.OriginalGBO | 100.4 | %90.0 | %80.0 | 147.4 | 57.7 | Geçti |
| GOA.OriginalGOA | 80.8 | %90.0 | %80.0 | 152.6 | 56.6 | Geçti |
| QSA.OriginalQSA | 51.2 | %90.0 | %80.0 | 153.8 | 52.7 | Geçti |
| HBA.OriginalHBA | 79.6 | %90.0 | %80.0 | 158.9 | 46.5 | Geçti |
| SRSR.OriginalSRSR | 90.4 | %90.0 | %80.0 | 161.6 | 56.7 | Geçti |
| NMRA.OriginalNMRA | 97.2 | %90.0 | %90.0 | 164.0 | 53.6 | Geçti |
| SCSO.OriginalSCSO | 90.8 | %90.0 | %80.0 | 167.5 | 51.9 | Geçti |
| AEO.OriginalAEO | 92.4 | %90.0 | %90.0 | 171.3 | 54.6 | Geçti |
| HC.OriginalHC | 128.4 | %90.0 | %80.0 | 174.8 | 48.4 | Geçti |
| TLO.OriginalTLO | 90.8 | %90.0 | %90.0 | 176.2 | 55.4 | Geçti |
| PSS.OriginalPSS | 137.2 | %90.0 | %80.0 | 178.7 | 53.7 | Geçti |
| BMO.OriginalBMO | 110.8 | %90.0 | %90.0 | 183.2 | 52.7 | Geçti |
| MGO.OriginalMGO | 75.6 | %90.0 | %90.0 | 192.2 | 53.4 | Geçti |
| FLA.OriginalFLA | 100.8 | %90.0 | %80.0 | 194.5 | 56.8 | Geçti |
| VCS.OriginalVCS | 139.2 | %90.0 | %90.0 | 209.2 | 56.7 | Geçti |
| DMOA.OriginalDMOA | 88.4 | %85.0 | %80.0 | 133.5 | 56.2 | Geçti |
| WCA.OriginalWCA | 96.8 | %85.0 | %70.0 | 136.9 | 49.7 | Geçti |
| NGO.OriginalNGO | 95.6 | %85.0 | %70.0 | 138.7 | 48.3 | Geçti |
| AFT.OriginalAFT | 62.4 | %85.0 | %80.0 | 141.5 | 48.3 | Geçti |
| Hub-Constrained-PSO | 77.2 | %85.0 | %70.0 | 155.9 | 73.9 | Geçti |
| FOA.OriginalFOA | 59.6 | %85.0 | %80.0 | 157.3 | 51.6 | Geçti |
| GSKA.OriginalGSKA | 64.8 | %85.0 | %80.0 | 158.3 | 54.9 | Geçti |
| WarSO.OriginalWarSO | 82.8 | %85.0 | %70.0 | 158.6 | 51.6 | Geçti |
| GTO.OriginalGTO | 72.8 | %85.0 | %80.0 | 162.9 | 53.5 | Geçti |
| TSO.OriginalTSO | 91.6 | %85.0 | %70.0 | 169.6 | 53.8 | Geçti |
| WOA.OriginalWOA | 97.6 | %85.0 | %70.0 | 171.5 | 55.0 | Geçti |
| PSO.OriginalPSO | 113.2 | %85.0 | %70.0 | 173.3 | 48.9 | Geçti |
| DE.OriginalDE | 103.2 | %85.0 | %70.0 | 173.8 | 53.9 | Geçti |
| ICA.OriginalICA | 75.2 | %85.0 | %80.0 | 177.4 | 50.3 | Geçti |
| FDO.OriginalFDO | 102.8 | %85.0 | %80.0 | 185.5 | 52.3 | Geçti |
| RIME.OriginalRIME | 94.8 | %85.0 | %70.0 | 196.4 | 46.8 | Geçti |
| GJO.OriginalGJO | 58.4 | %85.0 | %70.0 | 201.6 | 53.3 | Geçti |
| JA.OriginalJA | 169.6 | %85.0 | %70.0 | 203.0 | 54.5 | Geçti |
| MPA.OriginalMPA | 191.6 | %85.0 | %70.0 | 204.8 | 49.8 | Geçti |
| CRO.OriginalCRO | 72.0 | %80.0 | %60.0 | 165.0 | 54.3 | Geçti |
| GCO.OriginalGCO | 66.8 | %80.0 | %70.0 | 190.6 | 51.7 | Geçti |
| SHO.OriginalSHO | 110.4 | %80.0 | %60.0 | 193.4 | 46.2 | Geçti |
| SSO.OriginalSSO | 147.6 | %80.0 | %60.0 | 203.5 | 46.9 | Geçti |
| SMA.OriginalSMA | 129.2 | %80.0 | %80.0 | 206.2 | 59.5 | Geçti |
| SA.OriginalSA | 103.6 | %75.0 | %60.0 | 173.3 | 53.9 | Geçti |
| ALO.OriginalALO | 130.4 | %75.0 | %60.0 | 207.4 | 48.2 | Geçti |
| Random-waypoints | 234.8 | %65.0 | %60.0 | 271.1 | 46.1 | Geçti |

## Hata veren koşular

- **BCO.OriginalBCO**: 5 koşu. `ValueError("'n_chemotaxis' is an integer and value should be in range: (1, 5).")`. Farklı algoritmayla sessizce değiştirilmedi; bu kurulum/parametre kümesinde karşılaştırma başarısız.

## Gerçek YOLO ile ayrı operatör deneyi

`scripts/operator_trial.py` gerçek `best.pt` modelini çağırdı; Mock kullanılmadı. 600 saniyelik hub devriyesinde iki başlangıç hedefi ve 180 s gecikmeli üçüncü hedef vardı. İlk anda aday/gbest sıfırdı. İlk iki hedefin 75 m yakınında sensör adayları oluştu; üçüncü hedef yakınında aday oluşmadı. Yakınlık hedef kimliğinin kanıtı değildir. Aynı yangın birden fazla aday üretebilir; aday sayısını bulunan yangın sayısı diye saymıyoruz.
Kamera fotoğraf bankası tam kareye harmanlanır; gerçek hava kamerasının geometrisi değildir. Üçüncü örnek duman görüntüsünün model tarafından kaçırılması bilinen bir sınırlamadır. Artçı hedef başarısını uydurmak için geometrik sensör sonucunu bu deneye taşımadık. Model SHA256, kareler ve zaman çizgisi `artifacts/operator_trial/` içindedir.

## Bulunan ve düzeltilen hatalar

- Rastgele referans / tohum 105: önce 28.814 m ayrılma, erken itme düzeltmesinden sonra 46.113 m. Önceki başarısız kayıt `pre_fix_failure.json` içinde duruyor. Bu bir matematiksel çarpışmazlık garantisi değildir.
- Çözülen olayın çevresinde gelecekteki sensör adaylarının sürekli bastırılması giderildi; 60 s sonra yeni aday mümkün.
- Sonuç dosyasının arayüz tarafından okunurken yarım yazılma riski atomik snapshot ile giderildi; `--resume` tamamlanan kayıtları tekrar koşmaz.
- Gönüllü kamera karelerinin alınmasına rağmen algılamada kullanılmaması giderildi; poz-kare eşleme, yaş ve tekrar kontrolleri eklendi.

## Canlı kullanım ve yeniden üretme

Ana sayfada **Tatbikat → gecikme → ◇ Tatbikat hedefi → haritaya tıkla → Başlat**. Gerçeklik katmanı yalnızca operatöre gösterilir. Olay listesinde otomatik hazır yangın oluşturulmaz. Kayıt tekrarları `/static/benchmark.html` adresinde; tohum, yöntem, zaman kaydırıcısı ve oynatma seçilebilir.

```powershell
py -3.11 -m pip install -r requirements-benchmark.txt
py -3.11 scripts/compare_swarm_search.py --families all --seeds 101 102 103 104 105
py -3.11 scripts/operator_trial.py
py -3.11 -m pytest -q
```

Ham kayıt: [runs.json](../artifacts/swarm_comparison/runs.json). [CSV tablo](../artifacts/swarm_comparison/comparison.csv). [Özet](../artifacts/swarm_comparison/summary.json). [Drone entegrasyon kılavuzu](DRONE_INTEGRATION_TR.md).
Uygulama kaynağı: [MEALPY](https://github.com/thieu1995/mealpy), [swarm_based API](https://mealpy.readthedocs.io/en/latest/pages/models/mealpy.swarm_based.html). Kütüphane uygulamasını kullanmak makaledeki tüm iddiaları bağımsız doğruladığımız anlamına gelmez.
