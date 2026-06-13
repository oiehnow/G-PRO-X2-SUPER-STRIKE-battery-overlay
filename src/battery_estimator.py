"""배터리 잔량 샘플로부터 남은 사용 시간을 외삽한다.

마우스(및 LGSTrayEx)는 배터리 %만 보고하고 "몇 시간 남음"은 주지 않으므로,
(시각, %) 샘플을 누적해 시간당 방전율(%/h)을 구하고 남은시간을 계산한다.
표본이 부족하면 스펙 기준 배터리 수명을 폴백으로 사용한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# PRO X2 Superstrike 공칭 배터리 수명(시간). 표본이 모이기 전 폴백 기준선.
DEFAULT_FULL_LIFE_HOURS = 75.0  # 스펙 60~90h 의 중간값

# 방전율 추정에 필요한 최소 샘플 수와 최소 시간 간격(초).
MIN_SAMPLES = 2
MIN_SPAN_SECONDS = 60.0


@dataclass
class BatteryEstimator:
    """(timestamp_seconds, percent) 샘플을 받아 남은시간을 추정한다."""

    full_life_hours: float = DEFAULT_FULL_LIFE_HOURS
    max_samples: int = 240
    _samples: list[tuple[float, float]] = field(default_factory=list)

    def add_sample(self, timestamp: float, percent: float) -> None:
        """새 측정값 추가. 충전(%가 오름)이 감지되면 이력을 리셋한다."""
        percent = max(0.0, min(100.0, float(percent)))
        if self._samples:
            last_ts, last_pct = self._samples[-1]
            if timestamp <= last_ts:
                return  # 시간 역행/중복 무시
            if percent > last_pct + 1.0:
                # 충전되었거나 새 배터리 → 기존 방전 추세 무효
                self._samples.clear()
        self._samples.append((timestamp, percent))
        if len(self._samples) > self.max_samples:
            self._samples.pop(0)

    def discharge_rate_per_hour(self) -> float | None:
        """시간당 방전율(%/h). 추정 불가하면 None.

        최소제곱 직선 기울기를 사용하되, 방전(음의 기울기)일 때만 양수 비율로 반환.
        """
        if len(self._samples) < MIN_SAMPLES:
            return None
        first_ts = self._samples[0][0]
        last_ts = self._samples[-1][0]
        if last_ts - first_ts < MIN_SPAN_SECONDS:
            return None

        xs = [(ts - first_ts) / 3600.0 for ts, _ in self._samples]  # 시간 단위
        ys = [pct for _, pct in self._samples]
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        if denom == 0:
            return None
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
        rate = -slope  # 방전이면 slope<0 → rate>0
        if rate <= 0:
            return None  # 방전 추세 아님(평탄/충전)
        return rate

    def hours_remaining(self, current_percent: float | None = None) -> float:
        """남은 사용 시간(시간). 측정된 방전율 우선, 없으면 스펙 기준선 폴백."""
        if current_percent is None:
            if not self._samples:
                return self.full_life_hours
            current_percent = self._samples[-1][1]
        current_percent = max(0.0, min(100.0, float(current_percent)))

        rate = self.discharge_rate_per_hour()
        if rate is None:
            # 폴백: 공칭 수명에 현재 잔량 비율 적용
            return self.full_life_hours * (current_percent / 100.0)
        return current_percent / rate

    @property
    def sample_count(self) -> int:
        return len(self._samples)


def format_hours(hours: float) -> str:
    """시간(float)을 'Hh Mm' 형태 문자열로."""
    total_minutes = int(round(hours * 60))
    h, m = divmod(total_minutes, 60)
    if h <= 0:
        return f"{m}m"
    return f"{h}h {m}m"
