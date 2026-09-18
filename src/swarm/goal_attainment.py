"""
PyreSwarm - Çok Amaçlı Hedef Ulaşımı (Multi-Objective Goal Attainment Fitness)
Yalnızca yangın güvenini maksimize etmek yerine; yangın kanıtı, duman, yeni alan keşfi,
risk, enerji maliyeti, sürü örtüşmesi ve seyahat mesafesini normalize edilmiş
ağırlıklarla optimize eder.
J = w_f * F + w_s * S + w_c * C - w_r * R - w_e * E - w_o * O - w_d * D
[THEORETICAL_BOUND]
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import math


@dataclass
class MultiObjectiveWeights:
    """Normalize edilmiş amaç ağırlıkları. Toplam pozitif etki ve cezalar dengelenmiştir."""
    w_fire: float = 0.35        # F: Yangın kanıtı ağırlığı
    w_smoke: float = 0.15       # S: Duman kanıtı ağırlığı
    w_coverage: float = 0.25    # C: Yeni taranacak alan keşif değeri
    w_risk: float = 0.05        # R: Risk / tehlike cezası
    w_energy: float = 0.08      # E: Enerji tüketim cezası
    w_overlap: float = 0.07     # O: Diğer drone'larla gereksiz örtüşme cezası
    w_distance: float = 0.05    # D: Mesafe / seyahat süresi cezası


class GoalAttainmentFitness:
    """
    Hedef Ulaşımı (Goal Attainment) ve Çok Amaçlı Uygunluk (Fitness) değerlendiricisi.
    Her aday hedef noktasını [0.0, 1.0] aralığında normalize edilmiş bileşenlerle puanlar.
    """

    def __init__(self, weights: Optional[MultiObjectiveWeights] = None):
        self.w = weights or MultiObjectiveWeights()

    def evaluate_candidate(
        self,
        fire_evidence: float,       # [0.0, 1.0]
        smoke_evidence: float,      # [0.0, 1.0]
        coverage_value: float,      # [0.0, 1.0] (1.0 = daha önce hiç taranmamış)
        risk_penalty: float,        # [0.0, 1.0] (1.0 = NFZ veya tehlikeye çok yakın)
        energy_cost: float,         # [0.0, 1.0] (1.0 = çok yüksek batarya sarfiyatı)
        overlap_penalty: float,     # [0.0, 1.0] (1.0 = başka bir drone'un tarama alanı)
        distance_penalty: float     # [0.0, 1.0] (1.0 = maksimum operasyon yarıçapı)
    ) -> float:
        """
        Normalize edilmiş bileşenleri birleştirerek net fitness skorunu üretir.
        Döndürür: composite_fitness (Tipik aralık: [-1.0, 1.0], yüksek olan tercih edilir)
        """
        # Pozitif ödül terimleri
        reward = (
            self.w.w_fire * min(1.0, max(0.0, fire_evidence)) +
            self.w.w_smoke * min(1.0, max(0.0, smoke_evidence)) +
            self.w.w_coverage * min(1.0, max(0.0, coverage_value))
        )

        # Negatif ceza terimleri
        penalty = (
            self.w.w_risk * min(1.0, max(0.0, risk_penalty)) +
            self.w.w_energy * min(1.0, max(0.0, energy_cost)) +
            self.w.w_overlap * min(1.0, max(0.0, overlap_penalty)) +
            self.w.w_distance * min(1.0, max(0.0, distance_penalty))
        )

        composite_fitness = reward - penalty
        return round(composite_fitness, 4)

    def calculate_goal_deviation(
        self,
        achieved_metrics: Dict[str, float],
        goal_targets: Dict[str, float]
    ) -> float:
        """
        Klasik Goal Attainment formülasyonu:
        min alpha, subject to f_j(x) - g_j <= w_j * alpha
        Tüm hedeflerden en büyük göreli sapmayı (Chebyshev mesafesi) döndürür.
        """
        max_alpha = -float("inf")
        for key, goal in goal_targets.items():
            achieved = achieved_metrics.get(key, 0.0)
            weight = getattr(self.w, f"w_{key}", 0.2)
            if weight > 0:
                deviation = (goal - achieved) / weight
                if deviation > max_alpha:
                    max_alpha = deviation

        return round(max_alpha, 4)
