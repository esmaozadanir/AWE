#!/usr/bin/env python
"""Büyük ölçekli sentetik değerlendirme (bölüm 126-129).

100+ subject / 10.000+ event üzerinde motoru gerçek pipeline'dan (ingestion → analiz) geçirir,
Habit kararlarını ground truth ile karşılaştırıp precision/recall/F1 hesaplar ve motor sağlık
metriklerini raporlar. Sonuç hem konsola hem de `--report` ile verilen JSON dosyasına yazılır.

Kullanım:
    python scripts/evaluate_engine.py --subjects-per-profile 6 --multi-habit-subjects 10
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import func, select  # noqa: E402

from awe.config import ProjectRegistry  # noqa: E402
from awe.domain.enums import HabitDecision, PlanType, RiskDecisionType  # noqa: E402
from awe.persistence import Base, create_database_engine, create_session_factory, session_scope  # noqa: E402
from awe.persistence.models import (  # noqa: E402
    FamilyRecord,
    HabitEvaluationRecord,
    PlanCandidateRecord,
    SeriesRecord,
    SuggestionRecord,
)
from awe.risk import ResolverContract  # noqa: E402
from awe.services import analyze_subject, ingest_batch  # noqa: E402
from awe.testing import PROFILE_NAMES, generate_multi_habit_subject, generate_subject  # noqa: E402

_PROJECTS = (
    "shopwave",
    "socialpulse",
    "financepilot",
    "healthtrack",
    "wanderly",
    "streamboxx",
)
"""Sentetik üretici, ShopWave'in canonical-benzeri raw event şeklini (eventId/projectId/...)
üretir; bu 6 proje aynı şekli paylaşır (bölüm 121'in domain portability iddiası — aynı Core,
farklı iş sözlükleriyle). LearnLoop ve TaskFlow kasıtlı olarak FARKLI bir ham telemetry şekli
kullanır (bölüm 32'nin adapter portability gereksinimi) ve bu nedenle ayrı adanmış testlerle
(`tests/integration/test_pipeline_end_to_end.py`) doğrulanır; jenerik üreticiye dahil edilmez."""
_BASE_TIME = datetime(2026, 1, 1, 9, tzinfo=UTC)
_ANALYSIS_NOW = _BASE_TIME + timedelta(days=200)


def _build_dataset(factory, subjects_per_profile: int, multi_habit_subjects: int, seed_base: int):
    registry = ProjectRegistry("config_examples")
    project_cycle = itertools.cycle(_PROJECTS)
    seed = seed_base

    single_subjects: list[tuple[str, str, HabitDecision]] = []
    multi_subjects: list[tuple[str, str, int]] = []
    total_events = 0

    for profile in PROFILE_NAMES:
        for index in range(subjects_per_profile):
            project_id = next(project_cycle)
            project_config = registry.get(project_id)
            subject_id = f"{profile}_{index}"
            generated = generate_subject(profile, project_id, subject_id, seed, _BASE_TIME)
            seed += 1
            with session_scope(factory) as session:
                outcomes = ingest_batch(session, project_config, project_id, generated.events, _BASE_TIME)
                assert all(o.accepted for o in outcomes)
            total_events += len(generated.events)
            single_subjects.append((project_id, subject_id, generated.expected_habit_decision))

    for index in range(multi_habit_subjects):
        project_id = next(project_cycle)
        project_config = registry.get(project_id)
        subject_id = f"multi_{index}"
        generated = generate_multi_habit_subject(project_id, subject_id, seed, _BASE_TIME)
        seed += 1
        with session_scope(factory) as session:
            outcomes = ingest_batch(session, project_config, project_id, generated.events, _BASE_TIME)
            assert all(o.accepted for o in outcomes)
        total_events += len(generated.events)
        multi_subjects.append((project_id, subject_id, len(generated.component_profiles)))

    return single_subjects, multi_subjects, total_events


def _analyze_all(factory, single_subjects, multi_subjects):
    registry = ProjectRegistry("config_examples")
    resolver = ResolverContract.permissive()

    single_results = []
    for project_id, subject_id, expected in single_subjects:
        project_config = registry.get(project_id)
        with session_scope(factory) as session:
            summary = analyze_subject(session, project_config, project_id, subject_id, resolver, _ANALYSIS_NOW)
        actual = summary.families[0].habit_decision if summary.families else HabitDecision.PENDING_EVIDENCE
        single_results.append(
            {
                "project_id": project_id,
                "subject_id": subject_id,
                "profile": subject_id.rsplit("_", 1)[0],
                "expected": expected.value,
                "actual": actual.value,
                "correct": actual == expected,
                "family_count": len(summary.families),
            }
        )

    multi_results = []
    for project_id, subject_id, expected_family_count in multi_subjects:
        project_config = registry.get(project_id)
        with session_scope(factory) as session:
            summary = analyze_subject(session, project_config, project_id, subject_id, resolver, _ANALYSIS_NOW)
        passing = sum(1 for f in summary.families if f.habit_decision == HabitDecision.PASS)
        multi_results.append(
            {
                "project_id": project_id,
                "subject_id": subject_id,
                "expected_family_count": expected_family_count,
                "actual_family_count": len(summary.families),
                "passing_family_count": passing,
                "correct": passing == expected_family_count,
            }
        )

    return single_results, multi_results


def _classification_metrics(single_results: list[dict]) -> dict:
    tp = sum(1 for r in single_results if r["expected"] == "pass" and r["actual"] == "pass")
    fn = sum(1 for r in single_results if r["expected"] == "pass" and r["actual"] != "pass")
    fp = sum(1 for r in single_results if r["expected"] != "pass" and r["actual"] == "pass")
    tn = sum(1 for r in single_results if r["expected"] != "pass" and r["actual"] != "pass")

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if (precision and recall) else None

    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1}


def _per_profile_breakdown(single_results: list[dict]) -> dict:
    breakdown: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})
    for result in single_results:
        entry = breakdown[result["profile"]]
        entry["total"] += 1
        entry["correct"] += int(result["correct"])
    return dict(breakdown)


def _engine_health_metrics(factory) -> dict:
    with session_scope(factory) as session:
        subject_count = session.execute(
            select(func.count(func.distinct(FamilyRecord.subject_id)))
        ).scalar_one()
        family_count = session.execute(select(func.count(FamilyRecord.id))).scalar_one()
        series_count = session.execute(select(func.count(SeriesRecord.id))).scalar_one()
        ambiguous_series_count = session.execute(
            select(func.count(SeriesRecord.id)).where(SeriesRecord.family_id.is_(None))
        ).scalar_one()

        families = session.execute(select(FamilyRecord)).scalars().all()
        avg_variants = (
            sum(len(f.representative_variants) for f in families) / len(families) if families else 0.0
        )
        avg_cohesion = sum(f.cohesion for f in families) / len(families) if families else 0.0

        habit_decisions = session.execute(select(HabitEvaluationRecord.decision)).scalars().all()
        eligible_habit_count = sum(1 for d in habit_decisions if d == HabitDecision.PASS.value)

        plan_rows = session.execute(select(PlanCandidateRecord)).scalars().all()
        plans_per_habit = len(plan_rows) / eligible_habit_count if eligible_habit_count else 0.0
        prefill_plans = [p for p in plan_rows if p.plan_type == PlanType.PREFILL.value]
        downgraded_prefill = sum(
            1 for p in prefill_plans if p.risk_decision == RiskDecisionType.DOWNGRADE_TO_NAVIGATE.value
        )
        prefill_downgrade_rate = downgraded_prefill / len(prefill_plans) if prefill_plans else 0.0

        suggestions = session.execute(select(SuggestionRecord)).scalars().all()
        eligible_suggestion_states = {"active", "eligible", "stale"}
        eligible_suggestions = [s for s in suggestions if s.state in eligible_suggestion_states]
        duplicate_suppressed = sum(1 for s in suggestions if "duplicate_plan" in (s.reason_codes or []))

    return {
        "subjects_with_families": subject_count,
        "families_total": family_count,
        "series_total": series_count,
        "ambiguous_series_rate": (ambiguous_series_count / series_count) if series_count else 0.0,
        "families_per_subject": (family_count / subject_count) if subject_count else 0.0,
        "variants_per_family_avg": avg_variants,
        "family_cohesion_avg": avg_cohesion,
        "eligible_habits_total": eligible_habit_count,
        "plans_per_habit_avg": plans_per_habit,
        "prefill_downgrade_rate": prefill_downgrade_rate,
        "eligible_suggestions_total": len(eligible_suggestions),
        "eligible_suggestions_per_subject": (len(eligible_suggestions) / subject_count) if subject_count else 0.0,
        "duplicate_suppressed_total": duplicate_suppressed,
    }


def _failure_bucket(result: dict) -> str:
    if result["expected"] == "pass" and result["actual"] != "pass":
        return "HABIT_FALSE_NEGATIVE"
    if result["expected"] != "pass" and result["actual"] == "pass":
        return "HABIT_FALSE_POSITIVE"
    return "NONE"


def run(subjects_per_profile: int, multi_habit_subjects: int, db_path: Path | None, seed_base: int) -> dict:
    database_url = f"sqlite:///{db_path}" if db_path else "sqlite:///:memory:"
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)

    start = time.perf_counter()
    single_subjects, multi_subjects, total_events = _build_dataset(
        factory, subjects_per_profile, multi_habit_subjects, seed_base
    )
    ingestion_seconds = time.perf_counter() - start

    start = time.perf_counter()
    single_results, multi_results = _analyze_all(factory, single_subjects, multi_subjects)
    analysis_seconds = time.perf_counter() - start

    metrics = _classification_metrics(single_results)
    breakdown = _per_profile_breakdown(single_results)
    health = _engine_health_metrics(factory)
    failures = Counter(_failure_bucket(r) for r in single_results)
    failures.pop("NONE", None)

    total_subjects = len(single_subjects) + len(multi_subjects)

    return {
        "dataset": {
            "total_subjects": total_subjects,
            "single_profile_subjects": len(single_subjects),
            "multi_habit_subjects": len(multi_subjects),
            "total_events": total_events,
            "ingestion_seconds": round(ingestion_seconds, 3),
            "analysis_seconds": round(analysis_seconds, 3),
        },
        "classification_metrics": metrics,
        "per_profile_breakdown": breakdown,
        "multi_habit_results": multi_results,
        "failure_buckets": dict(failures),
        "engine_health": health,
        "mismatches": [r for r in single_results if not r["correct"]],
    }


def _print_report(report: dict) -> None:
    dataset = report["dataset"]
    metrics = report["classification_metrics"]
    health = report["engine_health"]

    print("=== Dataset ===")
    print(f"subjects: {dataset['total_subjects']}  events: {dataset['total_events']}")
    print(f"ingestion: {dataset['ingestion_seconds']}s  analysis: {dataset['analysis_seconds']}s")

    print("\n=== Habit Classification (positive class = PASS) ===")
    print(f"TP={metrics['tp']} FP={metrics['fp']} FN={metrics['fn']} TN={metrics['tn']}")
    print(f"precision={metrics['precision']}  recall={metrics['recall']}  f1={metrics['f1']}")

    print("\n=== Per-profile ===")
    for profile, entry in sorted(report["per_profile_breakdown"].items()):
        print(f"  {profile:28s} {entry['correct']}/{entry['total']}")

    print("\n=== Multi-habit subjects ===")
    multi_correct = sum(1 for r in report["multi_habit_results"] if r["correct"])
    print(f"  {multi_correct}/{len(report['multi_habit_results'])} subjects had the exact expected family count")

    print("\n=== Failure buckets ===")
    if not report["failure_buckets"]:
        print("  none")
    for bucket, count in report["failure_buckets"].items():
        print(f"  {bucket}: {count}")

    print("\n=== Engine health ===")
    for key, value in health.items():
        print(f"  {key}: {value}")

    if report["mismatches"]:
        print("\n=== Mismatches ===")
        for mismatch in report["mismatches"]:
            print(f"  {mismatch}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects-per-profile", type=int, default=6)
    parser.add_argument("--multi-habit-subjects", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    report = run(args.subjects_per_profile, args.multi_habit_subjects, args.db_path, args.seed)
    _print_report(report)

    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRapor yazildi: {args.report}")


if __name__ == "__main__":
    main()
