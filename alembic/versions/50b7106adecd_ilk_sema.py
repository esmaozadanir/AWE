"""ilk sema

Revision ID: 50b7106adecd
Revises:
Create Date: 2026-08-08 14:28:50.989866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import awe.persistence.types


# revision identifiers, used by Alembic.
revision: str = '50b7106adecd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('project_id', sa.String(length=128), nullable=False),
    sa.Column('event_id', sa.String(length=128), nullable=False),
    sa.Column('subject_id', sa.String(length=128), nullable=False),
    sa.Column('received_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('raw_payload', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'event_id', name='uq_events_project_event')
    )
    op.create_table('event_conflicts',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('project_id', sa.String(length=128), nullable=False),
    sa.Column('event_id', sa.String(length=128), nullable=False),
    sa.Column('first_payload', sa.JSON(), nullable=False),
    sa.Column('conflicting_payload', sa.JSON(), nullable=False),
    sa.Column('detected_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_conflicts_project_event', 'event_conflicts', ['project_id', 'event_id'], unique=False)
    op.create_table('observations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('project_id', sa.String(length=128), nullable=False),
    sa.Column('subject_id', sa.String(length=128), nullable=False),
    sa.Column('session_id', sa.String(length=256), nullable=False),
    sa.Column('event_id', sa.String(length=128), nullable=False),
    sa.Column('timestamp', awe.persistence.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('action', sa.String(length=256), nullable=False),
    sa.Column('source', sa.String(length=32), nullable=False),
    sa.Column('effect', sa.String(length=32), nullable=False),
    sa.Column('trigger', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('screen', sa.String(length=256), nullable=True),
    sa.Column('target', sa.String(length=256), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('mapping_version', sa.String(length=64), nullable=False),
    sa.Column('quality_has_screen', sa.Boolean(), nullable=False),
    sa.Column('quality_missing_target_field', sa.Boolean(), nullable=False),
    sa.Column('quality_invalid_duration', sa.Boolean(), nullable=False),
    sa.Column('quality_warnings', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'event_id', name='uq_observations_project_event')
    )
    op.create_index('ix_observations_subject_scope', 'observations', ['project_id', 'subject_id', 'session_id'], unique=False)
    op.create_table('habit_evaluations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('project_id', sa.String(length=128), nullable=False),
    sa.Column('subject_id', sa.String(length=128), nullable=False),
    sa.Column('variant_key', sa.String(length=128), nullable=False),
    sa.Column('family_key', sa.String(length=64), nullable=False),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('reason_codes', sa.JSON(), nullable=False),
    sa.Column('evidence', sa.JSON(), nullable=True),
    sa.Column('evaluated_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('variant_key')
    )
    op.create_index('ix_habit_evaluations_subject_scope', 'habit_evaluations', ['project_id', 'subject_id'], unique=False)
    op.create_table('shortcut_intents',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('intent_key', sa.String(length=160), nullable=False),
    sa.Column('project_id', sa.String(length=128), nullable=False),
    sa.Column('subject_id', sa.String(length=128), nullable=False),
    sa.Column('variant_key', sa.String(length=128), nullable=False),
    sa.Column('family_key', sa.String(length=64), nullable=False),
    sa.Column('anchor', sa.JSON(), nullable=False),
    sa.Column('scope', sa.JSON(), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('mode', sa.String(length=16), nullable=True),
    sa.Column('destination_screen', sa.String(length=256), nullable=True),
    sa.Column('target', sa.String(length=256), nullable=True),
    sa.Column('requires_user_confirmation', sa.Boolean(), nullable=False),
    sa.Column('supporting_occurrences', sa.Integer(), nullable=False),
    sa.Column('intent_reason_codes', sa.JSON(), nullable=False),
    sa.Column('risk_decision', sa.String(length=16), nullable=False),
    sa.Column('risk_evidence', sa.JSON(), nullable=False),
    sa.Column('risk_reason_codes', sa.JSON(), nullable=False),
    sa.Column('benefit_observed_actions', sa.Integer(), nullable=False),
    sa.Column('benefit_planned_actions', sa.Integer(), nullable=False),
    sa.Column('selection_outcome', sa.String(length=16), nullable=False),
    sa.Column('selection_reason_codes', sa.JSON(), nullable=False),
    sa.Column('evaluated_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('intent_key')
    )
    op.create_index('ix_shortcut_intents_subject_scope', 'shortcut_intents', ['project_id', 'subject_id'], unique=False)
    op.create_table('suggestions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('suggestion_key', sa.String(length=64), nullable=False),
    sa.Column('project_id', sa.String(length=128), nullable=False),
    sa.Column('subject_id', sa.String(length=128), nullable=False),
    sa.Column('family_key', sa.String(length=64), nullable=False),
    sa.Column('variant_key', sa.String(length=128), nullable=False),
    sa.Column('primary_intent_key', sa.String(length=160), nullable=False),
    sa.Column('state', sa.String(length=32), nullable=False),
    sa.Column('reason_codes', sa.JSON(), nullable=False),
    sa.Column('created_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('dismissed_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('dismiss_cooldown_until', awe.persistence.types.UTCDateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('suggestion_key'),
    sa.UniqueConstraint('variant_key')
    )
    op.create_index('ix_suggestions_subject_scope', 'suggestions', ['project_id', 'subject_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_suggestions_subject_scope', table_name='suggestions')
    op.drop_table('suggestions')
    op.drop_index('ix_shortcut_intents_subject_scope', table_name='shortcut_intents')
    op.drop_table('shortcut_intents')
    op.drop_index('ix_habit_evaluations_subject_scope', table_name='habit_evaluations')
    op.drop_table('habit_evaluations')
    op.drop_index('ix_observations_subject_scope', table_name='observations')
    op.drop_table('observations')
    op.drop_index('ix_event_conflicts_project_event', table_name='event_conflicts')
    op.drop_table('event_conflicts')
    op.drop_table('events')
