"""Create the initial n3rf persistence schema.

Revision ID: 0001_initial_schema
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=True),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "model_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("api_key_env", sa.String(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("model_profiles")
    op.drop_table("runs")
    op.drop_table("workflows")
