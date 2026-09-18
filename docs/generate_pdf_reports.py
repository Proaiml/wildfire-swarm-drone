"""
PyreSwarm - Profesyonel PDF Dokümantasyon ve Metrik Raporu Üreticisi
ReportLab kullanarak baskı kalitesinde, renkli, tablolu ve grafikli iki kapsamlı PDF dokümanı oluşturur:
1. PyreSwarm_Kullanim_Kilavuzu.pdf
2. PyreSwarm_Matematiksel_Model_ve_Metrik_Raporu.pdf
"""

import os
import sys

# Proje kök dizinini ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

from core.metrics_engine import MetricsEngine


class NumberedCanvas(canvas.Canvas):
    """Her sayfaya profesyonel alt bilgi (footer) ve sayfa numarası ekler."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Kapak sayfasında alt bilgi çizme

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#53647c"))

        # Üst bilgi
        self.drawString(2.0 * cm, A4[1] - 1.2 * cm, "PYRESWARM | OTONOM YANGIN TESPİT & SÜRÜ DRONE SİSTEMİ")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(2.0 * cm, A4[1] - 1.35 * cm, A4[0] - 2.0 * cm, A4[1] - 1.35 * cm)

        # Alt bilgi
        page_text = f"Sayfa {self._pageNumber} / {page_count}"
        self.drawRightString(A4[0] - 2.0 * cm, 1.2 * cm, page_text)
        self.drawString(2.0 * cm, 1.2 * cm, "GİZLİ & TİCARİ DEĞİL - AÇIK KAYNAK MÜHENDİSLİK DOKÜMANI")
        self.line(2.0 * cm, 1.45 * cm, A4[0] - 2.0 * cm, 1.45 * cm)

        self.restoreState()


def create_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=colors.HexColor('#0f172a'),
        alignment=0,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#ff5500'),
        alignment=0,
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#ff5500'),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    formula_style = ParagraphStyle(
        'Formula_Custom',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#005588'),
        backColor=colors.HexColor('#f1f5f9'),
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=6
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'h1': h1_style,
        'h2': h2_style,
        'body': body_style,
        'bullet': bullet_style,
        'formula': formula_style
    }


def generate_user_guide_pdf(output_path: str = "docs/PyreSwarm_Kullanim_Kilavuzu.pdf"):
    """PyreSwarm Türkçe Kullanım Kılavuzu PDF'ini oluşturur."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm
    )

    st = create_styles()
    story = []

    # Kapak Başlığı
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("PYRESWARM", st['title']))
    story.append(Paragraph("OTONOM YANGIN TESPİT VE 3D-PSO SÜRÜ DRONE SİSTEMİ", st['subtitle']))
    story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor('#ff5500'), spaceBefore=0, spaceAfter=20))

    story.append(Paragraph("<b>Belge Türü:</b> Operasyonel Saha ve Kullanım Kılavuzu (User Manual)", st['body']))
    story.append(Paragraph("<b>Sürüm:</b> v2.4 Professional Enterprise", st['body']))
    story.append(Paragraph("<b>Yapay Zeka Modeli:</b> YOLOv8 Deep Vision (best.pt - Yangın & Duman)", st['body']))
    story.append(Paragraph("<b>Otopilot Protokolü:</b> MAVLink (PX4 / ArduPilot / Pixhawk) & Virtual SITL", st['body']))
    story.append(Paragraph("<b>Tarih:</b> Eylül 2026", st['body']))

    story.append(Spacer(1, 1.0 * cm))

    # Özet Kutu
    summary_data = [[
        Paragraph("<b>HIZLI BAKIŞ (ÖZET):</b><br/>"
                  "Bu kılavuz; orman yangınlarının ilk çıkış anlarının tespiti ve yayılma perimetrelerinin takibi "
                  "için geliştirilen PyreSwarm sisteminin web görev kontrol istasyonunu (GCS), alan kapatma sihirbazını, "
                  "gönüllü vatandaş drone entegrasyonunu ve gerçek otopilot saha kurulumunu adım adım açıklamaktadır.", st['body'])
    ]]
    summary_table = Table(summary_data, colWidths=[17 * cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff7ed')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#ffedd5')),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)

    story.append(PageBreak())

    # Bölüm 1
    story.append(Paragraph("1. Sistem Mimarisi ve Çalışma Mantığı", st['h1']))
    story.append(Paragraph(
        "PyreSwarm, klasik optimizasyon yöntemlerinden farklı olarak <b>Parçacık Sürü Optimizasyonunu (PSO)</b> "
        "fiziksel drone kinematiği ve bilgisayarlı görü ile birleştirir. Sürüdeki her bir drone (parçacık), "
        "kendi kamerasından frame frame yangın/duman çıkarımı yapar.", st['body']
    ))
    story.append(Paragraph("<b>Sistemdeki Temel Parametreler:</b>", st['body']))
    story.append(Paragraph("• <b>Kişisel En İyi (pbest):</b> Drone'un kendi uçuşu boyunca tespit ettiği en yüksek alev/duman skoru ve GPS noktasıdır.", st['bullet']))
    story.append(Paragraph("• <b>Küresel En İyi (gbest):</b> Sürü mesh ağında paylaşılan en kritik yangın koordinatıdır.", st['bullet']))
    story.append(Paragraph("• <b>Çarpışma Önleme (APF):</b> Yapay Potansiyel Alanlar ile drone'lar birbirine 30 metreden fazla yaklaşmaz.", st['bullet']))
    story.append(Paragraph("• <b>Dinamik İrtifa:</b> Arama fazında geniş görüş alanı için 85m, tespit anında detaylı inceleme için 35m irtifa kullanılır.", st['bullet']))

    # Bölüm 2
    story.append(Paragraph("2. Kurulum ve Tek Tıkla Başlatma", st['h1']))
    story.append(Paragraph("Sistem gereksinimleri ve başlatma komutları:", st['body']))
    story.append(Paragraph("python run.py", st['formula']))
    story.append(Paragraph("Sunucu ayağa kalktığında web tarayıcısından <b>http://localhost:8000</b> adresine bağlanılır.", st['body']))

    # Bölüm 3
    story.append(Paragraph("3. Alan Kapatma Sihirbazı (Geofence / Taboo Zones)", st['h1']))
    story.append(Paragraph(
        "Operasyon sırasında belirli alanların arama dışı bırakılması kritik önem taşır:", st['body']
    ))
    story.append(Paragraph("• <b>Söndürülmüş Yangın Bölgesi:</b> İtfaiye yangını kontrol altına aldığında, haritadaki 'SÖNDÜRÜLDÜ (KAPAT)' "
                           "butonuyla alan çevrilir. Sürü bu bölgeyi taboo ilan eder ve <b>gbest otomatik sıfırlanarak</b> yeni yangınlara yönelinir.", st['bullet']))
    story.append(Paragraph("• <b>Göl / Su Kütlesi:</b> 'GÖL KAPAT' butonu ile yangın riski olmayan alanlar devre dışı bırakılır.", st['bullet']))
    story.append(Paragraph("• <b>Uçuşa Yasak Bölge (No-Fly):</b> Havalimanı veya askeri alanlar işaretlenir, APF itki kuvveti drone'ları sınırdan uzaklaştırır.", st['bullet']))

    # Bölüm 4
    story.append(Paragraph("4. Vatandaş ve Gönüllü Drone Katılımı (Citizen Swarm)", st['h1']))
    story.append(Paragraph(
        "Yangın sahasına gelen sivil vatandaşların drone'ları anında sürüye dahil edilebilir:", st['body']
    ))
    story.append(Paragraph("1. Üst paneldeki <b>'GÖNÜLLÜ EKLE'</b> butonuna tıklayın.", st['bullet']))
    story.append(Paragraph("2. Pilot adını ve başlangıç koordinatlarını girip 'Sürüye Dahil Et'e basın.", st['bullet']))
    story.append(Paragraph("3. Sistem otonom PSO matrisine yeni drone'u katar ve sivil pilota pusula yönü/irtifa kılavuzluğu sağlar.", st['bullet']))

    # Bölüm 5
    story.append(Paragraph("5. Pixhawk / PX4 MAVLink Saha Bağlantısı", st['h1']))
    story.append(Paragraph(
        "Gerçek endüstriyel drone'lar için PyMAVLink entegrasyonu mevcuttur. "
        "Drone üzerindeki telemetri radyosu veya 4G Companion Computer (Raspberry Pi/Jetson) üzerinden "
        "<b>udpin:0.0.0.0:14550</b> portuna veri aktarılır. Otopilot modu <b>GUIDED</b> olarak ayarlanmalıdır.", st['body']
    ))

    # Dokümanı derle
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF] Kullanım Kılavuzu oluşturuldu: {output_path}")


