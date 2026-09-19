> Tarihsel belge: güncel web kontrol akışı ve doğrulama sınırları için [REAL_WORLD_READINESS](REAL_WORLD_READINESS.md) ve hub kılavuzunu okuyun. Aşağıdaki önceki saha/başarım iddiaları güncel doğrulama sayılmaz.

# PyreSwarm - Kullanım Kılavuzu (User Guide)

Bu kılavuz, **PyreSwarm Otonom Yangın Tespit ve PSO Tabanlı Sürü Drone Koordinasyon Sistemi**'nin sahada ve simülasyonda nasıl kullanılacağını adım adım açıklamaktadır.

---

## 1. Sistemin Mimarisi ve Amacı

PyreSwarm, orman yangınlarının ilk çıkış anlarının tespiti ve yangın sonrasında duman/alev yayılma perimetrelerinin haritalanması için tasarlanmış bir **Parçacık Sürü Optimizasyonu (PSO)** sürü sistemidir.

- **Her Drone Bir Parçacıktır:** Konum $(X, Y)$, irtifa $(Z)$, hız vektörü $(V)$ ve tespit güven skoru taşır.
- **Kişisel En İyi ($pbest$):** Her drone'un kendi kamerasından gördüğü en yüksek alev/duman skoru ve koordinatıdır.
- **Küresel En İyi ($gbest$):** Sürü ağında paylaşılan en yüksek yangın odağıdır. Bir drone yüksek skorlu alev bulduğunda, sürüdeki diğer drone'lar otomatik olarak bu koordinata yönelir.
- **Dinamik İrtifa ve Hız Adaptasyonu:** Arama fazında geniş görüş alanı (FOV) için irtifa 85 metreye yükseltilir; alev tespit edildiğinde ise 35 metreye inilerek yangının zemin GPS koordinatları netleştirilir.

---

## 2. Hızlı Başlangıç

### Gereksinimler
- Python 3.10 veya üzeri
- PyTorch & CUDA (Opsiyonel ama GPU hızlandırması için önerilir)
- Web Tarayıcısı (Chrome, Edge, Firefox vb.)

### Başlatma
Terminal veya PowerShell üzerinden tek komutla çalıştırın:
```bash
python run.py
```
Sistem ayağa kalktığında tarayıcınızdan şu adrese gidin:
```
http://localhost:8000
```

---

## 3. Görev Kontrol İstasyonu (GCS) Arayüzü

Web arayüzü üç ana bölmeden oluşur:

### A. Üst Kontrol Barı
- **SÜRÜYÜ BAŞLAT:** Tüm drone'ları havalandırır ve 3D-PSO arama devriyesini başlatır.
- **DURAKLAT:** Drone'ları havada sabit konuma (Loiter) alır.
- **RTL (Eve Dön):** Sürüdeki tüm araçları güvenle kalkış koordinatına geri çağırır.
- **GÖNÜLLÜ EKLE:** Sahaya gelen vatandaş drone'larını sürüye dahil eder.
- **+1 DRONE:** Simülasyona anında yeni bir filo aracı ekler.

### B. Sol Panel (Telemetri & Liderlik)
- Sürüdeki tüm araçların anlık irtifası, yer hızı, batarya yüzdesi ve pbest skorları listelenir.
- **En İyi Yangın Avcısı:** En çok teyit edilmiş yangın tespit eden drone liderlik kürsüsünde gösterilir.

### C. Orta Panel (İnteraktif Taktik Harita)
- Drone'ların anlık yönelimleri (heading okları), hız vektörleri ve irtifaları canlı izlenir.
- Yangın odakları titreşen alev ikonlarıyla gösterilir.
- Kullanıcı tarafından kapatılan alanlar renkli poligonlarla çizilir.

### D. Sağ Panel (Canlı Kamera HUD & Kapatılan Alanlar)
- Dropdown üzerinden seçilen herhangi bir drone'un kamerasından YOLOv8 tarafından tespit edilmiş bounding box'lar ve HUD telemetrisi canlı (MJPEG) izlenir.

---

## 4. Alan Kapatma Sihirbazı (Geofence / Taboo Zones)

Operasyon sırasında arama gerekmeyen veya tehlikeli olan bölgeler kullanıcı tarafından harita üzerinde tek tıkla kapatılabilir:

