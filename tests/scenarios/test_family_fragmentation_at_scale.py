"""50-100 session'lık karmaşık, gerçekçi bir tek-subject log'unda family fragmentation/explosion
ölçümü.

Bölüm 129'daki motor sağlığı metriklerinin (familiesPerSubject, ambiguousSeriesRate,
fragmentationRate) küçük ölçekte, tek bir ama YAPISAL OLARAK ZOR bir subject üzerinde ölçüldüğü
bir stres testi. `scripts/evaluate_engine.py`'nin büyük ölçekli koşumundan farkı: orada her
subject tek, temiz bir davranış sergiliyordu; burada TEK bir subject dört farklı davranışı
(bazıları ortak bir başlangıç adımını paylaşarak), gerçekçi gürültü (screen-view, misclick,
retry) ve kasıtlı olarak belirsiz kısa fragment'larla iç içe sergiliyor.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from awe.config import ProjectRegistry
from awe.persistence import Base, create_database_engine, create_session_factory, session_scope
from awe.persistence.models import FamilyRecord, SeriesRecord
from awe.risk import ResolverContract
from awe.services import analyze_subject, ingest_batch

_BASE = datetime(2026, 1, 1, 9, tzinfo=UTC)
_SUBJECT_ID = "complex_subject"

# İki davranış kasıtlı olarak aynı adımla ("open_settings") başlar -- ortak başlangıç
# ekranının discriminative weighting altında gerçek fragmentation'a yol açıp açmadığını da
# bu ölçüme dahil eder (bölüm 20/115).
_BEHAVIORS: dict[str, list[tuple[str, str]]] = {
    "password_reset": [
        ("open_settings", "route"),
        ("open_security", "route"),
        ("select_change_password", "select"),
        ("confirm_password_reset", "confirm"),
    ],
    "notification_settings": [
        ("open_settings", "route"),
        ("open_notifications", "route"),
        ("toggle_notifications", "select"),
    ],
    "profile_update": [
        ("open_profile", "route"),
        ("edit_profile_field", "input"),
        ("save_profile", "confirm"),
    ],
    "search_filter": [
        ("open_search", "route"),
        ("apply_filter", "select"),
    ],
}
_BEHAVIOR_WEIGHTS = {"password_reset": 1, "notification_settings": 1, "profile_update": 2, "search_filter": 6}


def _raw_event(
    session_id: str,
    event_id: str,
    timestamp: datetime,
    action_key: str,
    effect: str,
    *,
    role: str = "action",
    trigger: str = "button",
    status: str = "success",
) -> dict:
    return {
        "eventId": event_id,
        "projectId": "shopwave",
        "subjectId": _SUBJECT_ID,
        "sessionId": session_id,
        "timestamp": timestamp.isoformat(),
        "source": "client",
        "actionKey": action_key,
        "role": role,
        "effect": effect,
        "trigger": trigger,
        "screen": "app",
        "widget": None,
        "target": None,
        "status": status,
        "breaksEpisode": False,
        "metadata": {},
    }


def _generate_complex_subject_events(session_count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    behavior_names = list(_BEHAVIORS.keys())
    weights = [_BEHAVIOR_WEIGHTS[name] for name in behavior_names]

    events: list[dict] = []
    event_counter = 0
    day = 0

    def make_emit(session_id: str, day: int):
        minute = 0

        def emit(action_key: str, effect: str, **kwargs) -> None:
            nonlocal event_counter, minute
            event_id = f"evt-{event_counter}"
            event_counter += 1
            ts = _BASE + timedelta(days=day, minutes=minute)
            minute += 1
            events.append(_raw_event(session_id, event_id, ts, action_key, effect, **kwargs))

        return emit

    for session_index in range(session_count):
        day += rng.randint(0, 3)  # düzensiz gün aralığı -- gerçekçi kullanım deseni
        session_id = f"sess-{session_index}"
        behavior_name = rng.choices(behavior_names, weights=weights, k=1)[0]
        flow = _BEHAVIORS[behavior_name]
        emit = make_emit(session_id, day)

        if rng.random() < 0.4:
            # Uygulama yaşam-döngüsü sinyali: trigger=lifecycle + effect=update, ACTION/CONTEXT/
            # IGNORE sınıflandırmasında (bkz. awe.adapter.classification) hiçbir gruba girmediği
            # için IGNORE sayılır -- temiz action akışına hiç girmez.
            emit("app_foreground", "update", role="noise", trigger="lifecycle")
        if rng.random() < 0.3:
            # Ekran görüntüleme: trigger=automatic + effect=view -> CONTEXT (bkz. sınıflandırma
            # algoritması) -- action akışına girmez ama raw_observations'ta audit için kalır.
            emit("screen_view", "view", role="context", trigger="automatic")

        last_index = len(flow) - 1
        for step_index, (action_key, effect) in enumerate(flow):
            if rng.random() < 0.1 and step_index == 1:
                emit("wrong_screen", "route")
                emit("back_button", "navigate_back")
            if rng.random() < 0.08 and step_index == last_index:
                emit(action_key, effect, status="fail")
            emit(action_key, effect)

        # Kasıtlı olarak belirsiz, tamamlanmamış kısa bir fragment (bölüm 59'un gerçek
        # kullanımda da ortaya çıkabileceğini simüle eder): yalnızca ortak "open_settings"
        # adımıyla başlayıp hemen kesilen ayrı bir session.
        if rng.random() < 0.05:
            frag_session = f"sess-frag-{session_index}"
            frag_ts = _BASE + timedelta(days=day, hours=2)
            events.append(_raw_event(frag_session, f"evt-{event_counter}", frag_ts, "open_settings", "route"))
            event_counter += 1

    return events


def test_complex_realistic_log_measures_family_fragmentation_within_healthy_bounds():
    events = _generate_complex_subject_events(session_count=80, seed=2024)
    assert len(events) > 200  # gerçekten "büyük" bir log ürettiğimizi doğrula

    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    project_config = ProjectRegistry("config_examples").get("shopwave")

    with session_scope(factory) as session:
        outcomes = ingest_batch(session, project_config, "shopwave", events, _BASE)
        assert all(o.accepted for o in outcomes), [o for o in outcomes if not o.accepted][:3]

    now = _BASE + timedelta(days=400)
    with session_scope(factory) as session:
        analyze_subject(session, project_config, "shopwave", _SUBJECT_ID, ResolverContract.permissive(), now)

    with session_scope(factory) as session:
        families = list(
            session.execute(select(FamilyRecord).where(FamilyRecord.subject_id == _SUBJECT_ID)).scalars().all()
        )
        all_series = list(
            session.execute(select(SeriesRecord).where(SeriesRecord.subject_id == _SUBJECT_ID)).scalars().all()
        )

    total_series = len(all_series)
    ambiguous_series = [s for s in all_series if s.family_id is None and s.ambiguous_family_ids]
    unassigned_series = [s for s in all_series if s.family_id is None and not s.ambiguous_family_ids]
    family_supports = [sum(v["support"] for v in f.representative_variants) for f in families]
    singleton_families = [support for support in family_supports if support == 1]

    ambiguous_rate = len(ambiguous_series) / total_series if total_series else 0.0
    singleton_rate = len(singleton_families) / len(families) if families else 0.0

    print("\n--- Family fragmentation raporu (80 session, 4 gerçek davranış) ---")
    print(f"toplam event: {len(events)}  toplam O-Series: {total_series}")
    print(f"family sayısı: {len(families)}  (support dağılımı: {sorted(family_supports, reverse=True)})")
    print(f"ambiguous series: {len(ambiguous_series)} ({ambiguous_rate:.1%})")
    print(f"unassigned (çok kısa) series: {len(unassigned_series)}")
    print(f"singleton family oranı: {len(singleton_families)}/{len(families)} ({singleton_rate:.1%})")

    # sabit seed=2024 ile bu senaryo deterministik olarak şu sonucu üretir (manuel doğrulandı):
    # 4 gerçek davranışın her biri KENDİ tek family'sine toplanıyor (destek dağılımı büyükten
    # küçüğe [43, 17, 13, 7] -- search_filter/profile_update/password_reset/notification'ın
    # ağırlıklarıyla tutarlı) ve `screen_view` gürültü ön-eki family'yi BÖLMÜYOR, aynı family
    # içinde ikinci bir variant olarak kalıyor. Geri kalan 5 singleton family ise kasıtlı olarak
    # enjekte edilen, tek sembolden ("open_settings") ibaret belirsiz fragment'lardır -- bunlar
    # hem password_reset hem notification_settings ile aynı başlangıcı paylaştığından motor
    # bunları rastgele bir family'ye ZORLA eşlemek yerine kendi singleton family'lerinde
    # bırakıyor (min_symbols_to_seed_family altı/belirsiz durumlarda güvenli varsayılan
    # davranış). Yani 9 family = 4 gerçek davranış + 5 gerçekten ayırt edilemez fragment;
    # gerçek bir fragmentation/explosion YOK.
    assert len(families) == 9
    assert sorted(family_supports, reverse=True)[:4] == [43, 17, 13, 7]
    assert len(singleton_families) == 5
    assert ambiguous_rate == 0.0
    assert len(unassigned_series) == 0
