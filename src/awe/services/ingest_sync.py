"""Dış sunucudan veri çekip AWE'ye besleyen tetikleme akışı -- `awe.pull` (PULL) + servise özel
TRANSFORM + `awe.services.ingestion`/`analysis` (INGEST/ANALYZE). Önerileri geri gönderme
(PUSH) kasıtlı olarak burada DEĞİLDİR -- bağımsız bir yetenektir, bkz.
`awe.services.suggestions.push_pending`. İkisi ayrı config anahtarına (`pull:`/`delivery:`),
ayrı HTTP endpoint'ine (`POST .../pull` / `POST .../push`) ve ayrı hata moduna bağlıdır: biri
başarısız olsa diğerini etkilemez, farklı zamanlamalarda tetiklenebilirler.

TRANSFORM adımı (çekilen ham veriyi canonical event şekline çevirme) servise özeldir ve bu
modülde YOKTUR -- `awe.transforms.{project_id}`den (varsa) dinamik olarak yüklenir, bkz.
`awe.transforms` modül docstring'i. Kayıtlı değilse `pull_and_analyze` net bir hatayla döner,
sessizce yanlış bir şey yapmaz."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from awe.config import ProjectConfig
from awe.pull import fetch_raw_data
from awe.services.analysis import analyze_subject
from awe.services.ingestion import ingest_batch

TransformFn = Callable[[object], list[dict]]


@dataclass(frozen=True, slots=True)
class PullResult:
    success: bool
    error: str | None = None
    ingested_count: int = 0
    rejected_count: int = 0
    series_count: int = 0


def _load_transform(project_id: str) -> TransformFn | None:
    """`awe.transforms.{project_id}` modülünü bulup içindeki `transform` fonksiyonunu döner;
    modül ya da fonksiyon yoksa `None` (bkz. `awe.transforms` modül docstring'i)."""
    try:
        module = importlib.import_module(f"awe.transforms.{project_id}")
    except ModuleNotFoundError:
        return None
    transform = getattr(module, "transform", None)
    return transform if callable(transform) else None


def pull_and_analyze(
    session: Session,
    project_config: ProjectConfig,
    project_id: str,
    subject_id: str,
    now: datetime,
    client: httpx.Client | None = None,
) -> PullResult:
    """`client` yalnızca testlerde `httpx.MockTransport` ile sahte bir sunucuya bağlamak için
    opsiyonel olarak enjekte edilir (bkz. `awe.pull.fetch_raw_data`deki aynı desen); verilmezse
    gerçek bir `httpx.Client()` kullanılır."""
    if not project_config.pull.enabled:
        return PullResult(success=False, error="pull.enabled=False")

    transform = _load_transform(project_id)
    if transform is None:
        return PullResult(success=False, error=f"'{project_id}' için awe.transforms.{project_id} bulunamadı")

    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        try:
            raw_external_data = fetch_raw_data(project_config.pull, client=http_client)
        except Exception as exc:
            return PullResult(success=False, error=f"PULL başarısız: {exc}")

        try:
            raw_events = transform(raw_external_data)
        except Exception as exc:
            return PullResult(success=False, error=f"TRANSFORM başarısız: {exc}")
    finally:
        if owns_client:
            http_client.close()

    outcomes = ingest_batch(session, project_config, project_id, raw_events, now)
    session.commit()
    ingested = sum(1 for outcome in outcomes if outcome.accepted)
    rejected = sum(1 for outcome in outcomes if not outcome.accepted)

    summary = analyze_subject(session, project_config, project_id, subject_id, now)
    session.commit()

    return PullResult(
        success=True, ingested_count=ingested, rejected_count=rejected, series_count=summary.series_count
    )