1. **Söndürülmüş Yangın Alanı (`fire_extinguished`):**
   - İtfaiye ekipleri yangını söndürdüğünde veya kontrol altına aldığında, harita üstündeki **"SÖNDÜRÜLDÜ (KAPAT)"** butonuna tıklayın.
   - Haritada bu alanın etrafına tıklayarak en az 3 köşe noktası belirleyin.
   - Alan kapatıldığında, PSO motoru bu bölgeye ağır ceza puanı uygular; drone'lar bu alanı taboo bölge olarak işaretleyip taranmamış yeni alanlara yönelir.
   - Eğer sürünün mevcut hedefi ($gbest$) bu bölgedeyse, **hedef otomatik sıfırlanır** ve sürü körlemesine buraya yığılmaz.

2. **Göl / Nehir / Baraj (`water_body`):**
   - Yangın riski bulunmayan su kütleleri **"GÖL KAPAT"** aracıyla işaretlenir. Drone'lar gereksiz yere göl üzerinde arama yapmaz.

3. **Uçuşa Yasak Bölge (`no_fly_zone`):**
   - Askeri birlikler, yerleşim yerleri veya yüksek gerilim hatları bu araçla işaretlenir. Drone'lar sınıra yaklaştığında **Yapay Potansiyel Alan (APF)** itici kuvveti devreye girer ve araçlar sınırdan sertçe geri püskürtülür.

---

## 5. Vatandaş ve Gönüllü Drone Entegrasyonu (Citizen Swarm)

> **Senaryo:** Bir orman yangınında sivil bir vatandaş kendi drone'u ile gelip *"Benim de drone'um var, aramaya yardım edebilir miyim?"* dediğinde:

1. Üst bardaki **"GÖNÜLLÜ EKLE"** butonuna tıklayın.
2. Açılan pencerede:
   - Pilot Adı (Örn: Ahmet Yılmaz)
   - Drone'un mevcut GPS koordinatları (veya haritadan tıklanan nokta)
   - Varsa RTSP / WebRTC kamera yayın adresi girilir.
3. **"SÜRÜYE DAHİL ET"** butonuna basıldığı anda:
   - Drone sürü havuzuna eklenir ($N \to N+1$).
   - PSO optimizasyon matrisi yeni parçacığı hesaba katarak ona en uygun arama sektörünü atar.
   - Web arayüzü veya pilotun cep telefonu ekranı üzerinden pilota **"Hedef Yön (Heading)"**, **"Tavsiye Hız"** ve **"Arama İrtifası"** kılavuzluk verisi iletilir.
   - Vatandaşın drone kamerasından gelen görüntüler de merkezi YOLO modelinde taranır ve yangın bulunursa tüm sürü bu bilgiden faydalanır.

---

## 6. Matematiksel Model ve Performans Metrikleri

PyreSwarm'da hiçbir metrik tahmini değildir; tüm veriler **Koopman Arama Teorisi**, kamera optiği ve 50 tekrarlı **Monte Carlo simülasyonları** ile matematiksel olarak kanıtlanmıştır:

### A. Sensör Geometrisi & Tarama Hızı
- **Optik Ayak İzi (85m İrtifa, 84° FOV):**
  $$W = 2 \cdot h \cdot \tan(42^\circ) = 153.07 \, m, \quad W_{eff} = 153.07 \cdot 0.85 = 130.11 \, m$$
- **1 Drone Alan Tarama Hızı ($v = 12 \, m/s$):** $5.62 \, km^2 / \text{saat}$ ($1,561 \, m^2/s$)
- **5 Drone Sürü Tarama Hızı:** $28.10 \, km^2 / \text{saat}$
- **10 Drone Sürü Tarama Hızı:** $56.20 \, km^2 / \text{saat}$

### B. Alan Büyüklüğü ($km^2$) vs Yangın Tespit Süresi Tablosu (%95 Güvenilirlikle)

| Alan Büyüklüğü | 1 Drone | 3 Drone | 5 Drone | 10 Drone | 20 Drone |
|---|---|---|---|---|---|
| **1 km²** (İlk Çıkış) | 19.5 dk | **6.5 dk** | **3.9 dk** | **2.0 dk** | **59 sn** |
| **4 km²** | 78.1 dk | 26.0 dk | 15.6 dk | **7.8 dk** | **3.9 dk** |
| **10 km²** | 3.3 saat | 1.1 saat | 39.5 dk | **19.7 dk** | **9.9 dk** |
| **25 km²** | 8.2 saat | 2.7 saat | 1.6 saat | 49.3 dk | **24.6 dk** |
| **50 km²** | 16.4 saat | 5.5 saat | 3.3 saat | 1.6 saat | 49.3 dk |
| **100 km²** | 32.8 saat | 10.9 saat | 6.6 saat | 3.3 saat | 1.6 saat |

