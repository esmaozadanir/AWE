#!/usr/bin/env python
"""AWE motorunun TÜM katmanlarını, motora göre AYARLANMAMIŞ, canlı event loglarına benzemesi
için tasarlanmış geniş bir davranış çeşitliliğiyle stres testine tabi tutar.

Kullanıcının açık isteği: "canlı event loglarına çok benzeyen kullanıcı davranışları üret ...
aklına gelebilecek tüm senaryoları ekle ... motoruma uydurmaya çalışma, motor testi için
kullanılacak objektif bir veri seti olsun."

`scripts/realistic_learnloop_probe.py`den FARKI: o script tek bir alışkanlığı (continue_lesson)
ve önceki turlarda bulunan spesifik regresyonları hedefliyordu. Bu script kasıtlı olarak DAHA
GENİŞ: birden fazla PARALEL, bağımsız alışkanlık; yapısal olarak hiçbir zaman "alışkanlık"
SAYILAMAYACAK kadar değişken hedefli davranışlar (her seferinde farklı quiz/thread/arama);
kısa action-surface akışlar; tek seferlik gürültü; aynı timestamp'te belirsiz event'ler; aynı
action için bazen mevcut bazen HİÇ gönderilmeyen target alanı; ve TEK bir uzun, çok-amaçlı,
gürültülü session -- hepsi aynı subject'te, aynı zaman çizelgesinde.

Hiçbir sonuç önceden tahmin edilip buna göre veri ayarlanmadı. Gerçek ingest_event/
analyze_subject/list_subject_suggestions'tan geçirilip NE ÇIKARSA raporlanır -- iyi, kötü ya
da beklenmeyen.

Kullanım:
    python scripts/engine_stress_test.py
"""

from __future__ import annotations

import json
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from awe.config.project_config import load_project_config  # noqa: E402
from awe.domain.enums import HabitDecision  # noqa: E402
from awe.persistence import Base, create_database_engine, create_session_factory  # noqa: E402
from awe.persistence.repository import fetch_all_observations  # noqa: E402
from awe.services import analyze_subject, ingest_event, list_subject_suggestions  # noqa: E402

_SUBJECT = "learner_512"
_PROJECT = "learnloop"
_BASE = datetime(2026, 1, 5, tzinfo=UTC)  # bir Pazartesi
_RNG = random.Random(20260114)  # yalnızca zamanlama jitter'ı için -- yapısal desenler elle

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


# === 1) İki BAĞIMSIZ, paralel "temiz" ders devam etme alışkanlığı ==============================
# Aynı kullanıcı iki farklı kursu paralel takip ediyor -- ikisinin de bağımsız tespit edilmesi,
# birbirini bozmaması beklenir (endpoint-hypothesis tasarımının asıl amacı).
_PATTERN_DS301_CONTINUE = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
]
_PATTERN_DB220_CONTINUE = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_db220"),
    _step("continue_lesson", "open", "course_detail", "course_db220"),
]

# Aynı akış ama double-tap / UI gecikmesi -- continue_lesson iki kez loglanıyor. Ana 3 adımlık
# family'den AYRI bir 4 adımlık exact family oluşturur (bilinçli, kabul edilmiş fragmentation).
_PATTERN_DS301_CONTINUE_DOUBLE_TAP = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
]

# Yanlış kurs -- yapısal olarak aynı ama FARKLI hedef, kanıt havuzlanmamalı.
_PATTERN_WRONG_COURSE = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_algo210"),
    _step("continue_lesson", "open", "course_detail", "course_algo210"),
]


# === 2) Ders içi NOT ALMA -- continue_lesson'a eklenen, KENDİ target'ı olmayan bir alt-akış ====
_PATTERN_NOTE_TAKING = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
    _step("open_notes", "route", "lesson_player"),
    _step("save_note", "create", "notes_panel"),
]

# Slayt indirme -- kısa (2 adım), action-surface (download outcome-evidence ama route/open
# değil) -- Benefit'te muhtemelen hiç tasarruf üretmeyecek kadar kısa (planned=2).
_PATTERN_DOWNLOAD_SLIDES = [
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("download_slides", "download", "course_detail", "course_ds301"),
]


