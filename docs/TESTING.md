# PyreSwarm — Testler

## Çalıştırma

```powershell
py -3.11 -m pytest tests -q          # 118 test, Windows / Python 3.11
node --check web/static/js/dashboard.js
```

Windows'ta tek tıkla: `TESTLERI_CALISTIR.bat`.

## Web hub'ının testleri

| Dosya | Kapsam |
|---|---|
| `test_field_integration.py` | Kapsama haritası, hibrit arama (şerit → kıvılcım konisi), rüzgâr altı risk bölgesi, sensöre göre şerit aralığı, iki inceleyicinin ayrılması; otopilot kontrolünün kontroller geçmeden reddi, PX4'ün kontrole alınmaması, pilot devralması, bağlantı kaybı, duraklat/RTL'in otopilota ulaşması; tatbikat süresi ve kamerası; kontrol API'si |
| `test_hub_regressions.py` | Sektör paylaşımı, kanıt incelemesi, geofence dolanması, batarya rezervi, MAVLink eksen dönüşümü ve iniş, API doğrulaması, çapraz kaynak reddi |
| `test_field_operations.py`, `test_api.py` | Üs konumu, drone ekleme/çıkarma, tek drone RTL ve iniş, simülasyonda düşük bataryada otomatik RTL, görev ve bölge API'leri, gönüllü kaydı |
| `test_swarm_integration.py` | Sürü yöneticisi, yangın modeli ve arama motorunun birlikte çalışması |
| `test_pso.py`, `test_geofence.py`, `test_detector.py`, `test_metrics_engine.py` | Arama motoru, bölge geometrisi, yangın modeli, görev metrikleri |
| `test_swarm_comparison.py`, `test_scale_and_performance.py` | Karşılaştırma altyapısı; 30 drone'da adım süresi |

## Eski `src/` katmanının testleri

`test_coordinates.py`, `test_fusion_and_incidents.py`, `test_safety_plane.py`, `test_battery_and_rth.py`, `test_communication_and_membership.py`, `test_e2e_acceptance.py`, `test_invariants.py` ve `test_fuzz_and_edge_cases.py` önceki mimarinin (`src/`) modüllerini sınar. `test_multi_algorithm_suite.py` eski 30 algoritmalık karşılaştırmayı (`benchmarks/`), `test_pdf_generation.py` eski PDF raporlarının üretimini sınar. Bu modüller web hub'ının uçuş yolunda kullanılmaz; testleri kodun bozulmadığını gösterir, hub'ın saha davranışını değil.

## Testlerin kapsamadığı

- **Gerçek otopilotla davranış:** ArduPilot SITL denemesiyle ayrıca sınanır (`tools/sitl/sitl_swarm_trial.py`, Docker gerekir). Sonuçlar [HUB_VALIDATION.md](HUB_VALIDATION.md) ve README'de.
- **Arama başarımı:** `scripts/compare_swarm_search.py` ile ölçülür; sonuçlar [SWARM_COMPARISON_TR.md](SWARM_COMPARISON_TR.md).
- **Gerçek araçla uçuş ve sahada yangın modeli doğruluğu:** henüz yapılmadı.
