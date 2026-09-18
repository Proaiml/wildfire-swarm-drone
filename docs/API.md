# PyreSwarm - REST & WebSocket API Dokümantasyonu (API Specification)

## 1. REST Uç Noktaları (Endpoints)

### `GET /api/v1/swarm`
Sürünün genel durumunu, aktif drone'ları ve en iyi yangın koordinatını döndürür.
```json
{
  "active": true,
  "drones_count": 5,
  "gbest": {
    "lat": 37.052,
    "lon": 28.322,
    "alt": 65.0,
    "fitness": 0.92
  }
}
```

### `POST /api/v1/swarm/start`
Otonom yangın arama görevini başlatır.

### `POST /api/v1/swarm/pause`
Görevi duraklatır (drone'lar havada sabit kalır / loiter).

### `POST /api/v1/swarm/rtl`
Tüm sürüye kalkış noktasına otonom geri dönüş (RTL) emri iletir.

### `POST /api/v1/drones/join`
Canlı sürüye yeni bir drone (gönüllü veya yedek) ekler.
```json
{
  "pilot_name": "Ahmet Y.",
  "lat": 37.048,
  "lon": 28.318,
  "alt": 30.0
}
```

### `POST /api/v1/zones/close`
Kullanıcı veya operatör tarafından harita üzerinde çizilen poligonu yasaklı/dışlanan bölge olarak kaydeder.

### `GET /api/v1/metrics`
Operasyonel süre, taranan km², doğrulanan yangın sayısı ve batarya tüketim raporunu döndürür.

---

## 2. WebSocket Akışı (Streaming)
* **URL:** `ws://localhost:8000/ws/telemetry`
* **İçerik:** Her drone'un lat, lon, alt, hız, batarya ve anlık alev/duman skoru gerçek zamanlı olarak (4 Hz) GCS arayüzüne basılır.
