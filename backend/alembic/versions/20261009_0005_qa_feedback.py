"""по ответам организаторов: заявленная категория, gross/net, отзыв контактов, ATS

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-09 01:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Заявленная специализация: пока тест не пройден, кандидат виден с пометкой «не подтверждён»
    op.add_column('candidate_profiles', sa.Column('declared_specialization', sa.String(length=50), nullable=True))
    op.create_index('ix_candidate_profiles_declared_specialization', 'candidate_profiles',
                    ['declared_specialization'])
    # переносим специализацию из уже пройденных опросов
    cp = sa.table('candidate_profiles', sa.column('id', sa.Integer), sa.column('survey', sa.JSON),
                  sa.column('declared_specialization', sa.String))
    conn = op.get_bind()
    for row in conn.execute(sa.select(cp.c.id, cp.c.survey)).all():
        spec = (row.survey or {}).get('specialization') if isinstance(row.survey, dict) else None
        if spec:
            conn.execute(cp.update().where(cp.c.id == row.id).values(declared_specialization=spec))

    # 1б. Спортивный разряд участника ФСП
    op.add_column('candidate_profiles', sa.Column('fsp_rank', sa.String(length=30), nullable=True))

    # 2. Зарплата: явно до вычета НДФЛ (gross) или на руки (net)
    op.add_column('vacancies', sa.Column('salary_type', sa.String(length=10), nullable=False, server_default='gross'))
    op.add_column('invitations', sa.Column('salary_type', sa.String(length=10), nullable=False,
                                           server_default='gross'))

    # 3. Отзыв доступа к контактам кандидатом
    op.add_column('invitations', sa.Column('contacts_revoked_at', sa.DateTime(timezone=True), nullable=True))

    # 4. Интеграция с ATS работодателя
    op.add_column('employer_profiles', sa.Column('ats_webhook_url', sa.String(length=500), nullable=True))
    op.add_column('employer_profiles', sa.Column('ats_webhook_secret', sa.Text(), nullable=True))
    op.create_table(
        'ats_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employer_id', sa.Integer(), nullable=False),
        sa.Column('event', sa.String(length=60), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('ok', sa.Boolean(), nullable=False),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index('ix_ats_deliveries_employer_id', 'ats_deliveries', ['employer_id'])


def downgrade() -> None:
    op.drop_index('ix_ats_deliveries_employer_id', table_name='ats_deliveries')
    op.drop_table('ats_deliveries')
    with op.batch_alter_table('employer_profiles') as b:
        b.drop_column('ats_webhook_secret')
        b.drop_column('ats_webhook_url')
    with op.batch_alter_table('invitations') as b:
        b.drop_column('contacts_revoked_at')
        b.drop_column('salary_type')
    with op.batch_alter_table('vacancies') as b:
        b.drop_column('salary_type')
    op.drop_index('ix_candidate_profiles_declared_specialization', table_name='candidate_profiles')
    with op.batch_alter_table('candidate_profiles') as b:
        b.drop_column('fsp_rank')
        b.drop_column('declared_specialization')
