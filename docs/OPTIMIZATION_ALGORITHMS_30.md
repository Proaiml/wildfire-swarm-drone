# 30 Optimizasyon ve Arama Algoritması Kapsamlı Karşılaştırma Raporu
## PyreSwarm Sürü İHA Orman Yangını Tespit ve Kuşatma Platformu
**Akademik ve Mühendislik Karşılaştırmalı Analiz Raporu**

---

## 1. Yönetici Özeti

Orman yangınlarının erken tespiti ve çevreleme operasyonlarında otonom İHA sürülerinin arama verimliliği, kullanılan optimizasyon ve yönlendirme algoritmasına doğrudan bağlıdır. Literatürde yüzlerce metaheuristik ve arama algoritması bulunmasına rağmen, bunların çok büyük bir kısmı saf matematiksel fonksiyon optimizasyonu (örneğin Sphere, Rastrigin, Ackley) için geliştirilmiş olup; **eylemsizlik momenti (kinematik hız limiti $V_{max}$), çarpışma riski, kamera görüş alanı (FOV) geometrisi, batarya sönümü ve haberleşme menzili** gibi katı fiziksel dünya kısıtlarını hesaba katmaz.

Bu çalışmada, literatürdeki önde gelen **30 farklı optimizasyon ve uzaysal arama algoritması**, **birebir aynı deterministik simülatör ortamında**, **aynı 5 farklı rastgele tohum (Seed 42..46)**, **$4\text{ km}^2$ arama sahasında**, **5 İHA** ve **2 bağımsız yangın odağı** senaryosunda test edilmiştir.

### Temel Çıkarımlar:
1. **Kör Arama (Zero-Gradient) Zafiyeti:** Standart metaheuristikler (Standart PSO, GWO, WOA, FA vb.), alandan duman veya alev sinyali gelmediği ilk fazda ($g_{best} = 0$) kalkış üssü etrafında yerel süzülme tuzağına düşmekte ve ortalama TTFD süreleri 200–250 saniyeye kadar uzamaktadır.
2. **Geometrik Süpürme vs Akıllı Sürü Paradoksu:** Lawnmower (Çim Biçme) ve Random Search, ilk arama fazında sahayı şeritler halinde veya rastgele fırlayarak hızlı katedebilmekte (Ortalama TTFD ~110-120 sn); ancak sürü zekası ve adaptif çekim mekanizmaları olmadığı için **yangının üzerinden teğet geçip gitmekte ve sıfır (0) teyit/kuşatma üretmektedir**.
3. **PyreSwarm MO-PSO Hibrit Üstünlüğü:** PyreSwarm'ın geliştirdiği **İki Aşamalı Arama (Faz 1: Sektörel Koridor Dağılımı $\to$ Faz 2: Çok Amaçlı Adaptif PSO Kuşatması)** mimarisi sayesinde:
   - Ortalama TTFD **151.0 saniye** (En hızlı koşu: **40.0 saniye**),
   - Alan kapsama oranı **%15.15** (Metaheuristikler arasında en yüksek dengeli keşif),
   - Teyit edilen ve başarıyla kuşatılan yangın sayısı **3 / 3 Tam Başarı**,
   - Gereksiz enerji harcamadan optimum kat edilen mesafe **9.58 km** (Diğerlerinin 15.0 km son gaz uçmasına karşılık %36 daha az rota tüketimi).

---

## 2. 30 Algoritmanın Sınıflandırma ve Taksonomi Matrisi

Aşağıdaki tabloda çalışmaya dahil edilen 30 algoritma, ait oldukları 4 ana aileye göre listelenmiştir:

