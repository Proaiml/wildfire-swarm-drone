"""
PyreSwarm - Bilimsel Grafik ve Görselleştirme Üreticisi (Figure Generator)
PDF raporlarına ve dokümantasyona gömülmek üzere yüksek çözünürlüklü (300 DPI),
yayın kalitesinde analitik grafikler üretir.
"""

import os
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = "docs/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Görsel Stil Ayarları
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#cbd5e1'
plt.rcParams['axes.linewidth'] = 0.8


def generate_algorithm_comparison():
    """1. Algoritma Karşılaştırma Grafiği (Bar Chart)"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11, 7.5), dpi=300)
    fig.patch.set_facecolor('#ffffff')

    algos = ['Random\nSearch', 'Lawnmower\n(Boustrophedon)', 'Independent\nGreedy', 'PyreSwarm\nMO-PSO']
    colors_list = ['#94a3b8', '#38bdf8', '#fbbf24', '#ea580c']

    # Veriler (5-Tohumlu Monte Carlo Simülasyon Ölçümleri)
    ttfd_means = [160.8, 165.6, 250.0, 180.0]
    ttfd_best = [21.0, 23.0, 250.0, 40.0]
    coverage_means = [20.3, 29.3, 18.6, 19.5]
    redundant_ratios = [91.5, 89.8, 89.1, 89.2]

    # Panel 1: Ortalama İlk Tespit Süresi (TTFD)
    bars1 = ax1.bar(algos, ttfd_means, color=colors_list, width=0.55, edgecolor='#334155', linewidth=0.5)
    ax1.set_title('Ortalama İlk Tespit Süresi (TTFD - sn)\n(Düşük olan daha iyidir)', fontsize=10, fontweight='bold', pad=10)
    ax1.set_ylabel('Saniye', fontsize=9)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 4, f"{yval:.1f}s", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    # Panel 2: En Hızlı Tespit Süresi (Best TTFD)
    bars2 = ax2.bar(algos, ttfd_best, color=colors_list, width=0.55, edgecolor='#334155', linewidth=0.5)
    ax2.set_title('En Hızlı Tespit Süresi (Best Run TTFD - sn)\n(Erken müdahale başarımı)', fontsize=10, fontweight='bold', pad=10)
    ax2.set_ylabel('Saniye', fontsize=9)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 4, f"{yval:.1f}s", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    # Panel 3: Alan Kapsama Yüzdesi (%)
    bars3 = ax3.bar(algos, coverage_means, color=colors_list, width=0.55, edgecolor='#334155', linewidth=0.5)
    ax3.set_title('Alan Kapsama Oranı (%)\n(Geniş alan tarama kapasitesi)', fontsize=10, fontweight='bold', pad=10)
    ax3.set_ylabel('Yüzde (%)', fontsize=9)
    ax3.set_ylim(0, 38)
    ax3.grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars3:
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.8, f"%{yval:.1f}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    # Panel 4: Mükerrer / Fazladan Tarama Oranı (%)
    bars4 = ax4.bar(algos, redundant_ratios, color=colors_list, width=0.55, edgecolor='#334155', linewidth=0.5)
    ax4.set_title('Gereksiz Mükerrer Örtüşme Payı (%)\n(Düşük olan enerji tasarrufu sağlar)', fontsize=10, fontweight='bold', pad=10)
    ax4.set_ylabel('Yüzde (%)', fontsize=9)
    ax4.set_ylim(80, 96)
    ax4.grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars4:
        yval = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 0.3, f"%{yval:.1f}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    plt.tight_layout()
    output_path = os.path.join(OUTPUT_DIR, "algorithm_comparison_bar.png")
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Grafik] Kaydedildi: {output_path}")


def generate_pso_parameter_tuning():
    """2. PSO Parametre Ayarı ve Meta-Optimizasyon Analizi"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    fig.patch.set_facecolor('#ffffff')

    # Panel 1: Farklı Parametre Konfigürasyonlarının Skoru
    configs = [
        'Klasik / Naive PSO\n(w=0.72, c1=1.5, c2=2.5)',
        'Aşırı Keşif\n(w=0.90, c1=2.8, c2=0.4)',
        'Aşırı İşbirliği\n(w=0.60, c1=0.8, c2=2.8)',
        'PyreSwarm MO-PSO\n(Adaptif w/c1/c2 + Tabu)'
    ]
    scores = [21.46, 20.75, 31.58, 25.80]
    bar_colors = ['#94a3b8', '#64748b', '#0284c7', '#ea580c']

    bars = ax1.barh(configs, scores, color=bar_colors, height=0.55, edgecolor='#334155', linewidth=0.5)
    ax1.set_title('PSO Hiperparametre Meta-Optimizasyon Skorları\n(Farklı Arama Stratejilerinin Uygunluk Değeri)', fontsize=10, fontweight='bold', pad=10)
    ax1.set_xlabel('Bileşik Uygunluk Skoru (Score)', fontsize=9)
    ax1.grid(axis='x', linestyle='--', alpha=0.5)
    for bar in bars:
        wval = bar.get_width()
        ax1.text(wval + 0.5, bar.get_y() + bar.get_height()/2.0, f"{wval:.2f}", ha='left', va='center', fontsize=8.5, fontweight='bold')

    # Panel 2: Atalet Ağırlığı (w) ve Bilişsel/Sosyal Katsayı Adaptasyonu (Zaman İçinde)
    t = np.linspace(0, 200, 200)
    w_t = 0.85 - (0.85 - 0.40) * (t / 200.0)
    c1_t = 2.0 - 0.8 * (t / 200.0)
    c2_t = 1.2 + 0.8 * (t / 200.0)

    ax2.plot(t, w_t, label='Atalet Katsayısı w(t) [0.85 -> 0.40]', color='#0284c7', linewidth=2.0)
    ax2.plot(t, c1_t, label='Bilişsel Keşif c1(t) [2.0 -> 1.2]', color='#16a34a', linewidth=2.0, linestyle='--')
    ax2.plot(t, c2_t, label='Sosyal İşbirliği c2(t) [1.2 -> 2.0]', color='#ea580c', linewidth=2.0, linestyle='-.')
    ax2.set_title('PyreSwarm Dinamik Parametre Adaptasyon Eğrisi\n(Zamanla Keşiften Doğrulama/İşbirliğine Geçiş)', fontsize=10, fontweight='bold', pad=10)
    ax2.set_xlabel('Görev Süresi (Adım / Saniye)', fontsize=9)
    ax2.set_ylabel('Katsayı Değeri', fontsize=9)
    ax2.legend(loc='upper right', fontsize=8.5, framealpha=0.9)
    ax2.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    output_path = os.path.join(OUTPUT_DIR, "pso_parameter_tuning.png")
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Grafik] Kaydedildi: {output_path}")


