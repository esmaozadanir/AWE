#!/usr/bin/env python
"""Dış bir sunucudan veri çekme (PULL) ve ürettiği önerileri geri gönderme (PUSH) akışlarını
komut satırından tetikleyen ince bir CLI kabuğu -- iki BAĞIMSIZ, ayrı ayrı tetiklenebilir alt
komut olarak (`pull`, `push`).

Asıl mantık burada değil, `awe.services.ingest_sync.pull_and_analyze` ve
`awe.services.suggestions.push_pending`dedir -- aynı iki fonksiyon
`POST .../subjects/{subject_id}/pull` ve `POST .../subjects/{subject_id}/push` HTTP
endpoint'leri tarafından da çağrılır (bkz. `awe.api.routes_events`, `awe.api.routes_
suggestions`). Hangi yolu (CLI script ya da HTTP çağrısı) kullanacağın tetikleme şekline bağlı.

PULL ve PUSH kasıtlı olarak AYRIDIR, tek bir "sync" çağrısında birleştirilmez: farklı
zamanlamalarda tetiklenebilirler, biri başarısız olsa diğerini etkilemez, ayrı config
anahtarına (`pull:`/`delivery:`) bağlıdırlar.

PULL akışının üç adımından ikisi (INGEST/ANALYZE) jenerik ve çalışır durumda; yalnızca
TRANSFORM (çekilen ham veriyi bu projenin AdapterMapping'inin beklediği event şekline çevirme)
servise özeldir -- HER SERVİSİN veri şekli farklı olduğu için bu jenerik yapılamaz. Bunu
yazmak için: `src/awe/transforms/{project_id}.py` adında bir modül oluştur, içine
`def transform(raw_data: object) -> list[dict]:` yaz (bkz. `awe.transforms` modül docstring'i).
Yazılmadıysa `pull_and_analyze` net bir hatayla döner, sessizce yanlış bir şey yapmaz.

Otomatik zamanlama (cron/Görev Zamanlayıcı) bu script'in kapsamı DIŞINDA -- bu yalnızca tek
seferlik/elle ya da dışarıdan zamanlanmış çalıştırma için bir script'tir.

Kullanım:
    python scripts/external_sync_template.py pull <project_id> <subject_id>
    python scripts/external_sync_template.py push <project_id> <subject_id>
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _env import load_env_file  # noqa: E402

from awe.config import ProjectConfig, ProjectRegistry, get_settings  # noqa: E402
from awe.persistence import Base, create_database_engine, create_session_factory  # noqa: E402
from awe.services import pull_and_analyze, push_pending  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _REPO_ROOT / ".env"
_CONFIG_DIR = _REPO_ROOT / "config_examples"


def _load_project_config(project_id: str) -> ProjectConfig:
    load_env_file(_ENV_PATH)
    return ProjectRegistry(_CONFIG_DIR).get(project_id)


def _open_session():
    engine = create_database_engine(get_settings().database_url)
    Base.metadata.create_all(engine)
    return create_session_factory(engine)()


def run_pull(project_id: str, subject_id: str) -> None:
    project_config = _load_project_config(project_id)
    result = pull_and_analyze(_open_session(), project_config, project_id, subject_id, datetime.now(UTC))

    if not result.success:
        print(f"PULL BAŞARISIZ: {result.error}")
        return
    print(
        f"ingest: {result.ingested_count} kabul, {result.rejected_count} red | "
        f"analyze: {result.series_count} series"
    )


def run_push(project_id: str, subject_id: str) -> None:
    project_config = _load_project_config(project_id)
    result = push_pending(_open_session(), project_config, project_id, subject_id, datetime.now(UTC))

    if not result.success:
        print(f"PUSH BAŞARISIZ: {result.error}")
        return
    print(f"push: {result.pushed_count} gönderildi, {result.push_failed_count} başarısız")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="action", required=True)

    pull_parser = subparsers.add_parser("pull", help="Veri çek, AWE'ye besle, analiz et")
    pull_parser.add_argument("project_id")
    pull_parser.add_argument("subject_id")

    push_parser = subparsers.add_parser("push", help="Bekleyen önerileri gönder")
    push_parser.add_argument("project_id")
    push_parser.add_argument("subject_id")

    args = parser.parse_args()
    if args.action == "pull":
        run_pull(args.project_id, args.subject_id)
    else:
        run_push(args.project_id, args.subject_id)