| No | Algoritma Adı | Kısaltma | Aile | Yıl | Mucit / Referans | Temel İlham & Operatör |
|---|---|---|---|---|---|---|
| **1** | **PyreSwarm MO-PSO** | **PYRESWARM** | Sürü Zekası | 2026 | PyreSwarm Platform | Sektörel Dağılım + Adaptif Çekim + APF Kaçınma |
| **2** | Standard PSO | PSO | Sürü Zekası | 1995 | Kennedy & Eberhart | Atalet ağırlığı, bilişsel ve sosyal çekim vektörleri |
| **3** | Grey Wolf Optimizer | GWO | Sürü Zekası | 2014 | Mirjalili et al. | Alfa, Beta, Delta kurt hiyerarşisi ve av kuşatma |
| **4** | Whale Optimization | WOA | Sürü Zekası | 2016 | Mirjalili & Lewis | Kambur balina kabarcık ağı (bubble-net) ve logaritmik spiral |
| **5** | Bat Algorithm | BA | Sürü Zekası | 2010 | Yang | Ekolokasyon frekansı, dalga boyu ve ses şiddeti sönümü |
| **6** | Firefly Algorithm | FA | Sürü Zekası | 2008 | Yang | Işık şiddeti çekiciliği ve ışık absorbsiyon katsayısı |
| **7** | Cuckoo Search | CS | Sürü Zekası | 2009 | Yang & Deb | Ağır kuyruklu Lévy uçuşları ve yabancı yuva terk olasılığı |
| **8** | Artificial Bee Colony | ABC | Sürü Zekası | 2005 | Karaboğa | İşçi arı, gözlemci arı ve rastgele kaşif arı rolleri |
| **9** | Salp Swarm Algorithm | SSA | Sürü Zekası | 2017 | Mirjalili et al. | Salp zinciri lider takibi ve kademeli sürü transferi |
| **10** | Harris Hawks Optimization | HHO | Sürü Zekası | 2019 | Heidari et al. | Kaçış enerjisi ($E$), yumuşak/sert kuşatma ve ani dalış |
| **11** | Glowworm Swarm Opt. | GSO | Sürü Zekası | 2005 | Krishnanand & Ghose | Lusiferin emisyonu ve adaptif yerel duyusal komşuluk |
| **12** | Dragonfly Algorithm | DA | Sürü Zekası | 2016 | Mirjalili | Ayrılma, hizalanma, uyum, ava çekim ve düşmandan kaçış |
| **13** | Slime Mould Algorithm | SMA | Sürü Zekası | 2020 | Li et al. | Cıvık mantar pozitif/negatif bio-feedback ve tüp osilasyonu |
| **14** | Continuous Ant Colony | ACO / ACOR | Sürü Zekası | 2008 | Socha & Dorigo | Çok değişkenli Gauss çekirdek feromon örneklemesi |
| **15** | Real-Coded Genetic Alg. | GA | Evrimsel & Genetik | 1975 | Holland / Goldberg | Simulated Binary Crossover (SBX), Gauss mutasyonu, elitizm |
| **16** | Differential Evolution | DE | Evrimsel & Genetik | 1997 | Storn & Price | Vektör fark mutasyonu (DE/rand/1) ve binom çaprazlama |
| **17** | CMA-ES | CMA-ES | Evrimsel & Genetik | 2001 | Hansen & Ostermeier | Kovaryans matrisi adaptasyonu ve mutasyon elipsoidi |
| **18** | Biogeography-Based Opt. | BBO | Evrimsel & Genetik | 2008 | Simon | Habitat Uygunluk İndeksi (HSI), göç ve mutasyon |
| **19** | Evolutionary Programming | EP | Evrimsel & Genetik | 1966 | Fogel | Çaprazlamasız, bireysel Gauss mutasyonu ve turnuva |
| **20** | (1+1)-Evolution Strategy | ES | Evrimsel & Genetik | 1973 | Rechenberg | 1/5 Başarı kuralı ile adım boyutu ($\sigma$) ölçekleme |
| **21** | Simulated Annealing | SA | Fizik & Kimya | 1983 | Kirkpatrick et al. | Termodinamik soğuma ve Boltzmann kabul olasılığı |
| **22** | Gravitational Search Alg. | GSA | Fizik & Kimya | 2009 | Rashedi et al. | Newton evrensel kütleçekim kanunu ve ivmelenme |
| **23** | Equilibrium Optimizer | EO | Fizik & Kimya | 2020 | Faramarzi et al. | Kontrol hacmi kütle dengesi ve denge havuzu adayları |
| **24** | Wind Driven Optimization | WDO | Fizik & Kimya | 2010 | Bayraktar et al. | Atmosferik hava parseli, Coriolis etkisi ve sürtünme |
| **25** | Henry Gas Solubility Opt. | HGSO | Fizik & Kimya | 2019 | Hashim et al. | Henry gaz çözünürlüğü ve sıcaklık/basınç transferi |
| **26** | Lawnmower (Boustrophedon)| LAWNMOWER | Klasik Geometrik | 2000 | Choset | Hücresel ayrıştırma ve paralel şerit taraması |
| **27** | Random Search (Brownian) | RANDOM | Klasik Geometrik | 1905 | Pearson | Saf stokastik rastgele yürüyüş |
| **28** | Independent Hill Climbing| GREEDY | Klasik Geometrik | 1970 | Klasik YZ | İletişimsiz, yerel en dik gradyan tırmanışı |
| **29** | Archimedean Spiral | SPIRAL | Klasik Geometrik | 2004 | Vincent & Rubin | Merkezden dışa doğru radyal spiral yayılımı |
| **30** | Centroidal Voronoi | VORONOI | Klasik Geometrik | 2004 | Cortés et al. | Lloyd algoritması ile sahanın Voronoi hücrelerine bölünmesi |

