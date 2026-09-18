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

---

## 7. PDF Formatında Dokümantasyonlar

Sistemin tüm operasyonel ve akademik detayları yüksek çözünürlüklü iki PDF olarak derlenmiştir:
- 📄 **[PyreSwarm_Kullanim_Kilavuzu.pdf](PyreSwarm_Kullanim_Kilavuzu.pdf)**: Operasyonel adımlar, bölge kapatma, gönüllü katılımı ve MAVLink kurulumu.
- 📊 **[PyreSwarm_Matematiksel_Model_ve_Metrik_Raporu.pdf](PyreSwarm_Matematiksel_Model_ve_Metrik_Raporu.pdf)**: Koopman formülasyonu, Monte Carlo simülasyon grafikleri ve ampirik benchmark tabloları.

---

## 8. Testlerin Çalıştırılması

Sistemin matematiksel, algoritmik ve donanımsal 23 birim ve entegrasyon testini çalıştırmak için:
```bash
pytest tests/ -v
```
Test paketi şunları kapsar:
- `test_metrics_engine.py`: Arama teorisi, sensör geometrisi ve Monte Carlo testleri.
- `test_scale_and_performance.py`: 30 drone ölçeklenebilirlik ve adım gecikme testleri.
- `test_pdf_generation.py`: PDF bütünlük ve derleme testleri.
- `test_pso.py`: 3D PSO yakınsama, sosyal/bilişsel öğrenme ve çarpışma engelleme testleri.
- `test_detector.py`: `best.pt` ağırlıkları ile duman/alev çıkarımı ve zemin GPS ray-casting testleri.
- `test_geofence.py`: Kapatılan alanların sınır testleri ve APF itki vektörleri.
- `test_swarm_integration.py`: Sürü simülasyonu, hedef paylaşımı ve $gbest$ sıfırlama testleri.
- `test_api.py`: FastAPI REST ve WebSocket uç nokta testleri.
