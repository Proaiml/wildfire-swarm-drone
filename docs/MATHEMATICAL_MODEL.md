# PyreSwarm - Kapsamlı Matematiksel Model ve Analiz (Mathematical Model)

Bu doküman, PyreSwarm otonom sürü drone platformunda kullanılan tüm analitik formülasyonları, fiziksel kısıtları ve teorik sınırları açıklar.

---

## 1. Koordinat ve Coğrafi Metrik Dönüşümler

### 1.1 WGS84 Elipsoid Geometrisi [MANUFACTURER_SPEC]
* Yarı-büyük eksen (Ekvatoral yarıçap): $a = 6378137.0 \text{ m}$
* Basıklık: $f = \frac{1}{298.257223563}$
* Birinci eksantriklik karesi: $e^2 = 2f - f^2 \approx 0.00669437999014$

### 1.2 Geodetic $\rightarrow$ Yerel Metrik ENU Teğet Düzlem Dönüşümü [THEORETICAL_BOUND]
Operasyon merkez referans noktası $(\phi_0, \lambda_0, h_0)$ olmak üzere:
Baş meridyen eğrilik yarıçapı $M(\phi_0)$ ve asal düşey eğrilik yarıçapı $N(\phi_0)$:
$$N(\phi_0) = \frac{a}{\sqrt{1 - e^2 \sin^2(\phi_0)}}$$
$$M(\phi_0) = \frac{a(1 - e^2)}{(1 - e^2 \sin^2(\phi_0))^{3/2}}$$

Fark koordinatları $\Delta\phi = \phi - \phi_0$, $\Delta\lambda = \lambda - \lambda_0$:
$$x_{East} = \Delta\lambda \cdot N(\phi_0) \cdot \cos(\phi_0)$$
$$y_{North} = \Delta\phi \cdot M(\phi_0)$$
$$z_{Up} = h - h_0$$

Yerel operasyon alanlarında ($R < 50 \text{ km}$) açısal distorsiyon hatası $\%0.05$'in altındadır.

---

## 2. Sensör Kapsama ve Arama Teorisi (Koopman Modeli)

### 2.1 Kamera Yer İzdüşümü (Footprint Geometry) [THEORETICAL_BOUND]
Yerden irtifa $h$ (AGL), yatay görüş açısı $HFOV = 84^\circ$, dikey görüş açısı $VFOV = 56^\circ$ iken:
* Zemin görüş genişliği: $W = 2 h \tan\left(\frac{HFOV}{2}\right) = 2 h \tan(42^\circ) \approx 1.80 h$
* Zemin görüş boyu: $L = 2 h \tan\left(\frac{VFOV}{2}\right) = 2 h \tan(28^\circ) \approx 1.06 h$
* $\%15$ yan örtüşme payı ile efektif tarama genişliği: $W_{eff} = W \cdot (1 - 0.15) = 1.53 h$

$h = 85\text{ m}$ irtifada:
* $W = 153.07\text{ m}$
* $L = 90.39\text{ m}$
* $W_{eff} = 130.11\text{ m}$

### 2.2 Alan Tarama Hızı (Area Coverage Rate - ACR) [THEORETICAL_BOUND]
Tek bir drone için yer hızı $v = 12\text{ m/s}$ ($43.2\text{ km/h}$) iken:
$$ACR = v \cdot W_{eff} = 12 \cdot 130.11 = 1561.32\text{ m}^2\text{/s} \approx 5.62\text{ km}^2\text{/h}$$

$N = 4$ drone'lu sürü için teorik üst sınır:
$$ACR_{fleet} = 4 \times 5.62 = 22.48\text{ km}^2\text{/h}$$

### 2.3 Koopman Rastgele Arama vs PSO Tespit Olasılığı [THEORETICAL_BOUND]
Zaman $t$ içinde taranan efektif alan $A_{swept}(t) = \sum_{i=1}^N \int_0^t v_i W_{eff} d\tau$. Toplam aranabilir alan $A_{total}$ ise:
* **Rastgele Arama Tespit Olasılığı:**
  $$P_{random}(t) = 1 - \exp\left(-\frac{A_{swept}(t)}{A_{total}}\right)$$
* **PyreSwarm Sürü PSO Tespit Olasılığı:**
  $$P_{pso}(t) = 1 - \exp\left(-\eta_{pso} \frac{A_{swept}(t)}{A_{total}}\right)$$
  Burada $\eta_{pso} \approx 1.62$ sürü işbirliği ve duman/ısı gradyanı çekim çarpanıdır [SIMULATED].