def generate_swarm_trajectories():
    """3. Sürü Uçuş Yörüngeleri, NFZ Engeli ve Yangın Tespiti Taktik Haritası"""
    fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
    fig.patch.set_facecolor('#ffffff')

    # Arama Alanı (2000m x 2000m)
    search_box = patches.Rectangle((-1000, -1000), 2000, 2000, linewidth=2, edgecolor='#1e293b', facecolor='#f8fafc', linestyle='--')
    ax.add_patch(search_box)

    # Göl / Uçuşa Yasak Bölge (NFZ)
    lake_box = patches.Rectangle((-300, 100), 600, 500, linewidth=1.5, edgecolor='#0284c7', facecolor='#bae6fd', alpha=0.6, label='Göl / No-Fly Zone (NFZ)')
    ax.add_patch(lake_box)

    # Yangın Odakları
    fire1 = patches.Circle((450, 600), 75, facecolor='#ef4444', edgecolor='#b91c1c', alpha=0.8, label='Doğrulanan Yangın Odağı 1')
    fire2 = patches.Circle((-600, -400), 65, facecolor='#f97316', edgecolor='#c2410c', alpha=0.8, label='İkincil Yangın Odağı 2')
    ax.add_patch(fire1)
    ax.add_patch(fire2)

    # 5 Drone'un Simüle Yörüngeleri
    np.random.seed(42)
    drone_colors = ['#2563eb', '#16a34a', '#9333ea', '#ea580c', '#0891b2']
    base_pos = (0, -900)

    for i in range(5):
        # Üsten kalkış
        xs = [base_pos[0] + (i - 2) * 50]
        ys = [base_pos[1]]

        curr_x, curr_y = xs[0], ys[0]
        # Yörünge simülasyonu (NFZ'den kaçış ve yangına yaklaşma)
        for step in range(35):
            if i in (0, 1): # Yangın 1'e gidenler
                target = (450, 600)
            elif i in (2, 3): # Yangın 2'yi arayanlar
                target = (-600, -400)
            else: # Genel devriye
                target = (0, 300)

            dx = target[0] - curr_x
            dy = target[1] - curr_y
            dist = math.hypot(dx, dy)

            # NFZ kaçınma kuvveti
            if -350 < curr_x < 350 and 50 < curr_y < 650:
                curr_x += 40 if curr_x > 0 else -40
                curr_y -= 30
            else:
                curr_x += (dx / max(1.0, dist)) * 45 + np.random.randn() * 12
                curr_y += (dy / max(1.0, dist)) * 45 + np.random.randn() * 12

            xs.append(curr_x)
            ys.append(curr_y)

        ax.plot(xs, ys, color=drone_colors[i], linewidth=1.6, alpha=0.85, label=f'Drone {i+1} Yörüngesi')
        ax.scatter([xs[-1]], [ys[-1]], color=drone_colors[i], s=55, marker='^', zorder=5)

    # Üs Konumu
    ax.scatter([base_pos[0]], [base_pos[1]], color='#0f172a', s=120, marker='s', zorder=6, label='Operasyon Üssü (Home)')

    ax.set_xlim(-1100, 1100)
    ax.set_ylim(-1100, 1100)
    ax.set_title('PyreSwarm Sürü Arama Yörüngeleri & Taktik Harita (2D ENU Metrik)\n(NFZ Kaçınma, Çoklu Yangın Yakınsaması ve Sürü Ayrılması)', fontsize=10, fontweight='bold', pad=12)
    ax.set_xlabel('Doğu (East - Metre)', fontsize=9)
    ax.set_ylabel('Kuzey (North - Metre)', fontsize=9)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='lower right', fontsize=8, framealpha=0.92)

    output_path = os.path.join(OUTPUT_DIR, "swarm_trajectories.png")
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Grafik] Kaydedildi: {output_path}")


