"""Bảng nền cho auth: users, user_settings, revoked_tokens.

Revision ID: 0001_initial_auth
Revises:
Create Date: 2026-08-20

Viết tay (không autogenerate) để chạy được cả khi máy chưa kết nối DB lúc tạo file.
Khớp ORM model trong app/modules/*/models.py và docs/DATABASE_SCHEMA.md.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=60), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=False)

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("theme", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("send_on_enter", sa.Boolean(), nullable=False),
        sa.Column("show_suggestions", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_settings_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_settings"),
    )

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_revoked_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("jti", name="pk_revoked_tokens"),
    )
    op.create_index(
        "ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"], unique=False
    )
    op.create_index(
        "ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.drop_table("user_settings")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