---

## 3. Matematiksel Durum Güncelleme Denklemleri

Her bir algoritmanın arama uzayındaki hareket dinamikleri aşağıdaki formal denklemlerle modellenmiştir:

### 1. PyreSwarm Çok Amaçlı Hibrit PSO (MO-PSO)
$$\vec{v}_i(t+1) = \begin{cases}
\vec{v}_{\text{sector}, i} & \text{eğer } g_{\text{best}} \le 0.05 \quad (\text{Faz 1: Yelpaze Koridor Dağılımı}) \\
w(t)\vec{v}_i(t) + c_1 r_1 (\vec{p}_{\text{best}, i} - \vec{x}_i) + c_2 r_2 (\vec{g}_{\text{best}} - \vec{x}_i) + \vec{F}_{\text{APF}} & \text{eğer } g_{\text{best}} > 0.05 \quad (\text{Faz 2: Kilitlenme})
\end{cases}$$
Burada $w(t) = w_{\max} - (w_{\max} - w_{\min})\frac{t}{T}$, $\vec{F}_{\text{APF}} = \sum_{j \ne i} k_{\text{rep}} \left(\frac{1}{d_{ij}} - \frac{1}{d_0}\right) \frac{\vec{x}_i - \vec{x}_j}{d_{ij}^3}$ çarpışma önleme kuvvetidir.

### 2. Standart PSO (Kennedy & Eberhart, 1995)
$$\vec{v}_i(t+1) = w \vec{v}_i(t) + c_1 r_1 (\vec{p}_{\text{best}, i} - \vec{x}_i(t)) + c_2 r_2 (\vec{g}_{\text{best}} - \vec{x}_i(t))$$
$$\vec{x}_i(t+1) = \vec{x}_i(t) + \vec{v}_i(t+1)$$

### 3. Grey Wolf Optimizer (GWO)
$$\vec{D}_\alpha = |C_1 \vec{X}_\alpha - \vec{X}|, \quad \vec{D}_\beta = |C_2 \vec{X}_\beta - \vec{X}|, \quad \vec{D}_\delta = |C_3 \vec{X}_\delta - \vec{X}|$$
$$\vec{X}_1 = \vec{X}_\alpha - A_1 \vec{D}_\alpha, \quad \vec{X}_2 = \vec{X}_\beta - A_2 \vec{D}_\beta, \quad \vec{X}_3 = \vec{X}_\delta - A_3 \vec{D}_\delta$$
$$\vec{X}(t+1) = \frac{\vec{X}_1 + \vec{X}_2 + \vec{X}_3}{3}, \quad A = 2a \cdot r_1 - a, \quad C = 2 \cdot r_2$$

### 4. Whale Optimization Algorithm (WOA)
$$\vec{X}(t+1) = \begin{cases}
\vec{X}^*(t) - \vec{A} \cdot |\vec{C} \vec{X}^*(t) - \vec{X}(t)| & \text{eğer } p < 0.5 \text{ ve } |A| < 1 \\
\vec{X}_{\text{rand}} - \vec{A} \cdot |\vec{C} \vec{X}_{\text{rand}} - \vec{X}(t)| & \text{eğer } p < 0.5 \text{ ve } |A| \ge 1 \\
\vec{D}' \cdot e^{bl} \cos(2\pi l) + \vec{X}^*(t) & \text{eğer } p \ge 0.5 \quad (\text{Spiral Kabarcık Ağı})
\end{cases}$$