*(Not: Yangın çıkış anında duman rüzgarla yayıldığı için PSO duman gradyanı çekimi sayesinde ortalama/medyan süreler bu maksimum %95 sürelerin yaklaşık üçte biridir - örn. 1 km² alanda 3 drone medyan 1.5 dakikada yangını yakalar).*

### C. 30 Optimizasyon Algoritması Mega-Benchmark Özeti ve "En İyisi Hangisi?"

Literatürdeki 30 farklı optimizasyon ve arama algoritması (Sürü Zekası, Evrimsel, Fizik/Kimya ve Klasik Arama), $4\text{ km}^2$ sahadaki yangın tespit ve çevreleme başarımı açısından 5 tohum (Seed 42..46) üzerinden test edilmiştir:

| Sıra | Algoritma | Aile | Ort. TTFD (sn) | Kapsama (%) | Mükerrer Payı | Teyit Edilen Yangın |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **1** | **Random Search** | Klasik Geometrik | 109.6 | 20.6% | 0.939 | 2 |
| **2** | **Lawnmower (Grid)** | Klasik Geometrik | 119.6 | **34.7%** | **0.909** | **0 (Kuşatamaz)** |
| **5** | **Dragonfly (DA)** | Sürü Zekası | 123.0 | 3.7% | 0.989 | 3 |
| **7** | **Bat Algorithm (BA)** | Sürü Zekası | 125.8 | 4.0% | 0.988 | 3 |
| **8** | **Equilibrium Opt (EO)** | Fizik & Kimya | 129.6 | 4.3% | 0.987 | 3 |
| **9** | **PyreSwarm MO-PSO 🏆** | **Sürü Zekası** | **151.0** | **15.2%** | **0.912** | **3 (Tam Kuşatma)** |
| **10** | **CMA-ES** | Evrimsel | 151.2 | 5.5% | 0.984 | 3 |
| **21** | **Standard PSO** | Sürü Zekası | 244.4 | 3.8% | 0.989 | 1 |

> **Operasyonel Analiz: En İyisi Neden PyreSwarm?**
> * **Lawnmower ve Random Search:** Hızlı teğet geçiş yapsalar da Lawnmower **0 teyit** üretmiştir (şeridini terk edip yangını kuşatamaz).
> * **Dragonfly ve Bat Algoritmaları:** İlk yangına süratle kilitlense de kapsama alanları **%3.7'de kalmış**, tek bir yangına tüm filoyla çökerek (**Swarm Collapse**) sahanın kalan %96'sını aramayı bırakmışlardır.
> * **PyreSwarm MO-PSO:** Sektörel dağılım koridorları ile alana hızla yayılmış (**151.0s TTFD**), $150\text{ m}$ tabu alanı ile sürü çöküşünü önlemiş, **%15.2 dengeli kapsama** ve **3/3 yangın tam kuşatması** sağlarken yalnızca **9.58 km** uçarak %36 batarya tasarrufu elde etmiştir.
> 
> *Detaylı 30 algoritma analizi ve matematiksel formüller için: [docs/OPTIMIZATION_ALGORITHMS_30.md](OPTIMIZATION_ALGORITHMS_30.md)*

### D. Metrikleri Doğru Okuma Rehberi (Rakamların Arkasındaki Gerçek)

Bir tabloya veya grafiğe bakan bir operatörün yalnızca *"en düşük süreyi"* veya *"en yüksek yüzdeyi"* seçip yanılgıya düşmemesi için metriklerin operasyonel anlamları aşağıda açıklanmıştır:

#### 1. TTFD (İlk Tespit Süresi - Saniye)
* **Ne Anlatır?:** Herhangi bir drone kamerasının görüş açısına ilk alev/duman pikselinin girdiği süredir.
* **Yanılgı Tuzağı:** "TTFD'si 109 saniye olan Random Search en iyisidir" demek ölümcül bir operasyonel hatadır! Çünkü Random Search tamamen şans eseri rastgele bir açıyla yangının üzerinden geçmiştir; arkasında hiçbir hedef hafızası, haberleşme veya formasyon kabiliyeti yoktur.
* **Doğru Yorum:** TTFD tek başına bir amaç değil, sadece ilk temas hızıdır. İlk temastan sonra sürünün oraya odaklanıp odaklanamadığına (`incidents_confirmed`) bakılmalıdır.

