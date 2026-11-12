"""Hisoblash va risk algoritmi testlari (DB talab qilinmaydi)."""
import pytest

from app.services.calculator import attendance_rate, to_percent, trend_score, weighted_average
from app.services.risk import compute_risk, level_for, should_notify


def test_to_percent():
    assert to_percent(45, 50) == 90.0
    with pytest.raises(ValueError):
        to_percent(1, 0)


def test_weighted_average():
    assert weighted_average([]) is None
    assert weighted_average([("CURRENT", 80, 100)]) == 80.0
    # (60*1 + 90*2) / 3 = 80
    assert weighted_average([("CURRENT", 60, 100), ("FINAL", 90, 100)]) == 80.0
    # max_score 50 bo'lganda foizga o'tkaziladi
    assert weighted_average([("CURRENT", 25, 50)]) == 50.0


def test_attendance_rate():
    assert attendance_rate([]) is None
    assert attendance_rate(["EXCUSED"]) is None
    assert attendance_rate(["PRESENT", "ABSENT"]) == 50.0
    assert attendance_rate(["PRESENT", "LATE", "ABSENT", "EXCUSED"]) == 50.0  # (1+0.5+0)/3


def test_trend():
    assert trend_score([80, 80, 80]) == 0.0           # yetarli ma'lumot yo'q
    assert trend_score([90, 90, 90, 60, 60, 60]) == 60.0   # 30 punkt pasayish
    assert trend_score([50, 50, 50, 90, 90, 90]) == 0.0    # o'sish
    assert trend_score([100, 10, 10, 10]) == 100.0         # 90*2 -> 100 bilan cheklanadi


@pytest.mark.parametrize("score,level", [(0, "LOW"), (29.99, "LOW"), (30, "MEDIUM"), (49.99, "MEDIUM"),
                                         (50, "HIGH"), (69.99, "HIGH"), (70, "CRITICAL"), (100, "CRITICAL")])
def test_levels(score, level):
    assert level_for(score) == level


def test_compute_risk_examples():
    r = compute_risk(80, 90, 0)          # 10 + 3
    assert (r.risk_score, r.risk_level) == (13.0, "LOW")
    r = compute_risk(40, 50, 20)         # 30 + 15 + 4
    assert (r.risk_score, r.risk_level) == (49.0, "MEDIUM")
    r = compute_risk(30, 40, 40)         # 35 + 18 + 8
    assert (r.risk_score, r.risk_level) == (61.0, "HIGH")
    r = compute_risk(20, 30, 50)         # 40 + 21 + 10
    assert (r.risk_score, r.risk_level) == (71.0, "CRITICAL")


def test_compute_risk_missing_data():
    assert compute_risk(None, None, 0).risk_level == "LOW"
    assert compute_risk(None, 40, 0).risk_score == 60.0       # faqat davomat
    assert compute_risk(50, None, 0).risk_score == round((0.5 * 50) / 0.7, 2)


def test_should_notify():
    assert should_notify(None, "HIGH")
    assert should_notify("MEDIUM", "CRITICAL")
    assert should_notify("HIGH", "CRITICAL")
    assert not should_notify("HIGH", "HIGH")
    assert not should_notify("CRITICAL", "HIGH")
    assert not should_notify(None, "MEDIUM")