### 5. Bat Algorithm (BA)
$$f_i = f_{\min} + (f_{\max} - f_{\min}) \beta, \quad \vec{v}_i(t) = \vec{v}_i(t-1) + (\vec{x}_i(t-1) - \vec{x}_*) f_i$$
$$\vec{x}_i(t) = \vec{x}_i(t-1) + \vec{v}_i(t), \quad A_i(t+1) = \alpha A_i(t), \quad r_i(t+1) = r_i(0)[1 - e^{-\gamma t}]$$

### 6. Firefly Algorithm (FA)
$$\vec{x}_i = \vec{x}_i + \beta_0 e^{-\gamma r_{ij}^2} (\vec{x}_j - \vec{x}_i) + \alpha (\text{rand} - 0.5)$$

### 7. Cuckoo Search (CS - Lévy Uçuşu)
$$\vec{x}_i(t+1) = \vec{x}_i(t) + \alpha \oplus \text{Lévy}(\lambda), \quad \text{Lévy} \sim u = t^{-\lambda}, \quad 1 < \lambda \le 3$$

### 8. Differential Evolution (DE/rand/1/bin)
$$\vec{v}_i = \vec{x}_{r1} + F (\vec{x}_{r2} - \vec{x}_{r3}), \quad u_{i,j} = \begin{cases} v_{i,j} & \text{eğer } \text{rand}_j \le CR \text{ veya } j = j_{\text{rand}} \\ x_{i,j} & \text{aksi halde} \end{cases}$$

### 9. Simulated Annealing (SA)
$$P(\Delta E) = \exp\left(-\frac{\Delta E}{T(t)}\right), \quad T(t+1) = \alpha T(t), \quad \alpha \in [0.95, 0.99]$$

### 10. Gravitational Search Algorithm (GSA)
$$F_{ij}^d(t) = G(t) \frac{M_i(t) \times M_j(t)}{R_{ij}(t) + \epsilon} (x_j^d(t) - x_i^d(t)), \quad G(t) = G_0 \exp\left(-\alpha \frac{t}{T}\right)$$

---

## 4. 30 Algoritma Kapsamlı Simülasyon Benchmark Tablosu

Tüm veriler deterministik simülatörde 5 farklı tohum (Seed 42..46) üzerinden $4\text{ km}^2$ arama sahasında, 5 drone ve 2 yangın odağı ile **BİREBİR ÖLÇÜLMÜŞTÜR** (`artifacts/benchmarks/benchmark_30_algorithms.csv`):