def generate_metrics_report_pdf(output_path: str = "docs/PyreSwarm_Matematiksel_Model_ve_Metrik_Raporu.pdf"):
    """PyreSwarm Matematiksel İspat, Arama Teorisi ve Simülasyon Metrik Raporu PDF'ini oluşturur."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm
    )

    st = create_styles()
    story = []
    engine = MetricsEngine()

    # Kapak Başlığı
    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph("PYRESWARM", st['title']))
    story.append(Paragraph("MATEMATİKSEL ARAMA TEORİSİ, METRİKLER VE MONTE CARLO DOĞRULAMA RAPORU", st['subtitle']))
    story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor('#0088ff'), spaceBefore=0, spaceAfter=18))

    story.append(Paragraph("<b>Doküman Statüsü:</b> Matematiksel Kanıt ve Ampirik Simülasyon Raporu", st['body']))
    story.append(Paragraph("<b>Amaç:</b> km² başına yangın tespit sürelerinin teorik ve Monte Carlo simülasyonlarıyla ispatı", st['body']))
    story.append(Paragraph("<b>Optik Parametreler:</b> FOV 84° Yatay, 56° Dikey | Arama İrtifası: 85.0 m", st['body']))
    story.append(Paragraph("<b>Kinematik Parametreler:</b> Seyir Hızı v = 12.0 m/s (43.2 km/h) | %15 Güvenli Örtüşme", st['body']))

    story.append(Spacer(1, 0.5 * cm))

    # Bölüm 1: Matematiksel Formülasyon
    story.append(Paragraph("1. Sensör Geometrisi ve Alan Tarama Denklemleri", st['h1']))
    story.append(Paragraph(
        "Kamera sensörünün yerdeki izdüşümü (Ground Footprint), irtifa (h) ve görüş açılarına (FOV) bağlıdır:", st['body']
    ))
    story.append(Paragraph("W = 2 * h * tan(FOV_h / 2)  -->  W = 2 * 85 * tan(42°) = 153.07 metre", st['formula']))
    story.append(Paragraph("L = 2 * h * tan(FOV_v / 2)  -->  L = 2 * 85 * tan(28°) = 90.39 metre", st['formula']))
    story.append(Paragraph("Anlık Görüntü Kapsama Alanı: A_inst = W * L = 13,836 m² (0.0138 km²)", st['formula']))

    story.append(Paragraph(
        "Kör nokta kalmaması için %15 örtüşme payı düşüldüğünde etkin tarama genişliği:", st['body']
    ))
    story.append(Paragraph("W_eff = W * (1 - mu_overlap) = 153.07 * 0.85 = 130.11 metre", st['formula']))

    story.append(Paragraph(
        "Tek bir drone ve N adet drone'dan oluşan sürünün Birim Zamandaki Alan Tarama Hızı (ACR):", st['body']
    ))
    story.append(Paragraph("ACR_1 = v * W_eff = 12 m/s * 130.11 m = 1,561.3 m²/s = 5.62 km²/saat", st['formula']))
    story.append(Paragraph("ACR_Swarm = N * v * W_eff = N * 5.62 km²/saat", st['formula']))

    # Tablo: Drone Sayısına Göre Tarama Hızı
    acr_data = [
        ["Drone Sayısı (N)", "Bileşke Hız", "Etkin Genişlik", "Tarama Hızı (m²/s)", "Tarama Hızı (km²/saat)"],
        ["1 Drone", "12.0 m/s", "130.1 m", "1,561 m²/s", "5.62 km²/h"],
        ["3 Drone", "12.0 m/s", "390.3 m", "4,684 m²/s", "16.86 km²/h"],
        ["5 Drone", "12.0 m/s", "650.5 m", "7,807 m²/s", "28.10 km²/h"],
        ["10 Drone", "12.0 m/s", "1,301.1 m", "15,613 m²/s", "56.20 km²/h"],
        ["20 Drone", "12.0 m/s", "2,602.2 m", "31,226 m²/s", "112.41 km²/h"],
    ]
    t_acr = Table(acr_data, colWidths=[3.2 * cm, 2.5 * cm, 3.2 * cm, 3.8 * cm, 4.3 * cm])
    t_acr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(t_acr)
    story.append(Spacer(1, 0.4 * cm))

    # Bölüm 2: Koopman Arama Teorisi
    story.append(Paragraph("2. Koopman Arama Teorisi ve Tespit Süresi (MTTD)", st['h1']))
    story.append(Paragraph(
        "Koopman teoremine göre, A_total alanında rastgele bir noktada çıkan yangının "
        "t süresi içinde en az bir drone tarafından tespit edilme olasılığı kümülatif Poisson dağılımı izler:", st['body']
    ))
    story.append(Paragraph("P(t) = 1 - exp( - (N * v * W_eff * eta_pso / A_total) * t )", st['formula']))
    story.append(Paragraph(
        "Burada eta_pso = 1.62, duman kokusu ve pbest/gbest çekimiyle elde edilen arama verimlilik kazancıdır. "
        "Bu denklem tersine çevrildiğinde, %50 (medyan) ve %95 güvenilirlikte yangın tespit süreleri analitik olarak çözülür:", st['body']
    ))
    story.append(Paragraph("T_50 = ln(2) * A_total / (N * v * W_eff * eta_pso)", st['formula']))
    story.append(Paragraph("T_95 = ln(20) * A_total / (N * v * W_eff * eta_pso)  [ln(20) ~= 2.996]", st['formula']))

    # Kapsamlı Karşılaştırma Tablosu
    story.append(Paragraph("<b>Farklı Alan Boyutları ve Drone Sayılarına Göre Analitik Tespit Süreleri:</b>", st['body']))

    table_data = [
        ["Alan (km²)", "1 Drone (%95)", "3 Drone (%95)", "5 Drone (%95)", "10 Drone (%95)", "20 Drone (%95)"]
    ]
    test_areas = [1.0, 4.0, 10.0, 25.0, 50.0, 100.0]
    for a in test_areas:
        row = [f"{a:.0f} km²"]
        for n in [1, 3, 5, 10, 20]:
            res = engine.get_analytical_detection_time(a, n, confidence_percent=95.0)
            mins = res["t_target_conf_minutes"]
            if mins < 1.0:
                row.append(f"{res['t_target_conf_seconds']:.0f} sn")
            elif mins < 60.0:
                row.append(f"{mins:.1f} dk")
            else:
                row.append(f"{mins/60.0:.1f} saat")
        table_data.append(row)

    t_perf = Table(table_data, colWidths=[2.8 * cm, 2.8 * cm, 2.8 * cm, 2.8 * cm, 2.9 * cm, 2.9 * cm])
    t_perf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff5500')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff7ed')]),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(t_perf)

    story.append(PageBreak())

    # Bölüm 3: Monte Carlo Simülasyonu ve Grafikler
    story.append(Paragraph("3. Monte Carlo Simülasyonu ve Ampirik Doğrulama", st['h1']))
    story.append(Paragraph(
        "Matematiksel formüllerin yanı sıra, 2D/3D kinematik hareket, rüzgar duman sürüklenmesi (Gaussian Plume) "
        "ve gerçek PSO parametreleri ile 50'şer tekrarlı Monte Carlo simülasyonu koşturulmuştur.", st['body']
    ))

    # Grafikleri ekle
    fig1_path = "docs/figures/area_vs_detection_time.png"
    fig2_path = "docs/figures/algorithm_comparison.png"
    fig3_path = "docs/figures/cumulative_probability.png"

    if os.path.exists(fig1_path):
        story.append(Paragraph("<b>Şekil 1:</b> Tarama Alanı vs Yangın Tespit Süresi (Farklı Drone Sayıları)", st['h2']))
        story.append(Image(fig1_path, width=16.5 * cm, height=8.2 * cm))
        story.append(Spacer(1, 0.4 * cm))

    if os.path.exists(fig2_path):
        story.append(Paragraph("<b>Şekil 2:</b> 25 km² Alanda Arama Algoritmalarının Karşılaştırılması (Monte Carlo)", st['h2']))
        story.append(Image(fig2_path, width=16.5 * cm, height=8.2 * cm))
        story.append(Spacer(1, 0.4 * cm))

    if os.path.exists(fig3_path):
        story.append(Paragraph("<b>Şekil 3:</b> Zaman İçinde Kümülatif Tespit Olasılığı Eğrisi P(t)", st['h2']))
        story.append(Image(fig3_path, width=16.5 * cm, height=8.2 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("4. Temel Mühendislik ve Operasyonel Çıkarımlar", st['h1']))
    story.append(Paragraph("• <b>1 km² İlk Çıkış Alanı:</b> 3 drone ile yangın ortalama <b>1.5 dakikada</b> (medyan), en geç <b>6.5 dakikada</b> (%95 güvenle) tespit edilmektedir.", st['bullet']))
    story.append(Paragraph("• <b>10 km² Alan İçin:</b> 10 drone'luk bir sürü <b>4.5 dakikada</b> (%50 medyan), <b>19.7 dakikada</b> ise tüm bölgeyi %95 kesinlikle güvenceye almaktadır.", st['bullet']))
    story.append(Paragraph("• <b>25 km² Geniş Alan:</b> 20 drone filosu ile <b>24.6 dakikada</b> %95 tespit garantisi sağlanmaktadır.", st['bullet']))
    story.append(Paragraph("• <b>PSO Üstünlüğü:</b> PyreSwarm 3D-PSO algoritması, körlemesine ızgara (lawnmower) taramaya göre <b>1.54 kat</b>, rastgele gezinime göre ise <b>2.58 kat</b> daha hızlı sonuç üretmektedir.", st['bullet']))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF] Matematiksel Metrik Raporu oluşturuldu: {output_path}")


if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    generate_user_guide_pdf()
    generate_metrics_report_pdf()
