"""O'zlashtirish ko'rsatkichlarini hisoblash (sof funksiyalar, DB'ga bog'liq emas)."""
from statistics import mean
from typing import Iterable, Optional, Sequence, Tuple

# Baho turlari vazni: yakuniy nazorat eng muhim
GRADE_WEIGHTS = {"CURRENT": 1.0, "MIDTERM": 1.5, "FINAL": 2.0}
# Davomat: kelgan = 1, kechikkan = 0.5, kelmagan = 0, sababli (EXCUSED) hisobga olinmaydi
ATTENDANCE_CREDIT = {"PRESENT": 1.0, "LATE": 0.5, "ABSENT": 0.0}

GradeTuple = Tuple[str, float, float]  # (grade_type, score, max_score)


def to_percent(score: float, max_score: float) -> float:
    if max_score <= 0:
        raise ValueError("max_score 0 dan katta bo'lishi kerak")
    return float(score) / float(max_score) * 100.0


def weighted_average(grades: Sequence[GradeTuple]) -> Optional[float]:
    """Baholarning vaznli o'rtachasi, foizda (0-100). Baho bo'lmasa None."""
    total_w = 0.0
    total = 0.0
    for grade_type, score, max_score in grades:
        w = GRADE_WEIGHTS.get(grade_type, 1.0)
        total += to_percent(score, max_score) * w
        total_w += w
    if total_w == 0:
        return None
    return round(total / total_w, 2)


def attendance_rate(statuses: Iterable[str]) -> Optional[float]:
    """Davomat foizi (0-100). EXCUSED maxrajdan chiqariladi. Ma'lumot bo'lmasa None."""
    counted = [s for s in statuses if s != "EXCUSED"]
    if not counted:
        return None
    credit = sum(ATTENDANCE_CREDIT.get(s, 0.0) for s in counted)
    return round(credit / len(counted) * 100.0, 2)


def trend_score(percents: Sequence[float], recent_n: int = 3, min_points: int = 4) -> float:
    """Pasayish trendi (0-100). Oxirgi `recent_n` ta baho oldingilarga nisbatan
    qancha pasaygan bo'lsa, farq 2 ga ko'paytiriladi (50 punkt pasayish = 100).
    O'sish yoki yetarli ma'lumot yo'qligi = 0."""
    if len(percents) < min_points:
        return 0.0
    recent = percents[-recent_n:]
    earlier = percents[:-recent_n]
    if not earlier:
        return 0.0
    drop = mean(earlier) - mean(recent)
    return round(min(max(drop * 2.0, 0.0), 100.0), 2)
