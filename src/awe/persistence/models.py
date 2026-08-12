"""SQLAlchemy şema tanımları.

Yalnızca portable tipler kullanılır (`String`, `Integer`, `Float`, `Boolean`, `UTCDateTime`,
`JSON`) — SQLite ve PostgreSQL arasında taşınabilirlik için Postgres'e özgü tipler kullanılmaz.

Mimari not: `series`/`episode_candidates`/`families`/`target_variants` için ayrı tablo YOKTUR.
Yeni tasarımda Family/TargetVariant kimlikleri deterministiktir (exact sembol dizisinden türetilen
hash, bkz. `awe.families.matching.compute_family_id`) — durumsal/artımlı bir varlık değil, saf bir
hesaplama görünümüdür. O-Series Builder ve Episode Candidate Builder her `analyze_subject`
çağrısında `observations` tablosundan sıfırdan yeniden hesaplanır (bölüm 9.10: "incremental
tutulması ... bu algoritma prototiplerinin dışında kalmıştır" — bu motor bilinçli olarak batch/
recompute modelindedir, artımlı state yönetimi bu MVP'nin kapsamı dışıdır). Yalnızca ham
`observations` ve kullanıcı etkileşimine bağlı `suggestions` durumu gerçekten kalıcıdır;
`habit_evaluations`/`shortcut_intents` her analiz çalışmasında tamamen yeniden yazılan bir
önbellektir (eski `replace_plan_candidates` deseniyle aynı, bkz. `awe.persistence.repository`).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Integer, String, UniqueConstraint
from sqlalchemy import Index as SqlIndex
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from awe.persistence.types import UTCDateTime


class Base(DeclarativeBase):
    pass


class EventRecord(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "event_id", name="uq_events_project_event"),)


class EventConflictRecord(Base):
    """Aynı `(project_id, event_id)` farklı içerikle geldiğinde karantina kaydı (bölüm 6.3:
    "conflict quarantine edilir"). İkinci event reddedilir; bu tablo yalnızca denetim içindir."""

    __tablename__ = "event_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    first_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    conflicting_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (SqlIndex("ix_event_conflicts_project_event", "project_id", "event_id"),)


class ObservationRecord(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    action: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    effect: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    target: Mapped[str | None] = mapped_column(String(256), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)

    quality_has_screen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_missing_target_field: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_invalid_duration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("project_id", "event_id", name="uq_observations_project_event"),
        SqlIndex("ix_observations_subject_scope", "project_id", "subject_id", "session_id"),
    )


class HabitEvaluationRecord(Base):
    __tablename__ = "habit_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False)

    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (SqlIndex("ix_habit_evaluations_subject_scope", "project_id", "subject_id"),)


class ShortcutIntentRecord(Base):
    __tablename__ = "shortcut_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intent_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(128), nullable=False)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False)

    anchor: Mapped[dict] = mapped_column(JSON, nullable=False)
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)

    state: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    destination_screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    target: Mapped[str | None] = mapped_column(String(256), nullable=True)
    requires_user_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supporting_occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intent_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    risk_decision: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    risk_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    benefit_observed_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    benefit_planned_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    selection_outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    selection_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (SqlIndex("ix_shortcut_intents_subject_scope", "project_id", "subject_id"),)


class SuggestionRecord(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suggestion_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    primary_intent_key: Mapped[str] = mapped_column(String(160), nullable=False)

    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    dismiss_cooldown_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (SqlIndex("ix_suggestions_subject_scope", "project_id", "subject_id"),)
