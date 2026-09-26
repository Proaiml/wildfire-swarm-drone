# PyreSwarm — HTTP ve WebSocket API

Sunucu `http://127.0.0.1:8000` adresinde çalışır (`web/app.py`). İstek gövdeleri JSON'dur; tanımlanmamış alan içeren istekler reddedilir (`extra="forbid"`). Başka bir kaynaktan (Origin) gelen değiştirici istekler 403 ile reddedilir. Arayüzdeki her düğme aşağıdaki uç noktalardan birini çağırır.

## Durum ve canlı akış

| Yöntem | Yol | Ne yapar |
|---|---|---|
| GET | `/api/swarm/state` | Filo, roller, olaylar, kapsama haritası, rüzgâr, arama alanı ve hazırlık durumu |
| WS | `/ws/telemetry` | Aynı durum nesnesi, saniyede 4 kez |
| GET | `/api/video_feed/{drone_id}` | Drone'un işaretli kamera karesi (MJPEG) |
| GET | `/api/mission/export_report` | Olay raporu (JSON) |
| GET | `/api/metrics/calculate` | Görev metrikleri |

## Görev

| Yöntem | Yol | Gövde | Ne yapar |
|---|---|---|---|
| POST | `/api/mission/start` | — | Görevi başlatır; simülasyon drone'ları ve hub kontrolündeki otopilotlar kalkar |
| POST | `/api/mission/pause` | — | Drone'lar yerinde bekler (otopilotlara sıfır hız) |
| POST | `/api/mission/rtl` | — | Tüm filo eve döner |
| POST | `/api/mission/kind` | `{"kind": "fire" \| "sar"}` | Yangın keşfi / arama-kurtarma |
| POST | `/api/mission/set_aoi` | `{min_lat, max_lat, min_lon, max_lon}` | Arama alanı |
| POST | `/api/mission/set_wind` | `{"speed_ms": 5, "direction_deg": 225}` | Rüzgâr (rüzgârın **estiği** yön, 0 = kuzeyden) |
| GET / POST | `/api/mission/base` | `{name, lat, lon, ...}` | Üs konumu |
| POST | `/api/geofence/add` | `{name, zone_type, coordinates: [[lat, lon], ...]}` | Yasak bölge / göl / kapatılan alan (en az 3 köşe) |
| DELETE | `/api/geofence/{zone_id}` | — | Bölgeyi kaldırır |

## Filo ve otopilot kontrolü

| Yöntem | Yol | Ne yapar |
|---|---|---|
| POST | `/api/swarm/add_drone` | Drone ekler: `drone_type` = `simulated`, `volunteer` ya da `mavlink` |
| GET | `/api/drone/{id}/preflight` | Uçuş öncesi kontrol listesi (`id`, `label`, `ok`, `detail`) |
| POST | `/api/drone/{id}/control` | `{"enable": true}` ile hub kontrolüne alır (kontroller geçerse), `false` ile bırakır |
| POST | `/api/drone/{id}/rtl` · `/land` | Tek drone'u eve döndürür / indirir |
| DELETE | `/api/drone/{id}` | Filodan çıkarır (otopilotun hub bağlantısı kapanır) |

MAVLink otopilot ekleme örneği:

```json
POST /api/swarm/add_drone
{
  "drone_type": "mavlink",
  "drone_id": "ARDU-1",
  "connection_string": "tcp:127.0.0.1:5760",
  "target_system": 1,
  "camera_url": null,
  "synthetic_camera": false,
  "capabilities": {"max_speed_ms": 8, "search_altitude_m": 60, "max_altitude_m": 120, "camera_hfov_deg": 84}
}
```

Otopilot 10 saniye içinde heartbeat göndermezse yanıt 502'dir. Başarılı eklemede araç yalnızca izlenir; hareket komutu için `/control` çağrısı ve geçen uçuş öncesi kontroller gerekir.

## Olaylar ve tatbikat

| Yöntem | Yol | Ne yapar |
|---|---|---|
| POST | `/api/incidents/report` | Operatör ihbarı (bilinen konum) |
| POST | `/api/incidents/{id}/status` | `{"status": "confirmed" \| "dismissed" \| "resolved"}` |
| POST | `/api/mission/scenario/target` | Gizli tatbikat hedefi: `{lat, lon, intensity, delay_seconds}` |
| GET | `/api/mission/scenario/truth` | Tatbikat hedefleri ve tespit süreleri (yalnızca operatör ekranı için) |

## Gönüllü / başka marka drone köprüsü

| Yöntem | Yol | Ne yapar |
|---|---|---|
| POST | `/api/swarm/register_volunteer` | Kayıt; dönen `VOLUNTEER_...` kimliği köprüye verilir |
| POST | `/api/volunteer/{id}/telemetry` | Gerçek ölçüm: `{captured_at, lat, lon, alt, battery, ...}` (en az 1 Hz) |
| POST | `/api/volunteer/{id}/observation` | Aynı anda çekilmiş kamera karesi + poz (JPEG base64) |
| GET | `/api/volunteer/{id}/guidance` | Pilota yön/hız/irtifa önerisi (`advisory_only: true`) |

Ayrıntılar ve örnek istemci: [DRONE_INTEGRATION_TR.md](DRONE_INTEGRATION_TR.md), `examples/volunteer_bridge_client.py`.

## Karşılaştırma kayıtları

`GET /api/benchmarks/results` ve `GET /api/benchmarks/runs` eski arama karşılaştırmasının kayıtlarını döndürür (`/static/benchmark.html` tekrar oynatıcısı). Güncel karşılaştırma: [SWARM_COMPARISON_TR.md](SWARM_COMPARISON_TR.md).
