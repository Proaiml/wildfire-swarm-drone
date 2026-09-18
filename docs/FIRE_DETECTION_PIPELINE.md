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

## 3. Uzamsal-Zamansal Kanıt Füzyonu (Fusion Engine)

* **Zamansal Pencere:** $T = 8.0\text{ saniye}$, Yarı-Ömür Sönümlenmesi: $T_{half} = 4.0\text{ saniye}$.
* **Asgari Ardışık Gözlem:** $N_{consecutive} \ge 3$ ve güven skoru $\ge 0.40$ olmadan alarm üretilmez.
* **Uzamsal Kümeleme:** $50\text{ metre}$ içindeki gözlemler tek bir kümede birleştirilir.
