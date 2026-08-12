#!/usr/bin/env python
"""Gerçekçi bir LearnLoop (eğitim uygulaması) kullanıcısının ham event geçmişini elle,
tasarlanmış gerçekçi düzensizlikle kurar ve gerçek ingestion -> analiz -> suggestion
zincirinden geçirir.

Bu script `awe.testing.generators`ı KULLANMAZ — bilinçli olarak: o modül algoritmanın kendi
mental modeline uyan temiz veri üretir. Buradaki veri, algoritmayı geçmesi için ayarlanmamıştır;
gerçek bir öğrencinin yapacağı türden dağınıklığı (farklı giriş yolu, yarıda kalan denemeler,
retry, yanlış kurs, saf gezinme) kasıtlı olarak içerir. Amaç algoritmayı zorlamak, memnun
etmek değil.

Kullanım:
    python scripts/realistic_learnloop_probe.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from awe.config.project_config import load_project_config  # noqa: E402
from awe.domain.enums import HabitDecision  # noqa: E402
from awe.persistence import Base, create_database_engine, create_session_factory  # noqa: E402
from awe.persistence.repository import fetch_all_observations  # noqa: E402
from awe.services import analyze_subject, ingest_event, list_subject_suggestions  # noqa: E402

_SUBJECT = "learner_207"
_PROJECT = "learnloop"
_BASE = datetime(2026, 1, 5, tzinfo=UTC)  # bir Pazartesi

Step = tuple[str, str, str | None, str | None, str, str, str]
"""(action, effect, screen, target, status, trigger, origin)"""


def _step(
    action: str,
    effect: str,
    screen: str | None,
    target: str | None = None,
    *,
    status: str = "ok",
    trigger: str = "tap",
    origin: str = "device",
) -> Step:
    return (action, effect, screen, target, status, trigger, origin)


# --- Gerçek davranış kalıpları -----------------------------------------------------------
# Kalıp A ("temiz"): dashboard -> my_courses -> course_detail -> lesson_player, hep aynı
# kurs (course_ds301 = "Veri Yapıları").
_PATTERN_A = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
]

# Kalıp A + bildirim kontrolü arada (gerçek kullanıcı önce bildirimlere bakar, SONRA
# alışkanlığına devam eder). `open_my_courses`in screen'i artık "notifications" -- Pattern
# A'daki "dashboard"dan FARKLI -- bu adım tek başına exact eşleşmeyi bozar, ama
# open_course->continue_lesson çekirdeği sıra-korumalı alt dizi olarak hâlâ yakalanabilmeli.
_PATTERN_A_NOTIF_DETOUR = [
    _step("check_notifications", "route", "dashboard"),
    _step("open_my_courses", "route", "notifications"),
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
]

# Kalıp A + retry: "continue_lesson" bir kere network hatasıyla başarısız olur, kullanıcı
# tekrar dener. `status` sınıflandırmayı etkilemez -- ikisi de ACTION'dır.
_PATTERN_A_RETRY = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301", status="error"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
]

# Yarıda kalan ziyaret: kullanıcı kursu açar ama derse devam etmeden uygulamadan çıkar
# (dikkati dağılır, telefonu kilitler vb.) -- gerçek loglarda çok sık görülen bir durum.
_PATTERN_INCOMPLETE = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ds301"),
]

# Yanlış kurs: aynı yapısal akış ama FARKLI kurs (course_algo210 = "Algoritmalar") --
# Target Resolver'ın kanıtı havuzlamaması gerekir.
_PATTERN_WRONG_COURSE = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_algo210"),
    _step("continue_lesson", "open", "course_detail", "course_algo210"),
]

# Kalıp B: push bildirimden doğrudan kurs sayfasına deep-link (dashboard'dan hiç geçmez).
# `screen=None` -- kullanıcı uygulamanın içinde değildi, sistem bildirimine dokundu.
_PATTERN_B_PUSH_DEEPLINK = [
    _step("open_course", "route", None, "course_ds301", trigger="push"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
]

# Saf gezinme gürültüsü: alışkanlıkla hiç ilgisi olmayan, tek seferlik keşif session'ları.
_NOISE_CATALOG_BROWSE = [
    _step("open_catalog", "route", "dashboard"),
    _step("open_course_preview", "route", "catalog", "course_ml450"),
]
_NOISE_PROFILE_CHECK = [
    _step("view_profile", "route", "dashboard"),
]
_NOISE_SWIPE_CAROUSEL = [
    _step("open_catalog", "route", "dashboard"),
    _step("swipe_carousel", "select", "catalog", trigger="swipe"),
]

# (gün_offset, dakika_of_day, session_no, kalıp, açıklama)
_TIMELINE: list[tuple[int, int, list[Step], str]] = [
    (0, 20 * 60 + 10, _PATTERN_A, "clean A"),
    (1, 13 * 60 + 5, _NOISE_PROFILE_CHECK, "noise: profile check (lunch break)"),
    (2, 21 * 60 + 40, _PATTERN_INCOMPLETE, "incomplete: distracted after opening course"),
    (3, 19 * 60 + 50, _PATTERN_A, "clean A"),
    (4, 22 * 60 + 5, _PATTERN_A_NOTIF_DETOUR, "A + notification detour"),
    (5, 8 * 60 + 30, _PATTERN_B_PUSH_DEEPLINK, "B: push deep-link (weekend morning)"),
    (7, 20 * 60 + 15, _PATTERN_A, "clean A"),
    (8, 19 * 60 + 45, _PATTERN_A, "clean A"),
    (9, 21 * 60 + 0, _NOISE_CATALOG_BROWSE, "noise: catalog browsing"),
    (10, 20 * 60 + 20, _PATTERN_A, "clean A"),
    (11, 22 * 60 + 30, _PATTERN_A_RETRY, "A + retry on continue_lesson"),
    (12, 19 * 60 + 55, _PATTERN_WRONG_COURSE, "wrong course (algo210)"),
    (14, 20 * 60 + 5, _PATTERN_A, "clean A"),
    (15, 21 * 60 + 15, _PATTERN_A_NOTIF_DETOUR, "A + notification detour"),
    (17, 19 * 60 + 40, _PATTERN_A, "clean A"),
    (18, 9 * 60 + 10, _PATTERN_B_PUSH_DEEPLINK, "B: push deep-link (weekend morning)"),
    (19, 20 * 60 + 50, _PATTERN_INCOMPLETE, "incomplete: distracted after opening course"),
    (20, 21 * 60 + 5, _NOISE_SWIPE_CAROUSEL, "noise: carousel swipe, no course opened"),
    (21, 20 * 60 + 0, _PATTERN_A, "clean A"),
    (22, 22 * 60 + 0, _PATTERN_A_RETRY, "A + retry on continue_lesson"),
    (24, 19 * 60 + 35, _PATTERN_A, "clean A"),
    (25, 20 * 60 + 45, _PATTERN_A_NOTIF_DETOUR, "A + notification detour"),
    (28, 20 * 60 + 25, _PATTERN_A, "clean A"),
    (30, 8 * 60 + 50, _PATTERN_B_PUSH_DEEPLINK, "B: push deep-link (weekend morning)"),
]


def _build_events() -> list[dict]:
    events = []
    for session_index, (day, minute, steps, _label) in enumerate(_TIMELINE):
        session_id = f"sess-{session_index:03d}"
        for step_index, (action, effect, screen, target, status, trigger, origin) in enumerate(steps):
            timestamp = _BASE + timedelta(days=day, minutes=minute + step_index * 2)
            events.append(
                {
                    "eventUid": f"evt-{session_index:03d}-{step_index}",
                    "app": _PROJECT,
                    "learnerId": _SUBJECT,
                    "sessionUid": session_id,
                    "occurredAt": timestamp.isoformat(),
                    "actionName": action,
                    "screenName": screen,
                    "structuralEffect": effect,
                    "inputMethod": trigger,
                    "origin": origin,
                    "resultState": status,
                    "objectId": target,
                    "durationMs": None,
                }
            )
            # Her ACTION'dan sonra gerçekçi bir view event'i (ekranın gerçekten göründüğüne
            # dair kanıt) -- Screen Transition Evidence bunsuz hiçbir zaman STABLE bulamaz.
            if screen is not None or action != "swipe_carousel":
                view_screen = {
                    "open_my_courses": "my_courses",
                    "open_course": "course_detail",
                    "continue_lesson": "lesson_player",
                    "check_notifications": "notifications",
                    "open_catalog": "catalog",
                    "open_course_preview": "course_preview",
                    "view_profile": "profile",
                }.get(action)
                if view_screen:
                    view_ts = timestamp + timedelta(seconds=30)
                    events.append(
                        {
                            "eventUid": f"evt-{session_index:03d}-{step_index}-view",
                            "app": _PROJECT,
                            "learnerId": _SUBJECT,
                            "sessionUid": session_id,
                            "occurredAt": view_ts.isoformat(),
                            "actionName": f"{view_screen}_shown",
                            "screenName": view_screen,
                            "structuralEffect": "view",
                            "inputMethod": "tap",
                            "origin": "lifecycle",
                            "resultState": status,
                            "objectId": None,
                            "durationMs": None,
                        }
                    )
    return events


def main() -> None:
    project_config = load_project_config(Path("config_examples/learnloop.yaml"))
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()

    events = _build_events()
    now = _BASE + timedelta(days=32)

    rejected = []
    for raw_event in events:
        outcome = ingest_event(session, project_config, _PROJECT, raw_event, now)
        if not outcome.accepted and not outcome.duplicate:
            rejected.append((raw_event["eventUid"], outcome.error))

    print("=== Ingestion ===")
    print(f"{len(events)} ham event uretildi, {len(rejected)} reddedildi")
    for event_id, error in rejected:
        print(f"  REJECTED {event_id}: {error}")

    observations = fetch_all_observations(session, _PROJECT, _SUBJECT)
    print(f"{len(observations)} observation kabul edildi")
    print(f"{len(_TIMELINE)} session, {len({d for d, *_ in _TIMELINE})} farkli gun")

    summary = analyze_subject(session, project_config, _PROJECT, _SUBJECT, now)
    session.commit()

    print("\n=== Analiz Sonucu ===")
    print(f"series_count={summary.series_count}  variant_count={len(summary.variants)}")

    detected = [v for v in summary.variants if v.habit_decision == HabitDecision.HABIT_DETECTED]
    insufficient = [v for v in summary.variants if v.habit_decision != HabitDecision.HABIT_DETECTED]
    print(f"HABIT_DETECTED: {len(detected)}   INSUFFICIENT_EVIDENCE: {len(insufficient)}")
    for variant in summary.variants:
        print(
            f"  {variant.variant_key[:24]}...  {variant.habit_decision.value:22s}  "
            f"suggestion={variant.suggestion_state}"
        )

    suggestions = list_subject_suggestions(session, _PROJECT, _SUBJECT)
    print(f"\n=== Uretilen Oneriler ({len(suggestions)}) ===")
    for suggestion in suggestions:
        intent = suggestion.intent
        print(f"  state={suggestion.state}")
        print(f"    mode={intent.mode}  destination={intent.destination_screen}  target={intent.target}")
        print(f"    requires_confirmation={intent.requires_user_confirmation}")
        print(
            f"    risk={intent.risk_decision}  benefit_saved={intent.benefit_saved_actions}  "
            f"benefit_level={intent.benefit_level}"
        )
        print(f"    reason_codes={suggestion.reason_codes}")


if __name__ == "__main__":
    main()
