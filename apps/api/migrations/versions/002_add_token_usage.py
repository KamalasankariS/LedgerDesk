"""Add token_usage column to agent_runs.

Revision ID: 002
Revises: 001
Create Date: 2024-12-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs", sa.Column("token_usage", postgresql.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "token_usage")
