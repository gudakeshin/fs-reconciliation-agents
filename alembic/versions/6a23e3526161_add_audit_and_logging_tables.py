"""add_audit_and_logging_tables

Revision ID: 6a23e3526161
Revises: 9e74233aa993
Create Date: 2025-08-11 11:34:23.934756

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6a23e3526161'
down_revision = 'af01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create system_logs table
    op.create_table(
        'system_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('log_level', sa.String(length=20), nullable=False),
        sa.Column('log_message', sa.Text(), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=True),
        sa.Column('sub_component', sa.String(length=100), nullable=True),
        sa.Column('function_name', sa.String(length=255), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('exception_type', sa.String(length=255), nullable=True),
        sa.Column('exception_message', sa.Text(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('memory_usage_mb', sa.Numeric(10, 2), nullable=True),
        sa.Column('cpu_usage_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('log_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_system_logs_created_at', 'system_logs', ['created_at'])
    op.create_index('ix_system_logs_log_level', 'system_logs', ['log_level'])
    op.create_index('ix_system_logs_component', 'system_logs', ['component'])

    # Create audit_trail table
    op.create_table(
        'audit_trail',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('action_description', sa.Text(), nullable=True),
        sa.Column('action_data', postgresql.JSONB(), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('user_role', sa.String(length=100), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('entity_type', sa.String(length=100), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('entity_external_id', sa.String(length=255), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('memory_usage_mb', sa.Numeric(10, 2), nullable=True),
        sa.Column('ai_model_used', sa.String(length=100), nullable=True),
        sa.Column('ai_confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('regulatory_requirement', sa.String(length=255), nullable=True),
        sa.Column('compliance_category', sa.String(length=100), nullable=True),
        sa.Column('data_classification', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('is_successful', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_trail_created_at', 'audit_trail', ['created_at'])
    op.create_index('ix_audit_trail_action_type', 'audit_trail', ['action_type'])
    op.create_index('ix_audit_trail_user_id', 'audit_trail', ['user_id'])
    op.create_index('ix_audit_trail_entity_type', 'audit_trail', ['entity_type'])
    op.create_index('ix_audit_trail_session_id', 'audit_trail', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_trail_session_id', table_name='audit_trail')
    op.drop_index('ix_audit_trail_entity_type', table_name='audit_trail')
    op.drop_index('ix_audit_trail_user_id', table_name='audit_trail')
    op.drop_index('ix_audit_trail_action_type', table_name='audit_trail')
    op.drop_index('ix_audit_trail_created_at', table_name='audit_trail')
    op.drop_table('audit_trail')
    
    op.drop_index('ix_system_logs_component', table_name='system_logs')
    op.drop_index('ix_system_logs_log_level', table_name='system_logs')
    op.drop_index('ix_system_logs_created_at', table_name='system_logs')
    op.drop_table('system_logs') 