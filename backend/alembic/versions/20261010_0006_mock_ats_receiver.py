"""встроенный тестовый приёмник вебхуков ATS

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-10 16:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mock_ats_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employer_id', sa.Integer(), nullable=False),
        sa.Column('event', sa.String(length=60), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('signature_valid', sa.Boolean(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=True),  # EncryptedText: в БД — шифротекст
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index('ix_mock_ats_events_employer_id', 'mock_ats_events', ['employer_id'])


def downgrade() -> None:
    op.drop_index('ix_mock_ats_events_employer_id', table_name='mock_ats_events')
    op.drop_table('mock_ats_events')
