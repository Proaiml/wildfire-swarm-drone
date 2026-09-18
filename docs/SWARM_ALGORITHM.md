# PyreSwarm - Sürü Arama Algoritması ve Çoklu Çekici Dinamiği (Swarm Algorithm)

## 1. Algoritma Genel Mantığı

Geleneksel PSO formülleri doğrudan fiziksel drone üzerinde çalıştırıldığında iki temel felakete yol açar:
1. **Fiziksel Kısıt İhlalleri:** Sonsuz ivme, yasaklı hava sahasına girme, aşırı hız ve bataryanın biterek drone'un düşmesi.
2. **Sürü Çöküşü (Swarm Collapse):** Tek bir yangın bulunduğunda tüm sürünün tek bir noktaya yığılması ve diğer ikincil yangınların tamamen gözden kaçması.

PyreSwarm bu sorunları aşağıdaki kapalı çevrim mimari ile çözer:

```text
[Kamera Gözlemi] ──> [Füzyon & Incident] ──> [Çeşitlilik & Tabu Yöneticisi]
                                                        │
[Güvenlik Düzlemi] <── [3D-PSO Aday Waypoint] <── [Çok Amaçlı Uygunluk]
        │
[Otopilot & DroneAdapter] ──> [Fiziksel / Simüle Uçuş]
```

---

## 2. Sürü Çöküşünü Önleme (Anti-Collapse & Multi-Attractor)

### 2.1 Çeşitlilik Metriği (Swarm Diversity) [THEORETICAL_BOUND]
Sürünün anlık uzamsal yayılımı:
$$D(t) = \frac{1}{|S_{air}|} \sum_{i=1}^{|S_{air}|} \sqrt{(x_i - \bar{x})^2 + (y_i - \bar{y})^2}$$

Eğer $D(t) < 60\text{ m}$ olursa, sürü tehlikeli biçimde kümelenmiş sayılır ve bilişsel keşif katsayısı $c_1$ anında $\%50$ artırılır.

### 2.2 Tabu Çemberi (Taboo Masking)
Bir yangın `CONFIRMED` statüsüne geçtiğinde:
* En yakın en fazla $K = 2$ drone yangına doğrulama/gözlem (`MONITORING`) göreviyle atanır.
* Sürünün geri kalan $N - K$ drone'u için bu yangın koordinatı etrafında $R_{taboo} = 150\text{ m}$ çapında dinamik tabu alanı oluşturulur.
* Atanmamış drone'ların uygunluk fonksiyonunda bu yangın maskelenir; drone'lar henüz taranmamış diğer sektörlere yönlendirilir.

---

## 3. Dinamik Sürü Üyeliği (Dynamic Swarm Join)

Operasyon ortasında yeni bir drone katıldığında:
1. **JOIN_REQUEST:** İstemci kimlik ve yetenek parametrelerini sunar.
2. **Authentication:** Gizli belirteç (token) doğrulaması.
3. **Capability Discovery:** Hız sınırları, kamera FOV, termal sensör, batarya kontrolü.
4. **Health Validation:** Batarya $\ge \%25$, GPS kilitli.
5. **Swarm Registration:** Tekil kimlik kontrolü (duplicate rejection).
6. **Initial Assignment:** Sürünün en az taranmış sektörüne ilk otonom hedef atanır.
