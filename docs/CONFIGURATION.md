# PyreSwarm — Yapılandırma

## `config/mission_config.json`

Sunucu açılırken okunur. Arayüzden **Üs** değiştirilip "kalıcı kaydet" seçilirse bu dosyaya yazılır.

| Alan | Anlamı |
|---|---|
| `base_station` | Üssün adı, konumu ve irtifası; varsayılan filo buradan kalkar |
| `default_aoi` | Varsayılan arama alanı (`min_lat`, `max_lat`, `min_lon`, `max_lon`) |
| `wind` | `speed_ms` ve `direction_deg` (rüzgârın **estiği** yön, 0 = kuzeyden). Açılışta uygulanır; arayüzden değiştirilebilir |
| `presets` | Üs seçiminde hazır konumlar |

## Drone yetenekleri (her drone için)

Arayüzde **+ Ekle** formundan ya da API'de `capabilities` alanından verilir:

| Alan | Aralık | Varsayılan | Etkisi |
|---|---|---|---|
| `max_speed_ms` | 1–14 | 10 | Hız sınırı ve sektör payı |
| `search_altitude_m` | 25–120 | 60 | Arama irtifası; kamera ayak izini belirler |
| `max_altitude_m` | 25–120 | 120 | İrtifa üst sınırı |
| `camera_hfov_deg` | 20–120 | 84 | Kamera yatay görüş açısı; şerit aralığını belirler |

## Arama motoru (`core/pso_engine.py`, `PSOConfig`)

Önemli varsayılanlar:

| Alan | Varsayılan | Anlamı |
|---|---|---|
| `search_strategy` | `"hybrid"` | `hybrid`: şerit tarama, yangın bilinince rüzgâr altı kıvılcım konisine dönüş · `lanes`: yalnız şerit · `adaptive`: en eski görülen hücreler |
| `sensor_radius_m` | `None` | Bilinirse şerit aralığı buna göre; yoksa irtifa ve görüş açısından hesaplanır |
| `ember_seconds` | 90 | Kıvılcım menzili = rüzgâr hızı × bu süre (150–800 m arasında) |
| `ember_half_angle_deg` | 35 | Kıvılcım konisinin yarı açısı |
| `coverage_cell_m` | 30 | "Son görülme" haritasının hücre boyu |
| `candidate_merge_m` | 90 | Bu mesafedeki tespitler aynı olaya birleşir |
| `inspect_altitude` | 35 | İnceleme irtifası |
| `inspect_standoff_m` | 22 | İki inceleyicinin olaydan uzaklığı (karşı yanlarda) |
| `inspect_alt_step_m` | 10 | İkinci inceleyicinin irtifa farkı |
| `safe_drone_distance_m` | 30 | Hedef en az drone ayrılması |

## Otopilot kontrolü (`hardware/mavlink_drone.py`)

| Sabit | Değer | Anlamı |
|---|---|---|
| `HEARTBEAT_TIMEOUT_S` | 3 | Bu süre heartbeat gelmezse bağlantı kopmuş sayılır ve hub komutu keser |
| `MIN_GPS_SATS` | 6 | Hub kontrolü için en az uydu |
| `MIN_BATTERY` | 40 | Hub kontrolü için en az batarya (%) |

Otopilot tarafında önerilen ayarlar (ArduPilot): `FS_GCS_ENABLE=1`, `FS_GCS_TIMEOUT=5`, uygun `RTL_ALT`, `FENCE_ENABLE=1`, her araçta farklı `SYSID_THISMAV`. Ayrıntı: [SAHA_KILAVUZU_TR.md](SAHA_KILAVUZU_TR.md).

## Yangın modeli

`best.pt` (YOLO, sınıflar: `fire`, `smoke`) depo kökünde olmalıdır. Yüklenemezse arayüz bunu bildirir ve kamera tespiti kapalı kalır.
