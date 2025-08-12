"""add reconciliation_exceptions table

Revision ID: af01
Revises: da1d6cca1d89
Create Date: 2025-08-10 06:25:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reconciliation_exceptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('transaction_id', sa.UUID(), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('break_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('suggested_resolution', sa.Text(), nullable=True),
        sa.Column('break_amount', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('break_currency', sa.String(length=3), nullable=True),
        sa.Column('ai_confidence_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('ai_reasoning', sa.JSON(), nullable=True),
        sa.Column('ai_suggested_actions', sa.JSON(), nullable=True),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('resolution_method', sa.String(length=100), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('reconciliation_exceptions')


