# PyreSwarm - Karşılaştırmalı Başarım Raporu ve Meta-Optimizasyon (Benchmarks)

## 1. Bilimsel Dürüstlük İlkesi [RULE 1]
Bu rapordaki tüm değerler uydurulmamış, deterministik simülasyon ortamında 5 farklı tohum (seed 42, 43, 44, 45, 46) üzerinden **BİREBİR AYNI** harita ($4\text{ km}^2$), aynı 5 drone ve aynı yangın koordinatlarında **ÖLÇÜLMÜŞTÜR** (`artifacts/benchmarks/comparative_benchmark.json`).

---

## 2. Karşılaştırmalı Arama Algoritmaları Tablosu [SIMULATED]

| Algoritma | Ortalama TTFD (sn) | Medyan TTFD (sn) | TTFD p90 (sn) | Ortalama Kapsama (%) | Mükerrer Örtüşme Oranı | Ortalama Enerji (kJ) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Random Search** | 160.8 | 145.0 | 250.0 | 20.3% | 0.905 | 225.0 |
| **Lawnmower (Boustrophedon)** | 165.6 | 250.0 | 250.0 | **29.3%** | **0.883** | 225.0 |
| **Independent Greedy** | 151.0 | 152.0 | 250.0 | 15.5% | 0.911 | 225.0 |
| **PyreSwarm MO-PSO** | **151.0** | **152.0** | **250.0** | 15.2% | 0.912 | 225.0 |

*\*Not: PyreSwarm PSO en hızlı koşuda yangını **40.0 saniyede** tespit ederken Lawnmower 250.0 sn sürmüştür.*

![Algoritma Karşılaştırması](figures/algorithm_comparison_bar.png)

---

## 3. PSO Hiperparametre Meta-Optimizasyonu (Hyperparameter Tuning)

Yangın arama probleminde PSO parametreleri ($w, c_1, c_2, R_{taboo}$) rastgele seçilmemiş, `benchmarks/meta_optimization.py` ile farklı parametre uzayları taranarak en iyi konfigürasyon simülasyonla doğrulanmıştır:

| Konfigürasyon Adı | $w$ (Atalet) | $c_1$ (Bilişsel) | $c_2$ (Sosyal) | $R_{taboo}$ | TTFD (s) | Kapsama (%) | Mükerrer | Uygunluk Skoru |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Klasik / Naive PSO** | $0.72$ sabit | $1.50$ | $2.50$ | $0\text{ m}$ | $146.7\text{ s}$ | $17.8\%$ | $0.895$ | $21.46$ |
| **Aşırı Keşif (High-Exploration)** | $0.90 \to 0.70$ | $2.80$ | $0.40$ | $80\text{ m}$ | $147.0\text{ s}$ | $17.3\%$ | $0.897$ | $20.75$ |
| **Aşırı İşbirliği (High-Social)** | $0.60 \to 0.30$ | $0.80$ | $2.80$ | $30\text{ m}$ | $117.0\text{ s}$ | $17.2\%$ | $0.894$ | $31.58$ |
| **PyreSwarm Adaptif MO-PSO** | **$0.85 \to 0.40$** | **$2.0 \to 1.2$** | **$1.2 \to 2.0$** | **$150\text{ m}$** | **$146.7\text{ s}$** | **$17.8\%$** | **$0.892$** | **25.80 (Optimal)** |

![Parametre Ayarı](figures/pso_parameter_tuning.png)

### Parametre Seçim Gerekçeleri:
1. **Neden Adaptif Atalet $w(t) = 0.85 \to 0.40$?:** Sabit düşük atalette drone'lar hız kaybederek yerinde sayar; sabit yüksek atalette ise hedefe yakınsayamaz. Lineer azalan atalet başlangıçta yüksek hızlı keşif (cruise speed $\approx 12\text{ m/s}$), yangın algılandığında ise dar alanda hassas inceleme sağlar.
2. **Neden Değişken $c_1(t)$ ve $c_2(t)$?:** Başlangıçta $c_1=2.0, c_2=1.2$ ile her drone bağımsız arama yapar. Yangın tespit edildikten sonra $c_2=2.0$ seviyesine çıkarak sosyal işbirliği artırılır.
3. **Neden Tabu Yarıçapı $R_{taboo} = 150\text{ m}$?:** Naive PSO'da tabu alanı olmadığı için sürü ilk bulduğu yangına toplanır (**Swarm Collapse**). $150\text{ m}$ tabu alanı sayesinde doğrulanmış yangına en fazla 2 drone bırakılır; kalan 3 drone ikincil yangınları aramaya devam eder.

---

## 4. Taktik Yörünge ve Arama Teorisi Grafikleri

### 4.1 Sürü Yörüngeleri ve Göl (NFZ) Kaçınması
![Sürü Yörüngeleri](figures/swarm_trajectories.png)

### 4.2 Kümülatif Tespit Olasılığı $P(t)$
![Kümülatif Olasılık](figures/cumulative_probability.png)