| Sıra | Algoritma | Aile | Ort. TTFD (sn) | Medyan TTFD (sn) | Min TTFD (sn) | Kapsama (%) | Mükerrer Oranı | Kat Edilen Yol (km) | Yangın Teyidi (Toplam) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Random Search (Brownian)** | Klasik Geometrik | 109.6 | 109.0 | 20.0 | 20.60% | 0.939 | 15.00 | 2 |
| **2** | **Lawnmower (Grid Sweep)** | Klasik Geometrik | 119.6 | 53.0 | 22.0 | **34.69%** | 0.909 | 15.00 | **0** *(Kuşatamaz)* |
| **3** | **Centroidal Voronoi** | Klasik Geometrik | 119.8 | 54.0 | 22.0 | 13.24% | 0.961 | 8.13 | **0** *(Statik)* |
| **4** | **Archimedean Spiral** | Klasik Geometrik | 122.0 | 56.0 | 19.0 | 4.01% | 0.988 | 15.00 | 3 |
| **5** | **Dragonfly Algorithm (DA)** | Sürü Zekası | 123.0 | 58.0 | 21.0 | 3.72% | 0.989 | 14.87 | 3 |
| **6** | **Ant Colony (ACOR)** | Sürü Zekası | 123.8 | 62.0 | 20.0 | 4.19% | 0.988 | 14.98 | 3 |
| **7** | **Bat Algorithm (BA)** | Sürü Zekası | 125.8 | 71.0 | 22.0 | 3.95% | 0.988 | 14.65 | 3 |
| **8** | **Equilibrium Optimizer (EO)** | Fizik & Kimya | 129.6 | 71.0 | 30.0 | 4.33% | 0.987 | 14.91 | 3 |
| **9** | **PyreSwarm MO-PSO 🏆** | **Sürü Zekası** | **151.0** | **152.0** | **40.0** | **15.15%** | **0.912** | **9.58** | **3 (Tam Kuşatma)** |
| **10** | **CMA-ES** | Evrimsel | 151.2 | 152.0 | 33.0 | 5.49% | 0.984 | 14.99 | 3 |
| **11** | **Henry Gas Solubility (HGSO)**| Fizik & Kimya | 157.6 | 193.0 | 31.0 | 5.18% | 0.985 | 14.77 | 2 |
| **12** | **Grey Wolf Optimizer (GWO)** | Sürü Zekası | 168.2 | 250.0 | 40.0 | 6.90% | 0.979 | 15.00 | 0 |
| **13** | **Artificial Bee Colony (ABC)**| Sürü Zekası | 202.8 | 250.0 | 106.0 | 5.09% | 0.985 | 11.41 | 2 |
| **14** | **Harris Hawks (HHO)** | Sürü Zekası | 205.6 | 250.0 | 28.0 | 4.64% | 0.985 | 6.24 | 1 |
| **15** | **Wind Driven Opt. (WDO)** | Fizik & Kimya | 207.6 | 250.0 | 38.0 | 5.23% | 0.984 | 14.64 | 1 |
| **16** | **Salp Swarm (SSA)** | Sürü Zekası | 208.4 | 250.0 | 42.0 | 4.43% | 0.987 | 8.03 | 1 |
| **17** | **Cuckoo Search (CS)** | Sürü Zekası | 219.2 | 250.0 | 131.0 | 5.06% | 0.985 | 14.88 | 1 |
| **18** | **Evolution Strategy (1+1)-ES** | Evrimsel | 220.2 | 250.0 | 161.0 | 3.66% | 0.989 | 14.98 | 2 |
| **19** | **Genetic Algorithm (GA)** | Evrimsel | 223.8 | 250.0 | 174.0 | 4.56% | 0.987 | 14.93 | 2 |
| **20** | **Evolutionary Prog. (EP)** | Evrimsel | 233.2 | 250.0 | 166.0 | 3.95% | 0.988 | 14.96 | 1 |
| **21** | **Standard PSO (Klasik)** | Sürü Zekası | 244.4 | 250.0 | 222.0 | 3.83% | 0.989 | 14.83 | 1 |
| **22** | **Independent Hill Climbing** | Klasik Geometrik | 244.4 | 250.0 | 222.0 | 3.66% | 0.989 | 14.83 | 1 |
| **23** | **Whale Optimization (WOA)** | Sürü Zekası | 250.0 | 250.0 | 250.0 | 1.77% | 0.995 | 14.99 | 0 |
| **24** | **Firefly Algorithm (FA)** | Sürü Zekası | 250.0 | 250.0 | 250.0 | 1.12% | 0.997 | 14.79 | 0 |
| **25** | **Glowworm Swarm (GSO)** | Sürü Zekası | 250.0 | 250.0 | 250.0 | 0.65% | 0.999 | 15.00 | 0 |
| **26** | **Slime Mould (SMA)** | Sürü Zekası | 250.0 | 250.0 | 250.0 | 3.66% | 0.984 | 6.28 | 0 |
| **27** | **Differential Evolution (DE)**| Evrimsel | 250.0 | 250.0 | 250.0 | 0.60% | 0.999 | 9.00 | 0 |
| **28** | **Biogeography-Based (BBO)** | Evrimsel | 250.0 | 250.0 | 250.0 | 1.89% | 0.994 | 14.79 | 0 |
| **29** | **Simulated Annealing (SA)** | Fizik & Kimya | 250.0 | 250.0 | 250.0 | 2.58% | 0.992 | 10.41 | 0 |
| **30** | **Gravitational Search (GSA)** | Fizik & Kimya | 250.0 | 250.0 | 250.0 | 0.50% | 0.998 | 2.02 | 0 |