# === 3) YAPISAL OLARAK asla "alışkanlık" sayılamayacak kadar değişken hedefli davranışlar =======
# Her hafta FARKLI bir quiz -- gerçek hayatta bu GERÇEK bir alışkanlık (her hafta quiz çözüyor)
# ama exact-target eşleştirmesi hiçbir zaman iki occurrence'ı aynı fingerprint'e sokmayacağı
# için motor bunu YAPISAL OLARAK tespit edemez. Bilerek dahil edildi -- motora uydurmak yerine
# gerçek bir sınırı dürüstçe göstermek için.
def _quiz_pattern(week_number: int) -> list[Step]:
    quiz_id = f"quiz_ds301_w{week_number}"
    return [
        _step("open_my_courses", "route", "dashboard"),
        _step("open_course", "route", "my_courses", "course_ds301"),
        _step("start_quiz", "route", "course_detail", quiz_id),
        _step("submit_quiz", "submit", "quiz_player", quiz_id),
    ]


# Forum'da farklı thread'lere yanıt -- aynı sebepten yapısal olarak tespit edilemez.
def _forum_pattern(thread_number: int) -> list[Step]:
    thread_id = f"thread_{thread_number}"
    return [
        _step("open_forum", "route", "dashboard"),
        _step("open_thread", "route", "forum", thread_id),
        _step("post_reply", "submit", "thread_detail", thread_id),
    ]


# Kurs arama -- her sorgu farklı, aynı sebepten tespit edilemez.
def _search_pattern(query_number: int) -> list[Step]:
    return [
        _step("open_catalog", "route", "dashboard"),
        _step("search_courses", "filter", "catalog", f"query_{query_number}"),
    ]


# === 4) Tek seferlik / nadir davranışlar -- HABIT_DETECTED OLMAMALI =============================
_PATTERN_SETTINGS_PASSWORD = [
    _step("open_settings", "route", "dashboard"),
    _step("change_password", "update", "settings"),
]
_PATTERN_SETTINGS_PROFILE = [
    _step("open_settings", "route", "dashboard"),
    _step("update_profile", "update", "settings"),
]
_PATTERN_ABANDONED = [
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ml450"),
]


# === 5) Tek bir UZUN, ÇOK-AMAÇLI, gürültülü session ============================================
# Bildirim kontrolü + alakasız katalog göz atma (kendi hedefli, "gürültü") + ders devamı + not
# alma + slayt indirme + forum yanıtı -- hepsi TEK session'da. Bu, son iki turun segmentasyon
# çalışmasının asıl motive edici senaryosudur: chunk artık sınırsız, TEK session'da birden
# fazla strong pozisyon var. NOT: erken gelen open_course_preview(course_ml450) kendi target'ını
# taşıdığı için, SONRASINDAKİ her önek (course_ds301, thread_77 dahil) bu session'ın kendi
# içinde VARIABLE_TARGET olarak damgalanıp reddedilecek -- prefix'ler HER ZAMAN session başından
# başladığı için erken, alakasız hedefli bir gürültü adımı kendinden SONRAKİ her hipotezi
# "kirletir". Bu, önceki turlarda kapatılan (trailing içerik, ayrı session'lar) riskten FARKLI,
# hâlâ açık bir sınır -- bilerek buraya kondu, gizlenmedi.
_PATTERN_LONG_MIXED_SESSION = [
    _step("check_notifications", "route", "dashboard"),
    _step("open_catalog", "route", "notifications"),
    _step("open_course_preview", "route", "catalog", "course_ml450"),
    _step("open_my_courses", "route", "dashboard"),
    _step("open_course", "route", "my_courses", "course_ds301"),
    _step("continue_lesson", "open", "course_detail", "course_ds301"),
    _step("open_notes", "route", "lesson_player"),
    _step("save_note", "create", "notes_panel"),
    _step("download_slides", "download", "lesson_player", "course_ds301"),
    _step("open_forum", "route", "dashboard"),
    _step("open_thread", "route", "forum", "thread_77"),
    _step("post_reply", "submit", "thread_detail", "thread_77"),
]


# (gün_offset, dakika_of_day, session_no, kalıp, açıklama)
_TIMELINE: list[tuple[int, int, list[Step], str]] = []


def _add(day: int, minute: int, steps: list[Step], label: str) -> None:
    _TIMELINE.append((day, minute, steps, label))


# --- Zaman çizelgesi kurulumu: ~10 hafta (70 gün), elle tasarlanmış düzensiz aralıklarla -------
_EVENING = 20 * 60  # 20:00
_LUNCH = 13 * 60
_MORNING = 8 * 60 + 30

