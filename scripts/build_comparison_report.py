"""Build auditable GitHub tables from completed experiment records, retaining failures."""
import sys,json,csv,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.compare_swarm_search import catalog,summarize,write_snapshot


def main():
    output=Path('artifacts/swarm_comparison')
    merged={}
    for directory in [output,Path('artifacts/optimization_extended'),Path('artifacts/cma_comparison')]:
        if not (directory/'runs.json').exists(): continue
        for row in json.loads((directory/'runs.json').read_text(encoding='utf-8')):
            merged.setdefault((row['algorithm'],row['seed']),row)
    methods={'Hub-Constrained-PSO':None,'Random-waypoints':None,**catalog('all')}
    rows=list(merged.values()); seeds=[101,102,103,104,105]
    assert set(merged)=={(name,seed) for name in methods for seed in seeds}, 'Unfinished catalog, refuse complete report'
    summary=summarize(rows,methods,seeds)
    write_snapshot(output/'runs.json',rows);write_snapshot(output/'summary.json',summary)
    ranked=summary['ranking'];fastest=min((r for r in ranked if r['safety_pass']),key=lambda r:r['first_detection_s'])
    with (output/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(ranked[0]));writer.writeheader();writer.writerows(ranked)
    lines=['# Yangın ve artçı yangın arama karşılaştırması','',
        f"**{len(methods)} yöntem / {len(rows)} koşu tamamlandı.** {len(summary['failures'])} koşu hata verdi; bunlar başarı tablosuna çevrilmedi. Liste MEALPY 3.0.3 içindeki 134 Original uygulama + CMA-ES + hub PSO ve rastgele referanstan oluşur. Bu, dünyadaki bütün optimizasyon teknikleri değildir.",'',
        f"İlk yangını ortalamada en erken gören: **{fastest['algorithm']} — {fastest['first_detection_s']:.1f} s**; toplam keşfi %{100*fastest['recall']:.1f}. Keşif oranı, ardından kaçırmalar dahil gecikme sıralamasında önde: **{ranked[0]['algorithm']}**. Bunlar yalnızca aşağıdaki beş sentetik senaryonun sonuçlarıdır; bağımsız saha doğrulaması veya evrensel kazanan değildir.",'',
        '## Deneyin gerçekte ölçtüğü','',
        '- Tohumlar: 101–105. Aynı tohumda tüm yöntemlere aynı 4 hedef, başlangıç ve sensör koşulları. Alan 800×800 m, 4 drone, 600 saniye. İki hedef başlangıçta, artçı hedefler 180 ve 360. saniyede tutuşur.',
        '- Fizik 0.5 s adımlı üretim `SimulatedDrone`; yol/ayrılma/hız kısıtları üretim `PSOEngine`. 10 m/s hız ve 2.5 m/s² nominal ivme sınırı. Başlangıç 85 m. Bu bir aerodinamik/rüzgâr/terrain/HIL modeli değildir.',
        '- Sensör özellikle SENTETİK: 40 m menzil, 2 s gözlem aralığı, %20 kaçırma olasılığı. Yanlış pozitif yok. YOLO sonucuyla karıştırılmamalı. Rastgele sensör çekilişi senaryo/hedef/drone/zamana bağlıdır.',
        '- Gizli koordinatlar sadece sensör ve değerlendirmede okunur. Optimizasyon hedef fonksiyonu gözlenmiş kapsama haritasını ve drone konumlarını alır; gelecekteki tutuşmaları bilmez.',
        '- Kütüphane yöntemlerinde her 30 s yeniden planlama, aynı 50 başlangıç adayı ve en çok 200 hedef fonksiyonu değerlendirmesi. En iyi değerlendirilmiş aday kullanılır. Epoch sayısını eşit bütçe gibi göstermiyoruz. Ham kayıtta gerçek değerlendirme sayısı var.',
        '- Hub PSO uçtan uca referanstır; kütüphane yöntemleri ortak kapsama vekil amaç fonksiyonunu optimize eder. Hub algoritmasına kütüphane eşit hesap bütçesi atanmış değildir. Bu yöntem aileleri arasında arama stratejisi taramasıdır.',
        '- İlk keşif: hiç bulunmazsa 600 s. Gecikme: her hedefin tutuşma→tespit süresi; bulunamayan hedefe tutuşma→600 s atanır. Kaçırılanlar ortalamadan silinmez. Keşif oranı toplam bulunan / toplam 20 hedeftir.',
        '- Beş tohum bir ön taramadır. Aynı senaryolardan yöntem seçildiği için seçim yanlılığı vardır. Ayrı doğrulama senaryosu, hiperparametre bütçesi çalışması ve güven aralığı olmadan kesin en iyi iddiası yoktur.',
        '- Güvenlik sütunu yalnızca kayıttaki en az 30 m ayrılma ve sıfır sınır aşımıdır. Radyo kaybı, gerçek engel, hava durumu, batarya doğruluğu veya fiziksel uçuş yeterliliği değildir. Güvenlik ihlalli yöntemler varsa alta taşınır; sonuçları silinmez.','',
        '## Karşılaştırmalı tablo','',
        '| Yöntem | İlk keşif ort. (s) | Tüm yangın keşfi | Artçı keşfi | Kaçırmalar dahil gecikme (s) | En az ayrılma (m) | Kısıt testi |',
        '|---|---:|---:|---:|---:|---:|---|']
    for r in ranked:
        lines.append(f"| {r['algorithm']} | {r['first_detection_s']:.1f} | %{100*r['recall']:.1f} | %{100*r['secondary_recall']:.1f} | {r['penalized_delay_s']:.1f} | {r['minimum_separation_m']:.1f} | {'Geçti' if r['safety_pass'] else 'İHLAL'} |")
    lines+=['','## Hata veren koşular','']
    for name in sorted({r['algorithm'] for r in summary['failures']}):
        failures=[r for r in summary['failures'] if r['algorithm']==name]
        lines.append(f"- **{name}**: {len(failures)} koşu. `{failures[0]['error']}`. Farklı algoritmayla sessizce değiştirilmedi; bu kurulum/parametre kümesinde karşılaştırma başarısız.")
    if not summary['failures']:lines.append('Hata veren koşu yok.')
    lines+=['','## Gerçek YOLO ile ayrı operatör deneyi','',
        '`scripts/operator_trial.py` gerçek `best.pt` modelini çağırdı; Mock kullanılmadı. 600 saniyelik hub devriyesinde iki başlangıç hedefi ve 180 s gecikmeli üçüncü hedef vardı. İlk anda aday/gbest sıfırdı. İlk iki hedefin 75 m yakınında sensör adayları oluştu; üçüncü hedef yakınında aday oluşmadı. Yakınlık hedef kimliğinin kanıtı değildir. Aynı yangın birden fazla aday üretebilir; aday sayısını bulunan yangın sayısı diye saymıyoruz.',
        'Kamera fotoğraf bankası tam kareye harmanlanır; gerçek hava kamerasının geometrisi değildir. Üçüncü örnek duman görüntüsünün model tarafından kaçırılması bilinen bir sınırlamadır. Artçı hedef başarısını uydurmak için geometrik sensör sonucunu bu deneye taşımadık. Model SHA256, kareler ve zaman çizgisi `artifacts/operator_trial/` içindedir.','',
        '## Bulunan ve düzeltilen hatalar','',
        '- Rastgele referans / tohum 105: önce 28.814 m ayrılma, erken itme düzeltmesinden sonra 46.113 m. Önceki başarısız kayıt `pre_fix_failure.json` içinde duruyor. Bu bir matematiksel çarpışmazlık garantisi değildir.',
        '- Çözülen olayın çevresinde gelecekteki sensör adaylarının sürekli bastırılması giderildi; 60 s sonra yeni aday mümkün.',
        '- Sonuç dosyasının arayüz tarafından okunurken yarım yazılma riski atomik snapshot ile giderildi; `--resume` tamamlanan kayıtları tekrar koşmaz.',
        '- Gönüllü kamera karelerinin alınmasına rağmen algılamada kullanılmaması giderildi; poz-kare eşleme, yaş ve tekrar kontrolleri eklendi.','',
        '## Canlı kullanım ve yeniden üretme','',
        'Ana sayfada **Tatbikat → gecikme → ◇ Tatbikat hedefi → haritaya tıkla → Başlat**. Gerçeklik katmanı yalnızca operatöre gösterilir. Olay listesinde otomatik hazır yangın oluşturulmaz. Kayıt tekrarları `/static/benchmark.html` adresinde; tohum, yöntem, zaman kaydırıcısı ve oynatma seçilebilir.','',
        '```powershell',
        'py -3.11 -m pip install -r requirements-benchmark.txt',
        'py -3.11 scripts/compare_swarm_search.py --families all --seeds 101 102 103 104 105',
        'py -3.11 scripts/operator_trial.py',
        'py -3.11 -m pytest -q',
        '```','',
        'Ham kayıt: [runs.json](../artifacts/swarm_comparison/runs.json). [CSV tablo](../artifacts/swarm_comparison/comparison.csv). [Özet](../artifacts/swarm_comparison/summary.json). [Drone entegrasyon kılavuzu](DRONE_INTEGRATION_TR.md).',
        'Uygulama kaynağı: [MEALPY](https://github.com/thieu1995/mealpy), [swarm_based API](https://mealpy.readthedocs.io/en/latest/pages/models/mealpy.swarm_based.html). Kütüphane uygulamasını kullanmak makaledeki tüm iddiaları bağımsız doğruladığımız anlamına gelmez.']
    Path('docs/SWARM_COMPARISON_TR.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    checks={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [output/'runs.json',Path('scripts/compare_swarm_search.py'),Path('core/pso_engine.py'),Path('hardware/simulated_drone.py')]}
    write_snapshot(output/'sha256.json',checks)
    print(json.dumps({'runs':len(rows),'methods':len(methods),'failed':len(summary['failures']),'first_fastest':fastest,'rank1':ranked[0]}))

if __name__=='__main__':main()
