"""
Alembic environment configuration for FS Reconciliation Agents.

This file configures the Alembic migration environment and imports
all the SQLAlchemy models for automatic migration generation.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import all models to ensure they are registered with SQLAlchemy
from src.core.models.data_models.transaction import (
    Base as TransactionBase,
    Transaction,
    TransactionMatch,
)
from src.core.models.break_types.reconciliation_break import (
    Base as BreakBase,
    ReconciliationException,
    BreakAuditTrail,
    SecurityIDBreak,
    FixedIncomeCouponBreak,
    MarketPriceBreak,
    TradeSettlementDateBreak,
    FXRateBreak,
)
from src.core.models.audit_models.audit_trail import (
    Base as AuditBase,
    AuditTrail,
    DataLineage,
    UserActivity,
    SystemLog,
    ComplianceRecord,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# Use multiple metadatas so Alembic can detect all models
target_metadata = [
    TransactionBase.metadata,
    BreakBase.metadata,
    AuditBase.metadata,
]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Get database URL from environment variables."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://reconciliation_user:reconciliation_password@database:5432/reconciliation_db"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override the sqlalchemy.url in the config
    config.set_main_option("sqlalchemy.url", get_url())
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Enable automatic migration generation
            compare_type=True,
            compare_server_default=True,
            include_schemas=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 