for week in range(10):
    week_start = week * 7
    # ds301: haftada 2-3 kez, düzensiz günlerde (her hafta aynı gün DEĞİL -- gerçekçi jitter).
    for offset in _RNG.sample(range(7), k=_RNG.choice([2, 2, 3])):
        _add(week_start + offset, _EVENING + _RNG.randint(-45, 45), _PATTERN_DS301_CONTINUE, "clean ds301")
    # db220: haftada 1-2 kez, ds301'den bağımsız günlerde, 3. haftadan itibaren başlıyor
    # (kullanıcı sonradan ikinci kursa kaydolmuş gibi).
    if week >= 3:
        for offset in _RNG.sample(range(7), k=_RNG.choice([1, 1, 2])):
            _add(week_start + offset, _EVENING + _RNG.randint(-60, 60), _PATTERN_DB220_CONTINUE, "clean db220")
    # Haftalık quiz -- her hafta FARKLI hedef.
    _add(
        week_start + _RNG.randint(4, 6),
        _LUNCH + _RNG.randint(-30, 30),
        _quiz_pattern(week),
        "weekly quiz (varying target)",
    )
    # Forum -- haftada ~%60 ihtimalle, farklı thread.
    if _RNG.random() < 0.6:
        _add(
            week_start + _RNG.randint(0, 6),
            _EVENING + _RNG.randint(-90, 90),
            _forum_pattern(week * 3 + _RNG.randint(0, 2)),
            "forum reply (varying target)",
        )
    # Arama -- haftada ~%40 ihtimalle.
    if _RNG.random() < 0.4:
        _add(
            week_start + _RNG.randint(0, 6),
            _MORNING + _RNG.randint(-60, 200),
            _search_pattern(week),
            "course search (varying target)",
        )

# Not alma + slayt indirme: seyrek, birkaç kez.
for day in (5, 18, 33, 47, 61):
    _add(day, _EVENING + _RNG.randint(-30, 30), _PATTERN_NOTE_TAKING, "note-taking sub-flow")
for day in (9, 24, 40, 58):
    _add(day, _EVENING + _RNG.randint(-30, 30), _PATTERN_DOWNLOAD_SLIDES, "slide download")

# Double-tap / UI lag: 2 kez.
_add(15, _EVENING + 10, _PATTERN_DS301_CONTINUE_DOUBLE_TAP, "ds301 continue, double-tapped")
_add(52, _EVENING - 5, _PATTERN_DS301_CONTINUE_DOUBLE_TAP, "ds301 continue, double-tapped")

# Yanlış kurs: 2 kez.
_add(11, _EVENING + 20, _PATTERN_WRONG_COURSE, "wrong course (algo210)")
_add(44, _EVENING - 15, _PATTERN_WRONG_COURSE, "wrong course (algo210)")

# Tek seferlik ayarlar + terk edilmiş session'lar.
_add(7, _LUNCH, _PATTERN_SETTINGS_PASSWORD, "one-off: change password")
_add(29, _LUNCH + 15, _PATTERN_SETTINGS_PROFILE, "one-off: update profile")
_add(20, _MORNING, _PATTERN_ABANDONED, "abandoned: rare course glance")
_add(38, _MORNING + 30, _PATTERN_ABANDONED, "abandoned: rare course glance")
_add(63, _LUNCH - 20, _PATTERN_ABANDONED, "abandoned: rare course glance")

# Uzun, çok-amaçlı, gürültülü session -- 3 kez (kendi başına habit oluşturabiliyor mu diye).
_add(13, _EVENING + 30, _PATTERN_LONG_MIXED_SESSION, "LONG mixed-goal session")
_add(35, _EVENING + 40, _PATTERN_LONG_MIXED_SESSION, "LONG mixed-goal session")
_add(59, _EVENING + 35, _PATTERN_LONG_MIXED_SESSION, "LONG mixed-goal session")

_TIMELINE.sort(key=lambda entry: (entry[0], entry[1]))


