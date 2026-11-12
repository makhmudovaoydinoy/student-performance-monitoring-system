"""Risk assessment algoritmi (sof funksiyalar).

risk_score = 0.5*(100 - o'rtacha ball) + 0.3*(100 - davomat) + 0.2*trend
Daraja: LOW <30, MEDIUM 30-49.99, HIGH 50-69.99, CRITICAL >=70
Agar komponent ma'lumoti yo'q bo'lsa (masalan, hali baho qo'yilmagan),
mavjud komponentlar vaznlari 1 ga normallashtiriladi.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

W_SCORE = 0.5
W_ATTENDANCE = 0.3
W_TREND = 0.2

LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@dataclass(frozen=True)
class RiskResult:
    risk_score: float
    risk_level: str


def level_for(score: float) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def compute_risk(avg_score: Optional[float], attendance_rate: Optional[float], trend: float = 0.0) -> RiskResult:
    parts: List[Tuple[float, float]] = []
    if avg_score is not None:
        parts.append((W_SCORE, 100.0 - avg_score))
        parts.append((W_TREND, trend))
    if attendance_rate is not None:
        parts.append((W_ATTENDANCE, 100.0 - attendance_rate))
    if not parts:
        return RiskResult(0.0, "LOW")
    weight_sum = sum(w for w, _ in parts)
    score = sum(w * v for w, v in parts) / weight_sum
    score = round(max(0.0, min(100.0, score)), 2)
    return RiskResult(score, level_for(score))


def should_notify(previous_level: Optional[str], new_level: str) -> bool:
    """HIGH/CRITICAL ga yangi yetganda yoki yomonlashganda xabarnoma yuboriladi."""
    prev = LEVEL_ORDER.get(previous_level, 0) if previous_level else 0
    new = LEVEL_ORDER[new_level]
    return new >= LEVEL_ORDER["HIGH"] and new > prev
