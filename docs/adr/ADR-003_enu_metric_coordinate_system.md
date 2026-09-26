> **Tarihsel belge.** Bu belge önceki `src/` tabanlı mimariyi anlatır. Web hub'ı bugün `core/`, `hardware/` ve `web/` üzerinden çalışır. Güncel kullanım: [Saha kılavuzu](../SAHA_KILAVUZU_TR.md) · güncel doğrulama: [HUB_VALIDATION](../HUB_VALIDATION.md) · genel bakış: [README](../../README.md). Buradaki başarım ve doğrulama ifadeleri güncel sürüm için kanıt sayılmaz.

# ADR-003: Yerel Metrik ENU Teğet Düzlem Koordinat Sistemi

## Durum
KABUL EDİLDİ (ACCEPTED) - Versiyon 0.1.0

## Bağlam
WGS84 coğrafi koordinatları (enlem/boylam derece) üzerinde doğrudan Öklid mesafesi hesaplamak, kutuplara ve ekvatora olan mesafeye göre açısal bozulmalara ($1^\circ \text{ lon} = 111.139 \cdot \cos(\phi) \text{ km}$) neden olur. Bu durum drone hız vektörleri, APF çarpışma önleme kuvvetleri ve PSO optimizasyonunu bozar.

## Karar
Tüm kinematik, optimizasyon, APF ayrılma ve hücre kapsama hesaplamaları operasyon merkezine (üs) göre tanımlı **Yerel Metrik ENU (East-North-Up)** koordinat çerçevesinde (metre cinsinden) yürütülür.
- WGS84 Elipsoid formülleri ile dönüşüm sağlanır (`geodetic_to_enu` ve `enu_to_geodetic`).
- Operasyon yarıçapı < 100 km için teğet düzlem projeksiyon hatası <%0.05'tir.

## Sonuçlar
- **Olumlu:** Fiziksel hızlar (m/s), mesafeler (m) ve kuvvetler (N) doğru metrik birimlerde hesaplanır.
- **Harita Arayüzü:** Dış dünya ve Leaflet/Google Maps ile WGS84 formatında haberleşilir.