def _build_events() -> list[dict]:
    events = []
    view_screen = {
        "open_my_courses": "my_courses",
        "open_course": "course_detail",
        "continue_lesson": "lesson_player",
        "check_notifications": "notifications",
        "open_catalog": "catalog",
        "open_course_preview": "course_preview",
        "open_notes": "notes_panel",
        "save_note": "notes_panel",
        "download_slides": "course_detail",
        "open_forum": "forum",
        "open_thread": "thread_detail",
        "post_reply": "thread_detail",
        "start_quiz": "quiz_player",
        "submit_quiz": "quiz_result",
        "search_courses": "catalog",
        "open_settings": "settings",
    }

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
            shown = view_screen.get(action)
            if shown:
                view_ts = timestamp + timedelta(seconds=30)
                events.append(
                    {
                        "eventUid": f"evt-{session_index:03d}-{step_index}-view",
                        "app": _PROJECT,
                        "learnerId": _SUBJECT,
                        "sessionUid": session_id,
                        "occurredAt": view_ts.isoformat(),
                        "actionName": f"{shown}_shown",
                        "screenName": shown,
                        "structuralEffect": "view",
                        "inputMethod": "tap",
                        "origin": "lifecycle",
                        "resultState": status,
                        "objectId": None,
                        "durationMs": None,
                    }
                )

    # --- Özel durum 1: aynı timestamp'te 2 FARKLI ACTION (ambiguity barrier testi) -------------
    # Gerçek hayatta analytics SDK'sinin toplu (batch) gönderdiği, saat çözünürlüğü aynı gelen
    # iki bağımsız tıklama gibi -- hangisinin önce olduğu bilinemez, motor bu grubu hiçbir
    # chunk'ın step dizisine sokmamalı.
    collision_ts = (_BASE + timedelta(days=42, minutes=_EVENING)).isoformat()
    events.append(
        {
            "eventUid": "evt-collision-a",
            "app": _PROJECT,
            "learnerId": _SUBJECT,
            "sessionUid": "sess-collision",
            "occurredAt": collision_ts,
            "actionName": "open_course",
            "screenName": "my_courses",
            "structuralEffect": "route",
            "inputMethod": "tap",
            "origin": "device",
            "resultState": "ok",
            "objectId": "course_ds301",
            "durationMs": None,
        }
    )
    events.append(
        {
            "eventUid": "evt-collision-b",
            "app": _PROJECT,
            "learnerId": _SUBJECT,
            "sessionUid": "sess-collision",
            "occurredAt": collision_ts,
            "actionName": "open_settings",
            "screenName": "dashboard",
            "structuralEffect": "route",
            "inputMethod": "tap",
            "origin": "device",
            "resultState": "ok",
            "objectId": None,
            "durationMs": None,
        }
    )

    # --- Özel durum 2: aynı action, bazen target ALANI HİÇ YOK (null değil, anahtar eksik) -----
    # Gerçek hayatta eski bir app sürümünün bu alanı hiç göndermemesi gibi -- `objectId` null
    # DEĞİL, sözlükte hiç YOK. quality.missing_target_field=True ile işaretlenmeli,
    # UNKNOWN_TARGET'a yol açmalı.
    for i, day in enumerate((16, 31, 55)):
        ts = _BASE + timedelta(days=day, minutes=_EVENING + 12)
        raw = {
            "eventUid": f"evt-missingtarget-{i}",
            "app": _PROJECT,
            "learnerId": _SUBJECT,
            "sessionUid": f"sess-missingtarget-{i}",
            "occurredAt": ts.isoformat(),
            "actionName": "open_course",
            "screenName": "my_courses",
            "structuralEffect": "route",
            "inputMethod": "tap",
            "origin": "device",
            "resultState": "ok",
            "durationMs": None,
            # objectId BİLEREK YOK.
        }
        events.append(raw)
        ts2 = ts + timedelta(minutes=2)
        events.append(
            {
                "eventUid": f"evt-missingtarget-{i}-continue",
                "app": _PROJECT,
                "learnerId": _SUBJECT,
                "sessionUid": f"sess-missingtarget-{i}",
                "occurredAt": ts2.isoformat(),
                "actionName": "continue_lesson",
                "screenName": "course_detail",
                "structuralEffect": "open",
                "inputMethod": "tap",
                "origin": "device",
                "resultState": "ok",
                "objectId": "course_ds301",
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
    now = _BASE + timedelta(days=72)

    events_path = Path(__file__).resolve().parent.parent / "scratch" / "engine_stress_test_events.json"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"=== Veri seti ===\n{len(events)} ham event -> {events_path} (git'e girmez)\n")

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
    distinct_days = len({d for d, *_ in _TIMELINE})
    print(f"{len(_TIMELINE) + 4} session (ozel durumlar dahil), {distinct_days} farkli gun (ana zaman cizelgesi)")

    summary = analyze_subject(session, project_config, _PROJECT, _SUBJECT, now)
    session.commit()

    print("\n=== Analiz Sonucu ===")
    print(f"series_count={summary.series_count}  variant_count={len(summary.variants)}")

    detected = [v for v in summary.variants if v.habit_decision == HabitDecision.HABIT_DETECTED]
    insufficient = [v for v in summary.variants if v.habit_decision != HabitDecision.HABIT_DETECTED]
    print(f"HABIT_DETECTED: {len(detected)}   INSUFFICIENT_EVIDENCE: {len(insufficient)}")
    for variant in summary.variants:
        print(
            f"  {variant.variant_key[:26]}...  {variant.habit_decision.value:22s}  "
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
