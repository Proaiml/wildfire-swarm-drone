# PyreSwarm — ortak yangın keşfi ve arama-kurtarma merkezi

PyreSwarm, farklı kapasitedeki drone'ların arama sektörlerini paylaşan bir web görev merkezidir. Bu sürüm **simülasyon uçuşunu**, **gerçek telemetriye dayalı gönüllü pilot rehberliğini** ve **MAVLink telemetri gözlemini** destekler. Fiziksel otonom sürü uçuşu doğrulanmış veya etkin değildir.

## Başlatma

Windows: `BASLAT.bat` veya proje dizininde:

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 run.py
```

Arayüz: http://127.0.0.1:8000. Sunucu varsayılan olarak yalnızca bu bilgisayarda dinler. Mevcut `.venv` eksik olabilir; bu çalışmada doğrulanan ortam Windows üzerindeki Python 3.11'dir.

## Görev akışı

1. **Yangın keşfi** veya **Arama ve kurtarma** seçin. Mod değiştirmeden önce duraklatın; eski modun olayları temizlenir. Gerekliyse önce rapor indirin.
2. Arama alanını iki köşeyle belirleyin; yasak/göl alanını en az üç köşeyle çizip tamamlayın.
3. Filoya drone eklerken hız, arama irtifası, azami irtifa ve kamera görüşünü tanımlayın.
4. Başlatın. Kapasite ağırlıklı sektörlerde sürekli tarama yapılır; pozitif kanıt en fazla iki drone'a inceleme görevi verir. İnceleme 30 saniye ile sınırlıdır; kalan filo taramaya devam eder.
5. Şüpheli olayı operatör teyit eder, reddeder veya tamamlar. Alanı arama dışına almak ayrı işlemdir.
6. **Tatbikat hedefi** sensör tarafından görülene kadar gizlidir. **İhbar** operatörün bilinen bir konum bildirimidir; otomatik doğrulama değildir.

## Gerçek katılımın sınırları

| Katılım | Bu sürümdeki davranış |
|---|---|
| Simülasyon | İvme/hız sınırlı hareket, sektör tarama, bilinen poligonlardan dolanma, RTL/iniş, basit batarya modeli |
| Gönüllü / herhangi bir marka | Harici köprü gerçek konum gönderir; hub pilota rota, hız ve irtifa önerir. Eski telemetriyle yönlendirme verilmez. |
| MAVLink | PX4/ArduPilot bağlantı ve telemetri sürücüsü vardır. Webden fiziksel uçuş komutları kapalıdır. |
| DJI ve diğer kapalı ekosistemler | Üretici SDK'sına uygun köprü gerekir; evrensel tak-çalıştır bağlantı mevcut değildir. |
| Yangın algılama | `best.pt`: fire/smoke. Örnek görüntü çıkarımı test edildi; saha doğruluğu ölçülmedi. |
| Arama-kurtarma | Ayrı görev, operatör ihbarı ve sentetik kişi sensörü. Gerçek insan/termal algılama modeli henüz bağlı değildir. |

Drone'un uçuş izinin veya kamera görüşünün hesaplanması, alanın güvenilir şekilde aranıp temizlendiğini kanıtlamaz. PSO'nun ham kamera skorunu yükseltmesi de gerçek tespit kalitesinin arttığını kanıtlamaz. Bu sürümde hız/irtifa kapasiteye göre seçilir; otomatik öğrenilmiş en iyi uçuş profili iddiası yoktur.

## Doğrulama

```powershell
py -3.11 -m pytest tests -q
py -3.11 scripts/validate_hub.py
node --check web/static/js/dashboard.js
```

Güncel sonuçlar ve sınırlar: [doğrulama raporu](docs/HUB_VALIDATION.md).

600 saniyelik deterministik SAR simülasyonunda dört drone, iki gizli hedef ve bir kapalı alan kullanıldı. Bu senaryo gerçek kişi algılama veya uçuş doğrulaması değildir. Ölçümler yeniden üretilebilir: `artifacts/hub_validation/scenario.json`.

## Belgeler

- [Türkçe hub kullanım ve entegrasyon kılavuzu](docs/HUB_GUIDE_TR.md)
- [Kod incelemesi ve gerçek dünya uyumluluk değerlendirmesi](docs/REAL_WORLD_READINESS.md)
- [Güncel doğrulama raporu](docs/HUB_VALIDATION.md)

**Eski PDF'ler, `src/` tabanlı benchmark raporları ve önceki mimari belgeler tarihsel çıktılardır.** Yeni web kontrol akışının saha doğrulama belgesi olarak kullanılamazlar. Özellikle önceki "endüstriyel standart", "tam doğrulandı" ve genel algoritma üstünlüğü ifadeleri için yeterli kanıt bulunamadı.

## PSO hareket denklemi

Her kontrol adımında yatay komut şu kısıtlı PSO güncellemesinden üretilir:

`v_next = w*v + c1*r1*(pbest-x) + c2*r2*(evidence_target-x) + coverage + separation`

Konum farkları metre uzayında hız ölçeğine dönüştürülür. Kanıt bulunmadığında bilişsel/sosyal yangın çekimi sıfırlanır; kapsama terimi sektördeki keşfi sürdürür. Kanıt bulunduğunda PSO kişisel ve paylaşılan hedef bilgisini kullanır. Ardından ivme, araç kapasitesi, kapalı alan ve sınır kontrolleri uygulanır. Bu yöntem saf klasik PSO değil, görev ve güvenlik kısıtları eklenmiş PSO'dur. Sosyal terimi kapatma ve atalet değiştirme regresyonları, bu terimlerin hareketi gerçekten etkilediğini sınar.
