# ADR-002: Olay Güdümlü Dağıtık İletişim Veriyolu (MessageBus)

## Durum
KABUL EDİLDİ (ACCEPTED) - Versiyon 0.1.0

## Bağlam
Dağıtık sürü sisteminde drone telemetrileri, algılama olayları ve görev güncellemeleri tek bir global Python sözlüğü üzerinden paylaşılamaz. Bu durum race condition, thread kilitlenmeleri ve dağıtık ölçekleme sorunlarına yol açar.

## Karar
MQTT topic yapısını standart kabul eden olay güdümlü `MessageBus` soyutlaması oluşturuldu:
- `InMemoryBus`: Yerel simülasyon, birim testler ve tek sunucu için sıfır gecikmeli pub-sub.
- `WebSocketBus`: Web arayüzü ve GCS için çift yönlü telemetri köprüsü.
- Standart Topic Yapısı:
  - `swarm/{swarm_id}/drone/{drone_id}/telemetry`
  - `swarm/{swarm_id}/drone/{drone_id}/detection`
  - `swarm/{swarm_id}/incidents`
  - `swarm/{swarm_id}/mission`

## Sonuçlar
- **Olumlu:** Sürü bileşenleri gevşek bağlı (loosely coupled) hale geldi.
- **Haberleşme Kaybı:** `CommunicationLossHandler` ile kalp atışı takibi yapılarak kopan drone'lar swarm'ı kilitlemeden `DISCONNECTED` durumuna alınır.
