#!/usr/bin/env python
"""`realistic_learnloop_probe.py` ile aynı veri setini kurar ama pipeline'ı manuel olarak
katman katman çalıştırıp HER variant için Anchor/Scope/Destination/Intent/Risk/Benefit
detayını basar -- yalnızca sonunda SELECTED olanı değil, INSUFFICIENT_EVIDENCE ve
UNSUPPORTED/AMBIGUOUS düşen her şeyi de gösterir.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from datetime import timedelta  # noqa: E402

from realistic_learnloop_probe import _BASE, _PROJECT, _SUBJECT, _build_events  # noqa: E402

from awe.adapter import build_observation  # noqa: E402
from awe.benefit import evaluate_benefit  # noqa: E402
from awe.config.project_config import load_project_config  # noqa: E402
from awe.domain.enums import HabitDecision, IntentState  # noqa: E402
from awe.episodes import build_episode_candidates  # noqa: E402
from awe.families import group_into_families  # noqa: E402
from awe.habit import evaluate_habit  # noqa: E402
from awe.ordering import group_by_session, order_session  # noqa: E402
from awe.persistence import Base, create_database_engine, create_session_factory  # noqa: E402
from awe.persistence.repository import fetch_all_observations, insert_event, insert_observation  # noqa: E402
from awe.planner import build_shortcut_intent, project_scope, resolve_anchor, resolve_destination  # noqa: E402
from awe.risk import evaluate_risk  # noqa: E402
from awe.series import extract_series  # noqa: E402
from awe.targeting import resolve_targets  # noqa: E402


def main() -> None:
    project_config = load_project_config(Path("config_examples/learnloop.yaml"))
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()

    now = _BASE + timedelta(days=32)
    for raw_event in _build_events():
        observation = build_observation(raw_event, project_config.mapping)
        insert_event(session, observation.project_id, observation.event_id, observation.subject_id, now, raw_event)
        insert_observation(session, observation)

    observations = fetch_all_observations(session, _PROJECT, _SUBJECT)

    all_series = []
    for _sid, session_observations in group_by_session(observations).items():
        ordered, confidence = order_session(session_observations)
        all_series.extend(extract_series(ordered, confidence))
    series_by_id = {s.series_id: s for s in all_series}

    engine_config = project_config.engine
    candidates = build_episode_candidates(all_series, engine_config.episode)
    candidates_by_id = {c.candidate_id: c for c in candidates}

    families = group_into_families(candidates)
    print(f"{len(all_series)} series, {len(candidates)} episode candidate, {len(families)} exact family\n")

    for family in families:
        symbol_str = " -> ".join(f"{a}[{scr}]" for a, _e, scr, _mv in family.symbols)
        print(f"FAMILY {family.family_id[:16]}  support={family.support}")
        print(f"  sembol dizisi: {symbol_str}")

        variants = resolve_targets(family, candidates_by_id)
        for variant in variants:
            print(f"  VARIANT {variant.variant_id[-16:]}  kind={variant.kind.value}  support={variant.support}")
            print(f"    fingerprint={variant.fingerprint}")

            assessment = evaluate_habit(
                variant, candidates_by_id, all_series, engine_config.timezone, engine_config.habit
            )
            reasons = [r.value for r in assessment.reason_codes]
            print(f"    habit={assessment.decision.value}  reasons={reasons}")
            if assessment.decision != HabitDecision.HABIT_DETECTED:
                continue
            ev = assessment.evidence
            print(
                f"    evidence: organic={ev.organic_occurrences} sessions={ev.distinct_sessions} "
                f"days={ev.distinct_days}"
            )
            print(
                f"    regularity: cadence={ev.cadence.value} mean_gap={ev.mean_gap_days:.1f}g "
                f"gap_regularity={ev.gap_regularity:.2f} support={ev.support_ratio:.2f} "
                f"({ev.distinct_days}/{ev.active_days_total})"
            )

            anchor = resolve_anchor(
                family.symbols, variant, candidates_by_id, series_by_id, engine_config.screen_evidence
            )
            reasons = [r.value for r in anchor.reason_codes]
            print(f"    anchor: symbol={anchor.symbol[0]} pos={anchor.position} strength={anchor.strength.value}")
            print(f"      status={anchor.status.value} reasons={reasons}")

            scope = project_scope(family.symbols, variant.variant_id, anchor)
            destination = resolve_destination(
                anchor, variant, candidates_by_id, series_by_id, engine_config.screen_evidence
            )
            reasons = [r.value for r in destination.reason_codes]
            print(
                f"    destination: resolved={destination.resolved} screen={destination.screen} reasons={reasons}"
            )

            intent = build_shortcut_intent(variant, anchor, scope, destination)
            reasons = [r.value for r in intent.reason_codes]
            print(f"    intent: state={intent.state.value} mode={intent.mode} target={intent.target}")
            print(f"      reasons={reasons}")

            if intent.state != IntentState.READY:
                continue
            risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, engine_config.risk)
            benefit = evaluate_benefit(intent, len(scope.included))
            print(f"    risk={risk.decision.value} reasons={[r.value for r in risk.reason_codes]}")
            print(
                f"    benefit: observed={benefit.observed_actions} planned={benefit.planned_actions} "
                f"saved={benefit.saved_actions} level={benefit.level.value}"
            )
        print()


if __name__ == "__main__":
    main()
