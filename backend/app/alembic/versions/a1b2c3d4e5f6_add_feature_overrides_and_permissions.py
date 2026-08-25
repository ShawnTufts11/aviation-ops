"""Add feature_overrides and permissions_version to users, update invite_codes

Revision ID: a1b2c3d4e5f6
Revises: 09543a4b0ad7
Create Date: 2026-07-16 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "09543a4b0ad7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users table ──────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "feature_overrides",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
            comment="List of feature strings granted beyond the user's role",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "permissions_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Increment to force frontend cache-bust of permissions",
        ),
    )

    # ── invite_codes table ───────────────────────────────────────────────
    op.add_column(
        "invite_codes",
        sa.Column(
            "allowed_roles",
            sa.JSON(),
            nullable=True,
            comment="List of roles the invitee can choose from (null = single role only)",
        ),
    )
    op.add_column(
        "invite_codes",
        sa.Column(
            "granted_features",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
            comment="Additional feature overrides granted to the user upon accepting",
        ),
    )
    op.add_column(
        "invite_codes",
        sa.Column(
            "max_uses",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Maximum number of times this code can be used (1 = single-use, 0 = unlimited)",
        ),
    )
    op.add_column(
        "invite_codes",
        sa.Column(
            "use_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of times this code has been used",
        ),
    )


def downgrade() -> None:
    # ── invite_codes table ───────────────────────────────────────────────
    op.drop_column("invite_codes", "use_count")
    op.drop_column("invite_codes", "max_uses")
    op.drop_column("invite_codes", "granted_features")
    op.drop_column("invite_codes", "allowed_roles")

    # ── users table ──────────────────────────────────────────────────────
    op.drop_column("users", "permissions_version")
    op.drop_column("users", "feature_overrides")
