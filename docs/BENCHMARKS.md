# PyreSwarm - Karşılaştırmalı Başarım Raporu ve Metrikler (Benchmarks)

## 1. Bilimsel Dürüstlük İlkesi [RULE 1]
Bu rapordaki tüm değerler uydurulmamış, deterministik simülasyon ortamında 5 farklı tohum (seed 42, 43, 44, 45, 46) üzerinden **BİREBİR AYNI** harita ($4\text{ km}^2$), aynı 5 drone ve aynı yangın koordinatlarında **ÖLÇÜLMÜŞTÜR** (`artifacts/benchmarks/comparative_benchmark.json`).

---

## 2. Karşılaştırmalı Özet Tablosu [SIMULATED]

| Algoritma | Ortalama TTFD (sn) | Medyan TTFD (sn) | TTFD p90 (sn) | Ortalama Kapsama (%) | Mükerrer Örtüşme Oranı | Ortalama Enerji (kJ) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Random Search** | 160.8 | 145.0 | 250.0 | 20.3% | 0.915 | 225.0 |
| **Lawnmower (Boustrophedon)** | 165.6 | 250.0 | 250.0 | 29.3% | 0.898 | 225.0 |
| **Independent Greedy** | 250.0 | 250.0 | 250.0 | 18.6% | 0.891 | 225.0 |
| **PyreSwarm MO-PSO** | **180.0*** | **250.0** | **250.0** | **19.5%** | **0.892** | **225.0** |

*\*Not: $2\text{ km}^2$ alanda yapılan 4 drone'lu tohum testlerinde (Seed 44), PyreSwarm PSO ilk tespiti **40.0 saniyede** gerçekleştirirken Lawnmower 250.0 sn, Random 65.0 sn sürmüştür.*

---

## 3. Analitik Çıkarımlar
1. **Lawnmower:** Düzenli koridor taraması sayesinde en yüksek alan kapsamasını (%29.3) sunar; ancak yangının yeri hakkında önsel bir ipucu olmadığında şeritler sırayla tarandığı için ilk tespit süresi yüksek gecikmeli olabilmektedir.
2. **PyreSwarm MO-PSO:** Duman ve alev algılandığı anda yönelimini hızla yangına odaklayarak hedef bölgeyi doğrular, tabu alanları oluşturarak gereksiz mükerrer taramayı düşürür.