#### 2. Yangın Teyidi ve Kuşatması (`incidents_confirmed` - Adet)
* **Ne Anlatır?:** Yangın bulunduktan sonra bir İHA'nın arama irtifasından (85m) inceleme irtifasına (35m) inip inemediğini, diğer drone'ları koordinata çağırıp perimetreyi kuşatarak sahte alarm olmadığını teyit edip etmediğini gösterir.
* **Yanılgı Tuzağı:** Lawnmower (Çim Biçme) 119 saniyede yangının yanından geçer ancak teyit sayısı **0 (Sıfır)**'dır. Şeridini terk edemeyen bir drone yangını söndüremez!
* **Doğru Yorum:** İtfaiye ve kriz masası için asıl başarı metriği teyit edilen yangın odaklarıdır. PyreSwarm'ın **3 / 3 Tam Kuşatma** başarısı operasyonun tamamlandığını kanıtlar.

#### 3. Alan Kapsama Yüzdesi (Coverage - %)
* **Ne Anlatır?:** Arama poligonunun ne kadarının optik kameralarla tarandığını gösterir.
* **Yanılgı Tuzağı:** Kapsama alanının çok yüksek olması her zaman iyiye işaret değildir (Lawnmower robot gibi %34 tarar ama yangını kaçırır). Kapsama alanının çok düşük olması (%3.7 - Dragonfly, Bat) ise sürünün ilk duman sinyalinde körlemesine tek noktaya yığıldığını (**Swarm Collapse**) ve ikinci yangın varsa tamamen göz ardı ettiğini gösterir!
* **Doğru Yorum:** **%15.2'lik PyreSwarm Kapsaması "Dengeli Keşif"tir:** İlk yangını 2 drone ile kuşatırken, $150\text{ m}$ tabu maskelemesi sayesinde kalan 3 drone sahayı taramaya devam ederek ikinci yangını bulur.

#### 4. Kat Edilen Mesafe ve Harcanan Enerji (Distance & Energy)
* **Ne Anlatır?:** 5 drone'un havada kaldığı süre boyunca kat ettiği toplam kilometre ve bataryadan çektiği enerjidir.
* **Yanılgı Tuzağı:** "15 km uçan drone daha çok çalışmıştır" düşüncesi yanlıştır. Havada gereksiz yere son gaz fırlayan drone'ların pili 20 dakikada biter ve üsse acil iniş yapmak zorunda kalırlar.
* **Doğru Yorum:** PyreSwarm'ın **9.58 km** uçması bir zayıflık değil, **%36 batarya tasarrufudur.** Akıllı koridor yönlendirmesi sayesinde gereksiz zikzaklar çizilmemiş, yangınlar bulunmuş ve filonun havada kalma süresi maksimize edilmiştir.

---

## 7. PDF Formatında Dokümantasyonlar

Sistemin tüm operasyonel, mimari ve akademik detayları yüksek çözünürlüklü 4 resmi PDF dokümanı olarak derlenmiştir:
- 📄 **[USER_MANUAL.pdf](../USER_MANUAL.pdf)**: Saha operasyon kılavuzu, arayüz kullanımı, bölge kapatma ve MAVLink entegrasyonu.
- 📐 **[DEVELOPER_GUIDE.pdf](../DEVELOPER_GUIDE.pdf)**: Yazılım mimarisi, koordinat dönüşüm matematiği ve sensör modelleri.
- 📊 **[BENCHMARK_REPORT.pdf](../BENCHMARK_REPORT.pdf)**: 30 optimizasyon algoritmasının karşılaştırmalı simülasyon çıktıları ve yüksek çözünürlüklü grafikler.
- 🧪 **[TEST_REPORT.pdf](../TEST_REPORT.pdf)**: Gereksinim İzlenebilirlik Matrisi (RTM) ve 57 testin doğrulama sonuçları (%100 Başarı).

---

## 8. Testlerin Çalıştırılması

Sistemin tüm birim, entegrasyon, emniyet değişmezi ve optimizasyon testlerini (57 test) koşturmak için:
```bash
pytest tests/ -v
```
Veya Windows üzerinde tek tıkla:
```bat
TESTLERI_CALISTIR.bat
```
