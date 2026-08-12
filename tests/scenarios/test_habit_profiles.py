"""Bölüm 100-113'teki kullanıcı Habit profil matrisinin uçtan uca doğrulaması.

Her test, gerçek bir kullanım deseninin Habit katmanınca doğru sınıflandırıldığını (PASS,
PENDING_EVIDENCE ya da NOT_HABIT) dışarıdan beklenen davranış üzerinden doğrular; Habit
katmanının kendi implementasyonunu tekrar etmez.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.config import default_engine_config
from awe.domain.enums import HabitDecision, LivenessState, ReasonCode
from awe.domain.series import OSeries
from awe.habit import evaluate_habit
from tests.support.builders import make_series

_CONFIG = default_engine_config().habit
_BASE = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def _series_on_days(
    day_offsets: list[int], *, sessions_per_day: int = 1, symbols: list[str] | None = None
) -> list[OSeries]:
    symbols = symbols or ["open_settings", "open_security"]
    series: list[OSeries] = []
    for day in day_offsets:
        for session_index in range(sessions_per_day):
            started = _BASE + timedelta(days=day, hours=session_index)
            series.append(
                make_series(
                    session_id=f"sess-{day}-{session_index}",
                    started_at=started,
                    action_keys=symbols,
                    series_suffix=f"{day}-{session_index}",
                )
            )
    return series


def test_daily_regular_usage_passes_as_habit():
    series = _series_on_days(list(range(30)))
    now = _BASE + timedelta(days=30)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS
    assert result.evidence.distinct_days == 30


def test_daily_usage_with_missing_days_still_passes():
    series = _series_on_days(list(range(20, 23)) + list(range(0, 20, 2)))
    now = _BASE + timedelta(days=30)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS


def test_high_frequency_daily_usage_is_not_mistaken_for_a_burst():
    series = _series_on_days(list(range(20)), sessions_per_day=7)
    now = _BASE + timedelta(days=20)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS
    assert result.evidence.organic_occurrences == 20 * 7


def test_weekly_cadence_is_not_rejected_for_low_daily_density():
    series = _series_on_days([0, 7, 14, 21, 28, 35, 42, 49])
    now = _BASE + timedelta(days=50)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS


def test_biweekly_cadence_passes_with_sufficient_evidence():
    series = _series_on_days([0, 14, 28, 42, 56, 70, 84, 98, 112])
    now = _BASE + timedelta(days=115)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS


def test_monthly_cadence_over_six_months_passes():
    series = _series_on_days([0, 30, 61, 92, 122, 153, 183])
    now = _BASE + timedelta(days=185)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS


def test_irregular_but_recurring_days_are_not_outright_rejected():
    series = _series_on_days([1, 4, 11, 18, 29, 43, 55])
    now = _BASE + timedelta(days=58)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS


def test_short_two_step_pair_repeated_daily_can_still_be_a_strong_habit():
    series = _series_on_days(list(range(30)), symbols=["A", "B"])
    now = _BASE + timedelta(days=30)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS


def test_one_day_burst_is_not_accepted_as_habit():
    series = _series_on_days([5], sessions_per_day=35)
    now = _BASE + timedelta(days=30)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.NOT_HABIT
    assert ReasonCode.ONE_DAY_BURST in result.reason_codes


def test_two_day_burst_followed_by_silence_is_not_accepted_as_habit():
    series = _series_on_days([5, 6], sessions_per_day=15)
    now = _BASE + timedelta(days=30)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.NOT_HABIT


def test_single_session_repetition_is_not_accepted_as_habit():
    series = [
        make_series(
            session_id="sess-1",
            started_at=_BASE + timedelta(minutes=index),
            action_keys=["A", "B"],
            series_suffix=str(index),
        )
        for index in range(50)
    ]
    now = _BASE + timedelta(days=1)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.NOT_HABIT
    assert ReasonCode.INSUFFICIENT_DISTINCT_SESSIONS in result.reason_codes


def test_stale_habit_still_passes_but_is_flagged_as_stale():
    series = _series_on_days(list(range(30)))
    now = _BASE + timedelta(days=200)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS
    assert result.evidence.liveness == LivenessState.STALE
    assert ReasonCode.STALE_BEHAVIOR in result.reason_codes


def test_revived_habit_after_long_gap_reads_as_live():
    series = _series_on_days(list(range(5)) + list(range(90, 96)))
    now = _BASE + timedelta(days=96)

    result = evaluate_habit("fam", series, now, "UTC", _CONFIG)

    assert result.decision == HabitDecision.PASS
    assert result.evidence.liveness == LivenessState.LIVE


def test_multiple_independent_habits_for_the_same_user_do_not_interfere():
    daily = _series_on_days(list(range(30)), symbols=["A", "B"])
    weekly = _series_on_days([0, 7, 14, 21, 28, 35, 42], symbols=["C", "D"])
    monthly = _series_on_days([0, 30, 61, 92, 122], symbols=["E", "F"])
    irregular = _series_on_days([1, 9, 22, 23, 40], symbols=["G", "H"])
    now = _BASE + timedelta(days=125)

    results = [
        evaluate_habit(name, series, now, "UTC", _CONFIG)
        for name, series in [
            ("daily", daily),
            ("weekly", weekly),
            ("monthly", monthly),
            ("irregular", irregular),
        ]
    ]

    assert all(r.decision == HabitDecision.PASS for r in results)
