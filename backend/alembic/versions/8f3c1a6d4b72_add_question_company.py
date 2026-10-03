"""add question company column

Adds the optional ``company`` tag used by company-specific question mode, plus
its lookup index and the length check constraint. The operations run through
``batch_alter_table`` so the same revision also applies on SQLite, which cannot
ALTER a table to add a constraint.

Revision ID: 8f3c1a6d4b72
Revises: 4b1256116e28
Create Date: 2026-10-03 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3c1a6d4b72'
down_revision: Union[str, None] = '4b1256116e28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('questions') as batch_op:
        batch_op.add_column(
            sa.Column('company', sa.String(length=100), nullable=True, comment='Company the question targets (company-specific mode)')
        )
        batch_op.create_index(op.f('ix_questions_company'), ['company'], unique=False)
        batch_op.create_index('idx_company_type', ['company', 'question_type'], unique=False)
        batch_op.create_check_constraint('check_company_length', 'company IS NULL OR LENGTH(company) <= 100')


def downgrade() -> None:
    with op.batch_alter_table('questions') as batch_op:
        batch_op.drop_constraint('check_company_length', type_='check')
        batch_op.drop_index('idx_company_type')
        batch_op.drop_index(op.f('ix_questions_company'))
        batch_op.drop_column('company')