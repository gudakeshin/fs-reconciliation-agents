"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-08-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # transactions
    op.create_table(
        'transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(20, 4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 6), nullable=True),
        sa.Column('security_id', sa.String(length=100), nullable=True),
        sa.Column('security_name', sa.String(length=255), nullable=True),
        sa.Column('isin', sa.String(length=12), nullable=True),
        sa.Column('cusip', sa.String(length=9), nullable=True),
        sa.Column('sedol', sa.String(length=7), nullable=True),
        sa.Column('trade_date', sa.DateTime(), nullable=True),
        sa.Column('settlement_date', sa.DateTime(), nullable=True),
        sa.Column('value_date', sa.DateTime(), nullable=True),
        sa.Column('fx_rate', sa.Numeric(20, 6), nullable=True),
        sa.Column('fx_currency', sa.String(length=3), nullable=True),
        sa.Column('market_price', sa.Numeric(20, 6), nullable=True),
        sa.Column('market_value', sa.Numeric(20, 4), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=False),
        sa.Column('source_file', sa.String(length=255), nullable=True),
        sa.Column('source_line', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('processed_data', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_external_id', 'transactions', ['external_id'], unique=True)
    op.create_index('ix_transactions_security_id', 'transactions', ['security_id'], unique=False)
    op.create_index('ix_transactions_isin', 'transactions', ['isin'], unique=False)
    op.create_index('ix_transactions_cusip', 'transactions', ['cusip'], unique=False)
    op.create_index('ix_transactions_sedol', 'transactions', ['sedol'], unique=False)

    # transaction_matches
    op.create_table(
        'transaction_matches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('transaction_id', sa.UUID(), nullable=False),
        sa.Column('matched_transaction_id', sa.UUID(), nullable=False),
        sa.Column('match_type', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False),
        sa.Column('match_criteria', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id']),
        sa.ForeignKeyConstraint(['matched_transaction_id'], ['transactions.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # reconciliation_exceptions
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
        sa.Column('break_amount', sa.Numeric(20, 4), nullable=True),
        sa.Column('break_currency', sa.String(length=3), nullable=True),
        sa.Column('ai_confidence_score', sa.Numeric(5, 4), nullable=True),
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
    op.drop_table('transaction_matches')
    op.drop_index('ix_transactions_sedol', table_name='transactions')
    op.drop_index('ix_transactions_cusip', table_name='transactions')
    op.drop_index('ix_transactions_isin', table_name='transactions')
    op.drop_index('ix_transactions_security_id', table_name='transactions')
    op.drop_index('ix_transactions_external_id', table_name='transactions')
    op.drop_table('transactions')


