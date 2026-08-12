"""Habit kanıtının ham O-Series üyelerinden hesaplanması (bölüm 63-67)."""

from __future__ import annotations

import statistics
from datetime import date, datetime
from zoneinfo import ZoneInfo

from awe.config.engine_config import HabitConfig
from awe.domain.enums import LivenessState
from awe.domain.habit import HabitEvidence
from awe.domain.series import OSeries


def _local_date(moment: datetime, tz: ZoneInfo) -> date:
    return moment.astimezone(tz).date()


def _median_gap_days(sorted_dates: list[date]) -> float | None:
    if len(sorted_dates) < 3:
        return None
    gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
    return float(statistics.median(gaps))


def _regularity(sorted_dates: list[date], min_days: int) -> float | None:
    if len(sorted_dates) < min_days:
        return None
    gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
    mean_gap = statistics.mean(gaps)
    if mean_gap <= 0:
        return None
    coefficient_of_variation = statistics.pstdev(gaps) / mean_gap
    return 1.0 / (1.0 + coefficient_of_variation)


def _liveness(
    last_seen_at: datetime,
    now: datetime,
    median_gap_days: float | None,
    active_span_days: int,
    distinct_days: int,
    config: HabitConfig,
) -> tuple[float | None, LivenessState]:
    if median_gap_days is not None and median_gap_days > 0:
        expected_gap = median_gap_days
    elif distinct_days >= 2:
        expected_gap = active_span_days / max(distinct_days - 1, 1)
    else:
        expected_gap = None

    if expected_gap is None or expected_gap <= 0:
        return None, LivenessState.LIVE

    days_since_last = (now - last_seen_at).total_seconds() / 86400
    ratio = days_since_last / expected_gap
    if ratio <= config.liveness_watch_multiplier:
        state = LivenessState.LIVE
    elif ratio <= config.liveness_stale_multiplier:
        state = LivenessState.WATCH
    else:
        state = LivenessState.STALE
    return ratio, state


def _habit_strength(support_score: float, regularity: float | None, liveness: LivenessState) -> float:
    liveness_factor = {LivenessState.LIVE: 1.0, LivenessState.WATCH: 0.6, LivenessState.STALE: 0.3}[
        liveness
    ]
    regularity_component = regularity if regularity is not None else 0.5
    return round(support_score * 0.5 + regularity_component * 0.25 + liveness_factor * 0.25, 4)


def build_habit_evidence(
    organic_series: list[OSeries],
    shortcut_series_count: int,
    now: datetime,
    timezone_name: str,
    config: HabitConfig,
) -> HabitEvidence:
    tz = ZoneInfo(timezone_name)
    organic_count = len(organic_series)

    dates = [_local_date(s.started_at, tz) for s in organic_series]
    distinct_days_sorted = sorted(set(dates))
    distinct_days = len(distinct_days_sorted)
    distinct_sessions = len({s.session_id for s in organic_series})

    first_seen_at = min(s.started_at for s in organic_series)
    last_seen_at = max(s.started_at for s in organic_series)
    active_span_days = (distinct_days_sorted[-1] - distinct_days_sorted[0]).days + 1

    day_counts: dict[date, int] = {}
    for d in dates:
        day_counts[d] = day_counts.get(d, 0) + 1
    top_day_share = max(day_counts.values()) / organic_count

    session_counts: dict[str, int] = {}
    for s in organic_series:
        session_counts[s.session_id] = session_counts.get(s.session_id, 0) + 1
    top_session_share = max(session_counts.values()) / organic_count

    median_gap_days = _median_gap_days(distinct_days_sorted)
    regularity = _regularity(distinct_days_sorted, config.min_days_for_regularity)
    staleness_ratio, liveness = _liveness(
        last_seen_at, now, median_gap_days, active_span_days, distinct_days, config
    )

    support_score = organic_count / (organic_count + config.support_saturation_k)
    habit_strength = _habit_strength(support_score, regularity, liveness)

    return HabitEvidence(
        organic_occurrences=organic_count,
        distinct_sessions=distinct_sessions,
        distinct_days=distinct_days,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
        active_span_days=active_span_days,
        top_day_share=top_day_share,
        top_session_share=top_session_share,
        median_gap_days=median_gap_days,
        regularity=regularity,
        staleness_ratio=staleness_ratio,
        liveness=liveness,
        shortcut_utility_occurrences=shortcut_series_count,
        support_score=support_score,
        habit_strength=habit_strength,
    )
