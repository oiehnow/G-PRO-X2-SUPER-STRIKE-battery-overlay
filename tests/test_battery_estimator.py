import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from battery_estimator import (  # noqa: E402
    DEFAULT_FULL_LIFE_HOURS,
    BatteryEstimator,
    format_hours,
)


def test_no_samples_returns_full_life():
    est = BatteryEstimator()
    assert est.hours_remaining() == DEFAULT_FULL_LIFE_HOURS
    assert est.discharge_rate_per_hour() is None


def test_single_sample_uses_spec_fallback():
    est = BatteryEstimator(full_life_hours=80.0)
    est.add_sample(0.0, 50.0)
    # 방전율 추정 불가 → 80h * 50% = 40h
    assert est.discharge_rate_per_hour() is None
    assert est.hours_remaining() == 40.0


def test_discharge_rate_linear():
    est = BatteryEstimator()
    # 1시간 동안 100 -> 90 => 10%/h
    est.add_sample(0.0, 100.0)
    est.add_sample(3600.0, 90.0)
    rate = est.discharge_rate_per_hour()
    assert rate is not None
    assert abs(rate - 10.0) < 1e-6
    # 90% / 10%/h = 9h
    assert abs(est.hours_remaining() - 9.0) < 1e-6


def test_span_too_short_falls_back():
    est = BatteryEstimator(full_life_hours=75.0)
    est.add_sample(0.0, 100.0)
    est.add_sample(10.0, 99.0)  # 10초 < 최소 60초
    assert est.discharge_rate_per_hour() is None


def test_charging_resets_history():
    est = BatteryEstimator()
    est.add_sample(0.0, 100.0)
    est.add_sample(3600.0, 80.0)
    assert est.sample_count == 2
    # 충전 감지 (대폭 상승) → 리셋 후 새 샘플만 남음
    est.add_sample(7200.0, 95.0)
    assert est.sample_count == 1


def test_flat_samples_no_rate():
    est = BatteryEstimator()
    est.add_sample(0.0, 50.0)
    est.add_sample(3600.0, 50.0)
    assert est.discharge_rate_per_hour() is None


def test_backward_and_duplicate_timestamp_ignored():
    est = BatteryEstimator()
    est.add_sample(100.0, 90.0)
    est.add_sample(100.0, 89.0)  # 동일 시각
    est.add_sample(50.0, 88.0)   # 과거
    assert est.sample_count == 1


def test_percent_clamped():
    est = BatteryEstimator()
    est.add_sample(0.0, 150.0)
    est.add_sample(3600.0, -10.0)
    # 100 -> 0 over 1h = 100%/h, remaining 0
    assert abs(est.hours_remaining() - 0.0) < 1e-6


def test_format_hours():
    assert format_hours(9.0) == "9h 0m"
    assert format_hours(0.5) == "30m"
    assert format_hours(1.25) == "1h 15m"