def generate_cumulative_probability():
    """4. Kümülatif Tespit Olasılığı Eğrisi P(t) (Koopman vs Algoritmalar)"""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    fig.patch.set_facecolor('#ffffff')

    t = np.linspace(0, 300, 300)
    # A_total = 4 km2 = 4,000,000 m2
    # ACR_single = 12 * 130.11 = 1561.32 m2/s
    # 5 drone => 7806.6 m2/s
    # A_swept(t) = 7806.6 * t
    ratio = (7806.6 * t) / 4_000_000.0

    p_random = 1.0 - np.exp(-ratio)
    p_lawnmower = np.clip(ratio * 1.1, 0, 1.0) # Deterministik tarama
    p_pso = 1.0 - np.exp(-1.62 * ratio) # Koopman eta=1.62 çarpanı

    ax.plot(t, p_pso * 100, color='#ea580c', linewidth=2.5, label='PyreSwarm MO-PSO (Duman & Sürü İşbirliği, η=1.62)')
    ax.plot(t, p_lawnmower * 100, color='#0284c7', linewidth=2.0, linestyle='--', label='Lawnmower (Çim Biçme / Deterministik Şerit)')
    ax.plot(t, p_random * 100, color='#64748b', linewidth=1.8, linestyle=':', label='Rastgele Arama (Koopman Random Search)')

    ax.axhline(95.0, color='#ef4444', linestyle='-.', alpha=0.7, label='%95 Güven Sınırı (Operasyonel Hedef)')

    ax.set_title('Zaman İçinde Kümülatif Yangın Tespit Olasılığı P(t) (%)\n(4 km² Sahada 5 Drone ile Karşılaştırmalı Arama Teorisi)', fontsize=10, fontweight='bold', pad=12)
    ax.set_xlabel('Arama Süresi (Saniye)', fontsize=9)
    ax.set_ylabel('Kümülatif Tespit Olasılığı (%)', fontsize=9)
    ax.set_ylim(0, 105)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='lower right', fontsize=8.5, framealpha=0.92)

    output_path = os.path.join(OUTPUT_DIR, "cumulative_probability.png")
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Grafik] Kaydedildi: {output_path}")


if __name__ == "__main__":
    generate_algorithm_comparison()
    generate_pso_parameter_tuning()
    generate_swarm_trajectories()
    generate_cumulative_probability()
    print("[Tamamlandı] Tüm analitik grafikler oluşturuldu!")
