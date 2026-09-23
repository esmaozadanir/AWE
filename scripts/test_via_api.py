#!/usr/bin/env python
"""`scratch/engine_stress_test_events.json`'da DİSKTE duran ham event dosyasını, iç Python
fonksiyonlarını çağırmadan, GERÇEK HTTP API üzerinden (FastAPI TestClient ile -- gerçek routing/
şema doğrulama/serialization dahil) baştan sona test eder: events/batch -> analyze -> suggestions.

`scripts/engine_stress_test.py`den FARKI: o script `ingest_event`/`analyze_subject` Python
fonksiyonlarını doğrudan çağırıyordu. Bu script, event'leri önce DİSKE yazılmış JSON dosyasından
okuyup, `awe.api.main.app`'ın kendi HTTP endpoint'lerine gerçek istek olarak gönderiyor -- API
katmanının kendisi (request/response şema doğrulama, routing) da test edilmiş oluyor.

Kullanım:
    python scripts/test_via_api.py [json_dosya_yolu]
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from awe.api.main import app  # noqa: E402
from awe.config import ProjectRegistry, Settings  # noqa: E402
from awe.persistence import Base, create_database_engine  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _REPO_ROOT / "config_examples"
_PROJECT = "learnloop"
_SUBJECT = "learner_512"


def main() -> None:
    default_path = _REPO_ROOT / "scratch" / "engine_stress_test_events.json"
    events_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    events = json.loads(events_path.read_text(encoding="utf-8"))
    print(f"=== Veri seti ===\n{len(events)} ham event okundu <- {events_path}\n")

    db_path = _REPO_ROOT / "scratch" / f"api_test_{uuid.uuid4().hex}.db"
    database_url = f"sqlite:///{db_path}"
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)

    with TestClient(app) as client:
        # `app.state`, TestClient girişinden (lifespan çalıştıktan) SONRA set edilir -- aksi
        # halde `_lifespan`in kendi `get_settings()` çağrısı bu override'ı ezer.
        app.state.settings = Settings(database_url=database_url, project_config_dir=str(_CONFIG_DIR))
        app.state.project_registry = ProjectRegistry(_CONFIG_DIR)

        print(f"=== POST /events/batch?project_id={_PROJECT} ===")
        batch_response = client.post("/events/batch", params={"project_id": _PROJECT}, json=events)
        batch_response.raise_for_status()
        batch = batch_response.json()
        print(
            f"accepted={batch['accepted_count']}  duplicate={batch['duplicate_count']}  "
            f"rejected={batch['rejected_count']}"
        )
        for result in batch["results"]:
            if not result["accepted"] and not result["duplicate"]:
                print(f"  REJECTED {result['event_id']}: {result['error']}")

        print(f"\n=== POST /analyze?project_id={_PROJECT}&subject_id={_SUBJECT} ===")
        analyze_response = client.post("/analyze", params={"project_id": _PROJECT, "subject_id": _SUBJECT})
        analyze_response.raise_for_status()
        analysis = analyze_response.json()
        detected = [v for v in analysis["variants"] if v["habit_decision"] == "habit_detected"]
        print(f"series_count={analysis['series_count']}  variant_count={len(analysis['variants'])}")
        print(f"HABIT_DETECTED: {len(detected)}")

        print(f"\n=== GET /suggestions?project_id={_PROJECT}&subject_id={_SUBJECT} ===")
        suggestions_response = client.get("/suggestions", params={"project_id": _PROJECT, "subject_id": _SUBJECT})
        suggestions_response.raise_for_status()
        suggestions = suggestions_response.json()
        print(f"{len(suggestions)} oneri\n")
        for suggestion in suggestions:
            intent = suggestion["intent"]
            print(f"  state={suggestion['state']}")
            print(
                f"    mode={intent['mode']}  destination={intent['destination_screen']}  target={intent['target']}"
            )
            print(f"    requires_confirmation={intent['requires_user_confirmation']}")
            print(
                f"    risk={intent['risk_decision']}  benefit_saved={intent['benefit_saved_actions']}  "
                f"benefit_level={intent['benefit_level']}"
            )
            print(f"    reason_codes={suggestion['reason_codes']}")

    # Windows'ta app'in kendi içindeki (bu script'in `engine` değişkeninden AYRI) bağlantı
    # dosyayı hâlâ açık tutabiliyor -- best-effort temizlik, başarısız olursa script'i
    # çökertmesin (scratch/ zaten git'e girmiyor, kalırsa zararsız).
    engine.dispose()
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        print(f"\n(not: {db_path} silinemedi, dosya hala kullanımda -- zararsız, scratch/'ta kalabilir)")


if __name__ == "__main__":
    main()
