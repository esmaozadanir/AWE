#!/usr/bin/env python
"""Sentetik event log üretip JSONL dosyasına yazar.

Kullanım:
    python scripts/generate_synthetic_logs.py --output out.jsonl --subjects-per-profile 5
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from awe.testing import PROFILE_NAMES, generate_subject  # noqa: E402

_PROJECTS = (
    "shopwave",
    "socialpulse",
    "financepilot",
    "healthtrack",
    "wanderly",
    "streamboxx",
)
"""LearnLoop ve TaskFlow kasıtlı olarak farklı bir raw event şekli kullanır (bölüm 32); bu
jenerik üretici yalnızca ShopWave'in canonical-benzeri şeklini paylaşan projeleri hedefler."""
_BASE_TIME = datetime(2026, 1, 1, 9, tzinfo=UTC)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("synthetic_events.jsonl"))
    parser.add_argument("--subjects-per-profile", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1000)
    args = parser.parse_args()

    project_cycle = itertools.cycle(_PROJECTS)
    seed = args.seed
    total_events = 0
    total_subjects = 0

    with args.output.open("w", encoding="utf-8") as handle:
        for profile in PROFILE_NAMES:
            for index in range(args.subjects_per_profile):
                project_id = next(project_cycle)
                subject_id = f"{profile}_{index}"
                generated = generate_subject(profile, project_id, subject_id, seed, _BASE_TIME)
                seed += 1
                total_subjects += 1
                for event in generated.events:
                    handle.write(json.dumps(event, ensure_ascii=False))
                    handle.write("\n")
                total_events += len(generated.events)

    print(f"{total_subjects} subject, {total_events} event -> {args.output}")


if __name__ == "__main__":
    main()
