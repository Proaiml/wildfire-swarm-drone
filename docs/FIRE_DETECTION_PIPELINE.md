# PyreSwarm - Yangın Algılama ve Gözlem Hattı (Fire Detection Pipeline)

## 1. Model Mimarisi ve Karakteristiği [MEASURED]

Platform, yangın ve duman tespiti için PyTorch / Ultralytics tabanlı özelleştirilmiş YOLOv8 mimarisini kullanır:
* **Model Dosyası:** `best.pt`
* **Toplam Katman:** 130
* **Parametre Sayısı:** 3,011,238 (3.01 Milyon)
* **Hesaplama Yükü:** 8.19 GFLOPs (FP32)
* **Çıktı Sınıfları:** `0: smoke` (Duman), `1: fire` (Alev)
* **İnferans Cihazı:** CUDA GPU (Fallback: CPU)

---

## 2. İğne Deliği (Pinhole) Işın İzleme (Ray-Casting GPS İzdüşümü)

Kamera görüntüsündeki her bir nesne sınırlayıcı kutusunun (bounding box) piksel merkezi $(p_x, p_y)$ için zemin GPS koordinatı analitik pinhole ray-casting ile hesaplanır:

1. **Açısal Sapmalar:**
   $$\theta_x = \left(\frac{p_x - W/2}{W/2}\right) \cdot \frac{HFOV}{2}$$
   $$\theta_y = \left(\frac{H/2 - p_y}{H/2}\right) \cdot \frac{VFOV}{2}$$
2. **Kamera Koordinatlarında Metrik Sapmalar:**
   $$\Delta x_{cam} = h \cdot \tan(\theta_x)$$
   $$\Delta y_{cam} = h \cdot \tan(\theta_y)$$
3. **Drone Pusula Açısı (Yaw $\psi$) ile Zemin Rotasyonu:**
   $$\begin{bmatrix} \Delta x_{ground} \\ \Delta y_{ground} \end{bmatrix} = \begin{bmatrix} \cos\psi & \sin\psi \\ -\sin\psi & \cos\psi \end{bmatrix} \begin{bmatrix} \Delta x_{cam} \\ \Delta y_{cam} \end{bmatrix}$$
4. **WGS84 Koordinatına Ekleme:**
   $$\text{Lat}_{fire} = \text{Lat}_{drone} + \frac{\Delta y_{ground}}{111139.0}$$
   $$\text{Lon}_{fire} = \text{Lon}_{drone} + \frac{\Delta x_{ground}}{111139.0 \cdot \cos(\text{Lat}_{drone})}$$

---

## 3. Tespitten olaya (web hub'ı)

* **Güven eşiği:** Model 0.25 üstü güvenli kutuları döndürür (`core/fire_detector.py`).
* **Aday olay:** Her tespitin yer konumu bir **aday olaya** dönüşür. 90 m içindeki tespitler aynı olaya birleşir; olayın güveni en yüksek tespitinki olur, tespit sayısı artar (`candidate_merge_m`).
* **İnceleme:** Yeni aday olaya en yakın iki drone 30 saniye boyunca alçalıp bakar; diğerleri aramaya devam eder.
* **Teyit operatördedir:** Hub hiçbir olayı kendi kendine teyit etmez. Operatör *Teyit et*, *Reddet* ya da *Tamamlandı* der. Teyit edilen olayın 100 m çevresinde yeni skor bastırılır; reddedilen ya da tamamlanan olayın yerinde 60 saniye sonra yeni bir aday oluşabilir.
* **Kare ve konum aynı andan:** Konum hesabı, karenin çekildiği andaki drone pozuyla yapılır (dönüşte burun yönü değişse bile).

**Ölçülen konum hatası:** Tatbikat kamerasında (yangın karede gerçek yerinde çizilir) 35–80 m irtifada ortanca 1–3 m, en kötü 17 m. ArduPilot SITL denemesinde gerçek uçuş dinamiğiyle 7.8–12.7 m. Gerçek kamerada kalibrasyon, gimbal açısı ve arazi eğimi bu hatayı artırır.

Önceki `src/` mimarisindeki zamansal füzyon motoru (8 s pencere, en az 3 ardışık gözlem) web hub'ının kullandığı yol değildir.
