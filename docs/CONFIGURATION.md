# PyreSwarm - Konfigürasyon ve Parametre Yönetimi (Configuration)

Tüm platform parametreleri doğrulanmış (validated) ve modüler biçimde yönetilir. Kod içinde sihirli sayılar (magic numbers) yasaktır.

## 1. Temel Konfigürasyon Bölümleri

### 1.1 Algılayıcı (Detector)
* `model_path`: YOLO model ağırlıkları (`best.pt`)
* `conf_threshold`: Asgari güven eşiği (Varsayılan: `0.25`)
* `device`: `cuda` veya `cpu`

### 1.2 Güvenlik ve Uçuş (Safety & Flight)
* `min_altitude_m`: Asgari irtifa (Varsayılan: `25.0 m`)
* `max_altitude_m`: Azami irtifa (Varsayılan: `120.0 m`)
* `max_speed_ms`: Azami uçuş hızı (Varsayılan: `14.0 m/s`)
* `safe_separation_m`: Asgari güvenli drone ayrılma mesafesi (Varsayılan: `30.0 m`)

### 1.3 Batarya ve RTL (Battery & Failsafe)
* `nominal_capacity_mah`: Batarya kapasitesi (Varsayılan: `5000 mAh`)
* `nominal_voltage`: `14.8 V` (4S LiPo)
* `safety_margin_percent`: RTL rezerv yüzdesi (Varsayılan: `%20.0`)
* `critical_battery_threshold`: Acil iniş eşiği (Varsayılan: `%12.0`)

### 1.4 Çok Amaçlı PSO (Swarm Optimizer)
* `w_max`, `w_min`: Adaptif atalet sınırları (`0.85`, `0.40`)
* `c1_initial`, `c2_initial`: Bilişsel ve sosyal katsayı başlangıçları (`2.0`, `1.2`)
* `max_drones_per_incident`: Yangın başına azami görevlendirilecek drone (Varsayılan: `2`)
* `taboo_radius_meters`: Yangın onaylandığında atanmamış drone'lar için tabu yarıçapı (`150.0 m`)
