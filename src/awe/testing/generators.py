"""Deterministik sentetik event log üretici.

Her profil, gerçek bir kullanıcı davranış deseni için (günlük, haftalık, burst, gürültülü, vb.)
ground-truth bir Habit beklentisiyle birlikte, yeni ham event sözleşmesiyle (bölüm 4:
eventId/projectId/subjectId/sessionId/timestamp/actionKey/effect/trigger/source/screen/target/
status/duration) uyumlu ham event üretir.

Bu modül yalnızca test/evaluation amaçlıdır; üretim koduna (adapter, engine) bağımlılığı yoktur.

Eski tasarımdan kalan iki profil kasıtlı olarak kaldırılmıştır: `widget_rename` (artık `widget`
alanı yok — `screen` sembolün parçası olduğu için "kimlikten hariç tutulan alan" kavramının
analogu kalmadı) ve `parameter_drift` (FieldBinding recent-drift kavramı yeni tasarımda yok;
`target_variable` zaten aynı temel senaryoyu — hedefin değişkenliğini — kapsıyor).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from awe.domain.enums import HabitDecision

_STANDARD_FLOW: list[tuple[str, str]] = [
    ("open_dashboard", "route"),
    ("open_detail", "route"),
    ("select_option", "select"),
    ("confirm_action", "confirm"),
]
_SHORT_FLOW: list[tuple[str, str]] = [("quick_open", "route"), ("quick_action", "select")]
_LONG_FLOW: list[tuple[str, str]] = [
    ("open_dashboard", "route"),
    ("open_category", "route"),
    ("open_item", "route"),
    ("fill_field_a", "input"),
    ("fill_field_b", "input"),
    ("review_summary", "select"),
    ("confirm_action", "confirm"),
]


def _raw_event(
    project_id: str,
    subject_id: str,
    session_id: str,
    event_id: str,
    timestamp: datetime,
    action_key: str,
    effect: str,
    *,
    trigger: str = "button",
    screen: str = "app",
    target: str | None = None,
    status: str = "success",
) -> dict:
    return {
        "eventId": event_id,
        "projectId": project_id,
        "subjectId": subject_id,
        "sessionId": session_id,
        "timestamp": timestamp.isoformat(),
        "source": "client",
        "actionKey": action_key,
        "effect": effect,
        "trigger": trigger,
        "screen": screen,
        "target": target,
        "status": status,
        "duration": None,
    }


@dataclass(frozen=True, slots=True)
class _OccurrenceSpec:
    day: int
    minute_offset: int
    session_index: int
    target_ref: str | None = "item_1"
    add_noise: bool = False
    add_retry: bool = False
    final_status: str = "success"
    session_prefix: str = ""
    """Aynı subject için birden fazla bağımsız Habit üretilirken (bkz.
    `generate_multi_habit_subject`), farklı bileşenlerin aynı gün/session_index kombinasyonuna
    düşüp aynı session_id'yi paylaşmasını (ve böylece olay akışlarının birbirine karışmasını)
    önlemek için kullanılır."""


def _emit_occurrence(
    project_id: str,
    subject_id: str,
    occurrence_index: int,
    base_time: datetime,
    flow: list[tuple[str, str]],
    spec: _OccurrenceSpec,
) -> list[dict]:
    session_id = f"sess-{subject_id}-{spec.session_prefix}{spec.day}-{spec.session_index}"
    events: list[dict] = []
    step = 0

    def emit(action_key: str, effect: str, **kwargs) -> None:
        nonlocal step
        event_id = f"evt-{subject_id}-{occurrence_index}-{step}"
        ts = base_time + timedelta(days=spec.day, minutes=spec.minute_offset + step)
        events.append(_raw_event(project_id, subject_id, session_id, event_id, ts, action_key, effect, **kwargs))
        step += 1

    if spec.add_noise:
        # effect="none" bölüm 6.2'de koşulsuz IGNORE üretir; temiz action akışına hiç girmez
        # ve Family kimliğini etkilemez.
        emit("app_foreground", "none", trigger="automatic")

    last_index = len(flow) - 1
    for index, (action_key, effect) in enumerate(flow):
        if spec.add_retry and index == last_index:
            # `status` artık sınıflandırmayı etkilemez (bölüm 3 kural 4) — bu iki başarısız
            # deneme normalize edilip sıkıştırılmaz, exact sembol dizisine ayrı adım olarak
            # girer. Bu, retry-ağır bir davranışın "temiz" variant'tan ayrı, daha küçük bir
            # variant'a bölünmesine yol açar (bölüm 9.3 exact fragmentation) — kasıtlı kabul.
            emit(action_key, effect, status="fail")
            emit(action_key, effect, status="fail")

        target = spec.target_ref if (spec.target_ref and effect == "select") else None
        status = spec.final_status if index == last_index else "success"
        emit(action_key, effect, target=target, status=status)

    return events


@dataclass(frozen=True, slots=True)
class GeneratedSubject:
    project_id: str
    subject_id: str
    profile: str
    events: list[dict]
    expected_habit_decision: HabitDecision
    notes: str = ""


def _day_list(profile: str, rng: random.Random) -> list[_OccurrenceSpec]:
    if profile == "daily_regular":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(30)]
    if profile == "daily_missing_days":
        days = sorted(set(range(30)) - set(rng.sample(range(30), 8)))
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in days]
    if profile == "daily_high_frequency":
        specs = []
        for day in range(20):
            for session in range(rng.randint(5, 10)):
                specs.append(_OccurrenceSpec(day=day, minute_offset=session * 15, session_index=session))
        return specs
    if profile == "weekly_regular":
        return [_OccurrenceSpec(day=w * 7, minute_offset=0, session_index=0) for w in range(8)]
    if profile == "biweekly_regular":
        return [_OccurrenceSpec(day=i * 14, minute_offset=0, session_index=0) for i in range(9)]
    if profile == "monthly_regular":
        return [_OccurrenceSpec(day=i * 30, minute_offset=0, session_index=0) for i in range(7)]
    if profile == "irregular_recurring":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in (1, 4, 11, 18, 29, 43, 55)]
    if profile == "short_frequent":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(30)]
    if profile == "long_workflow":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(0, 30, 2)]
    if profile == "one_day_burst":
        return [_OccurrenceSpec(day=5, minute_offset=s * 5, session_index=s) for s in range(35)]
    if profile == "two_day_burst":
        return [_OccurrenceSpec(day=5, minute_offset=s * 5, session_index=s) for s in range(15)] + [
            _OccurrenceSpec(day=6, minute_offset=s * 5, session_index=s) for s in range(15)
        ]
    if profile == "single_session_repeater":
        # `_STANDARD_FLOW` 4 adımlıdır; ardışık occurrence'ların adımları arasında çakışma
        # olmaması için aralık adım sayısından büyük tutulur (aksi halde iki occurrence aynı
        # dakikaya düşüp order_session'da gerçek ama gereksiz bir zaman belirsizliği yaratır).
        return [_OccurrenceSpec(day=0, minute_offset=i * 6, session_index=0) for i in range(50)]
    if profile == "stale":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(30)]
    if profile == "revived":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(5)] + [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(95, 101)
        ]
    if profile == "noisy":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0, add_noise=True) for d in range(20)]
    if profile == "retry_heavy":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, add_retry=(d % 2 == 0)) for d in range(20)
        ]
    if profile == "target_variable":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, target_ref=f"item_{d % 7}") for d in range(20)
        ]
    raise ValueError(f"unknown profile: {profile}")


_EXPECTED_DECISION: dict[str, HabitDecision] = {
    "daily_regular": HabitDecision.HABIT_DETECTED,
    "daily_missing_days": HabitDecision.HABIT_DETECTED,
    "daily_high_frequency": HabitDecision.HABIT_DETECTED,
    "weekly_regular": HabitDecision.HABIT_DETECTED,
    "biweekly_regular": HabitDecision.HABIT_DETECTED,
    "monthly_regular": HabitDecision.HABIT_DETECTED,
    "irregular_recurring": HabitDecision.HABIT_DETECTED,
    "short_frequent": HabitDecision.HABIT_DETECTED,
    "long_workflow": HabitDecision.HABIT_DETECTED,
    "one_day_burst": HabitDecision.INSUFFICIENT_EVIDENCE,
    # Yeni MVP kapısı `distinct day >= 2` (bölüm 6.7) — eski `>= 3` eşiğinden düşürüldü. İki
    # farklı günde, sayısı ne olursa olsun, artık HABIT_DETECTED üretir; bu belgenin kendi
    # eşiğinin doğrudan sonucudur (yalnızca tek-gün burst'ü açıkça reddeder, bölüm 9.8).
    "two_day_burst": HabitDecision.HABIT_DETECTED,
    "single_session_repeater": HabitDecision.INSUFFICIENT_EVIDENCE,
    "stale": HabitDecision.HABIT_DETECTED,
    "revived": HabitDecision.HABIT_DETECTED,
    "noisy": HabitDecision.HABIT_DETECTED,
    "retry_heavy": HabitDecision.HABIT_DETECTED,
    "target_variable": HabitDecision.HABIT_DETECTED,
}

_FLOW_BY_PROFILE: dict[str, list[tuple[str, str]]] = {
    "short_frequent": _SHORT_FLOW,
    "long_workflow": _LONG_FLOW,
}

PROFILE_NAMES: tuple[str, ...] = tuple(_EXPECTED_DECISION.keys())


def generate_subject(
    profile: str,
    project_id: str,
    subject_id: str,
    seed: int,
    base_time: datetime,
) -> GeneratedSubject:
    rng = random.Random(seed)
    flow = _FLOW_BY_PROFILE.get(profile, _STANDARD_FLOW)
    specs = _day_list(profile, rng)

    events: list[dict] = []
    for occurrence_index, spec in enumerate(specs):
        events.extend(_emit_occurrence(project_id, subject_id, occurrence_index, base_time, flow, spec))

    return GeneratedSubject(
        project_id=project_id,
        subject_id=subject_id,
        profile=profile,
        events=events,
        expected_habit_decision=_EXPECTED_DECISION[profile],
    )


@dataclass(frozen=True, slots=True)
class MultiHabitSubject:
    project_id: str
    subject_id: str
    events: list[dict] = field(default_factory=list)
    component_profiles: tuple[str, ...] = ()


def generate_multi_habit_subject(
    project_id: str, subject_id: str, seed: int, base_time: datetime
) -> MultiHabitSubject:
    """Aynı kullanıcı için birbirinden bağımsız birden fazla Habit."""

    component_profiles = ("daily_regular", "weekly_regular", "monthly_regular", "irregular_recurring")
    flows = [
        [("open_a", "route"), ("open_a_detail", "route"), ("confirm_a", "confirm")],
        [("open_b", "route"), ("open_b_detail", "route"), ("confirm_b", "confirm")],
        [("open_c", "route"), ("open_c_detail", "route"), ("confirm_c", "confirm")],
        [("open_d", "route"), ("open_d_detail", "route"), ("confirm_d", "confirm")],
    ]

    rng = random.Random(seed)
    events: list[dict] = []
    for component_index, (profile, flow) in enumerate(zip(component_profiles, flows, strict=True)):
        specs = _day_list(profile, rng)
        for occurrence_index, spec in enumerate(specs):
            prefixed_spec = replace(spec, session_prefix=f"c{component_index}-")
            events.extend(
                _emit_occurrence(
                    project_id,
                    subject_id,
                    component_index * 1000 + occurrence_index,
                    base_time,
                    flow,
                    prefixed_spec,
                )
            )

    return MultiHabitSubject(
        project_id=project_id, subject_id=subject_id, events=events, component_profiles=component_profiles
    )
