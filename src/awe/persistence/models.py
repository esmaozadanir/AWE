"""SQLAlchemy şema tanımları (bölüm 96).

Yalnızca portable tipler kullanılır (`String`, `Integer`, `Float`, `Boolean`,
`UTCDateTime`, `JSON`) — SQLite ve PostgreSQL arasında taşınabilirlik için
Postgres'e özgü tipler (`ARRAY`, `JSONB` vb.) kullanılmaz.

Normalize edilmiş O-Series adımları ayrı bir tabloda tutulmaz: bunlar `observations` tablosundan
(seri'ye ait ham kayıtlardan) deterministik biçimde yeniden hesaplanır — bu, normalizasyon
mantığının iki yerde bakımsız kalmasını önler ve tek doğruluk kaynağını (raw observation)
korur.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
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


class ObservationRecord(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    effect: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)

    screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    widget: Mapped[str | None] = mapped_column(String(256), nullable=True)

    target: Mapped[str | None] = mapped_column(String(256), nullable=True)

    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    breaks_episode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)

    quality_has_screen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_has_widget: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_has_session_id: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quality_is_synthetic_session: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_mapping_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "event_id", name="uq_observations_project_event"),
        Index("ix_observations_subject_scope", "project_id", "subject_id", "session_id"),
        Index("ix_observations_series", "series_id"),
    )


class SeriesRecord(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(256), nullable=False)

    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ordering_confidence: Mapped[str] = mapped_column(String(16), nullable=False)

    ended_by_breaks_episode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    entry_trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    has_shortcut_trigger: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    final_status: Mapped[str] = mapped_column(String(32), nullable=False)

    family_id: Mapped[int | None] = mapped_column(ForeignKey("families.id"), nullable=True)
    ambiguous_family_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (Index("ix_series_subject_scope", "project_id", "subject_id"),)


class FamilyRecord(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)

    representative_variants: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    relationships: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cohesion: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (Index("ix_families_subject_scope", "project_id", "subject_id"),)


class HabitEvaluationRecord(Base):
    __tablename__ = "habit_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False, unique=True)

    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class PlanCandidateRecord(Base):
    __tablename__ = "plan_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)

    plan_type: Mapped[str] = mapped_column(String(16), nullable=False)
    anchor: Mapped[dict] = mapped_column(JSON, nullable=False)
    bindings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    target_binding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supporting_occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    risk_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reduced_bindings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    benefit_median: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_p25: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_p75: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    benefit_meets_minimum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (Index("ix_plan_candidates_family", "family_id"),)


class SuggestionRecord(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suggestion_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False, unique=True)

    primary_plan_id: Mapped[int] = mapped_column(ForeignKey("plan_candidates.id"), nullable=False)
    fallback_plan_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    dismiss_cooldown_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (Index("ix_suggestions_subject_scope", "project_id", "subject_id"),)
