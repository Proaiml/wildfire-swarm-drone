# Yangın ve artçı yangın arama karşılaştırması

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