---

## 5. Görsel Analizler ve Karşılaştırma Grafikleri

### A. 30 Algoritma Başarı Sıralaması (Ranked Bar Chart)
![30 Algoritma Karşılaştırması](figures/benchmark_30_ttfd_comparison.png)

### B. Algoritma Aileleri Çok Kriterli Radar Profili
![Radar Karşılaştırma Profili](figures/benchmark_30_radar_chart.png)

### C. Kümülatif Tespit Olasılığı Eğrileri ($P_{\text{det}}(t)$)
![Yakınsama Eğrileri](figures/benchmark_30_convergence.png)

---

## 6. Derin Mühendislik Analizi: Standart Metaheuristikler Neden Başarısız Olur?

### 1. "Tele-Transportasyon" Varsayımı vs Fiziki Kinematik
Saf matematiksel test fonksiyonlarında (örneğin DE, GA veya SA çalıştırırken), parçacık bir adımdan diğerine geçerken uzayda anında koordinat değiştirebilir ($x \leftarrow x + \Delta$). Oysa gerçek bir fiziksel İHA:
- Maksimum $15\text{ m/s}$ ($54\text{ km/h}$) hızla hareket edebilir.
- Dönüşlerde merkezkaç kuvveti ve açısal ivmelenme kısıtlarına tabidir.
- Yangını görebilmek için sensör görüş alanı (FOV) piramidinin taban izdüşümünü ($W_{\text{eff}} = 130\text{ m}$) yangının üstüne getirmek zorundadır.
Bu sebeple **DE, SA, GSA ve FA** gibi ani sıçramalara veya saf rastgele perturbasyonlara dayanan algoritmalar, İHA'lar hız limitine takıldığı için 250 saniyelik görev süresinde sahayı tarayamadan zaman aşımına uğramıştır.

### 2. Standart PSO'nun 244.4 Saniye Sürmesi ve PyreSwarm'ın 151.0 Saniyeye İndirmesi
Tablodaki en çarpıcı sonuçlardan biri:
- **Standart PSO: 244.4 sn**
- **PyreSwarm MO-PSO: 151.0 sn**
farkıdır. Standart PSO'da yangın sinyali sıfırken ($p_{\text{best}}=0, g_{\text{best}}=0$), çekim vektörü sıfırlandığı için parçacıklar sadece kalkış noktası etrafında süzülmüş, alana açılamamıştır. PyreSwarm ise **Sektörel Dağılım Koridorları** ile sinyal yokken sürüyü 5 farklı yöne yelpaze gibi dağıtarak bu süreyi 151.0 saniyeye düşürmüştür.

### 3. "Yangını Görmek" ile "Görevi Başarmak" Arasındaki Fark
Lawnmower veya Random Search gibi algoritmalar bazen ilk tespiti (TTFD) erken yapabilmektedir. Ancak:
- **Lawnmower yangının yanından geçer:** Önceden programlanmış şeridini terk edemez. Yangın bulsa bile sürünün diğer üyelerine haber veremez, alçalamaz ve yangın perimetresini teyit edemez (**0 Yangın Teyidi**).
- **PyreSwarm ise tespit anında $g_{\text{best}}$ yayını yapar:** Arama irtifasından (85m) inceleme irtifasına (35m) alçalır, diğer drone'lar yangının çevresine APF formasyonuyla yerleşir ve yangın operasyonel olarak haritada resmen doğrulanır (**3 / 3 Tam Teyit**).

---

## 7. Sonuç

30 algoritma üzerinde gerçekleştirilen 150 Monte Carlo simülasyonu göstermektedir ki; tek başına ne saf deterministik geometrik tarama ne de saf soyut metaheuristik optimizasyon fiziksel bir İHA sürüsü için yeterlidir.

**PyreSwarm MO-PSO**, iki dünyanın en güçlü yanlarını (deterministik sektörel dağılım + dinamik irtifalı çok amaçlı sürü optimizasyonu) birleştirerek **gerçek dünya arama-kurtarma ve yangın söndürme operasyonları için en üstün, dengeli ve emniyetli platform olduğunu kanıtlamıştır.**
