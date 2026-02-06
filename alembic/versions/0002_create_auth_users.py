"""create auth users table

Revision ID: 0002_create_auth_users
Revises: 0001_create_users
Create Date: 2026-02-05 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_create_auth_users"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_auth_users_id"), "auth_users", ["id"], unique=False)
    op.create_index(op.f("ix_auth_users_username"), "auth_users", ["username"], unique=True)
    op.create_index(op.f("ix_auth_users_email"), "auth_users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_users_email"), table_name="auth_users")
    op.drop_index(op.f("ix_auth_users_username"), table_name="auth_users")
    op.drop_index(op.f("ix_auth_users_id"), table_name="auth_users")
    op.drop_table("auth_users")