---

## 3. Çok Amaçlı Hedef Ulaşımı (Multi-Objective Goal Attainment)

### 3.1 Amaç Fonksiyonu Formülasyonu [THEORETICAL_BOUND]
Yangın arama yalnızca tek bir skoru maksimize etmek değildir. Bileşik uygunluk fonksiyonu:
$$J = w_f \hat{F} + w_s \hat{S} + w_c \hat{C} - w_r \hat{R} - w_e \hat{E} - w_o \hat{O} - w_d \hat{D}$$

Burada normalize edilmiş terimler:
1. $\hat{F} \in [0, 1]$: Yangın alev kanıtı skoru
2. $\hat{S} \in [0, 1]$: Duman kanıtı skoru
3. $\hat{C} \in [0, 1]$: Hücrenin keşif değeri (taranmamış hücreler için 1.0)
4. $\hat{R} \in [0, 1]$: Risk ve kısıt cezası (NFZ sınırına yakınlık)
5. $\hat{E} \in [0, 1]$: Hedefe ulaşım enerji tüketim tahmini
6. $\hat{O} \in [0, 1]$: Diğer drone'larla gereksiz ayak izi örtüşme cezası
7. $\hat{D} \in [0, 1]$: Drone'un mevcut konumundan olan mesafe cezası

Ağırlık vektörü: $w = [0.35, 0.15, 0.25, 0.05, 0.08, 0.07, 0.05]$.

### 3.2 Goal Attainment Minimax Formülasyonu
Verilen operasyonel hedef vektörü $g$ için:
$$\min \alpha \quad \text{subject to} \quad f_j(x) - g_j \le w_j \alpha, \quad \forall j \in \{1, \dots, m\}$$

---

## 4. Fiziksel Drone 3D-PSO Kinematiği

### 4.1 Adaptif Atalet ve Katsayılar [SIMULATED]
$$v_i(t+1) = \omega(t) v_i(t) + c_1(t) r_1 (p_{best, i} - x_i(t)) + c_2(t) r_2 (g_{best} - x_i(t)) + F_{rep, i}$$
$$x_i(t+1) = x_i(t) + v_i(t+1) \Delta t$$

* Atalet katsayısı: $\omega(t) = \omega_{max} - (\omega_{max} - \omega_{min}) \frac{t}{T_{max}}$, $\omega_{max}=0.85$, $\omega_{min}=0.40$
* Bilişsel ve Sosyal katsayılar:
  $c_1(t) = 2.0 - 0.8 \frac{t}{T_{max}}$ (Erken aşamada keşif)
  $c_2(t) = 1.2 + 0.8 \frac{t}{T_{max}}$ (Geç aşamada işbirliği)

---

## 5. Çarpışma Önleme ve Ayrılma (APF) [THEORETICAL_BOUND]

Asgari güvenli mesafe $d_{safe} = 30.0\text{ m}$, etki menzili $d_0 = 50.0\text{ m}$:
$$F_{rep, ij} = \begin{cases}
k_{rep} \left(\frac{1}{d_{ij}} - \frac{1}{d_0}\right) \frac{1}{d_{ij}^2} \frac{r_i - r_j}{d_{ij}}, & d_{ij} < d_0 \\
0, & d_{ij} \ge d_0
\end{cases}$$

---

## 6. Batarya ve Enerji Modeli [MANUFACTURER_SPEC / SIMULATED]

* Nominal gerilim: $V_{nom} = 14.8\text{ V}$ (4S LiPo), Kapasite: $C = 5000\text{ mAh}$
* Toplam Enerji: $E_{total} = \frac{5000}{1000} \cdot 14.8 \cdot 3600 = 266,400\text{ J}$
* Güç sarfiyatı: $P_{hover} = 220\text{ W}$, $P_{cruise} = 180\text{ W}$ ($v = 12\text{ m/s}$)
* Birim mesafe enerjisi: $e_{dist} = \frac{P_{cruise}}{v} = \frac{180}{12} = 15\text{ J/m}$
* **Otonom RTL Kapısı:**
  $$E_{remain} \le d_{home} \cdot 15\text{ J/m} + 30\text{ s} \cdot 220\text{ W} + 0.20 \cdot E_{total}$$
  Eşitsizlik sağlandığı anda drone otonom olarak üsse dönüşe zorlanır.
