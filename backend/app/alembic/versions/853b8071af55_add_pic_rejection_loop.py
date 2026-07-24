"""add_pic_rejection_loop

Revision ID: 853b8071af55
Revises: a1b2c3d4e5f6
Create Date: 2026-07-24 13:42:15.484286

Adds the PIC rejection loop to flight releases:
- safe_for_flight_signed_by / safe_for_flight_signed_at (columns the API already referenced)
- pic_accepted / pic_accepted_at (columns the API already referenced)
- pic_rejected / pic_rejected_at / pic_rejected_by / pic_rejection_reason (new rejection fields)
- in_maintenance status added to release_status CHECK constraint / ENUM
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '853b8071af55'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_context().bind
    is_sqlite = bind.dialect.name == "sqlite"

    # ── New columns ───────────────────────────────────────────────────────
    # safe_for_flight signing info (API-written columns)
    op.add_column('flight_releases', sa.Column(
        'safe_for_flight_signed_by', sa.String(255), nullable=True,
        comment='Name/ID of maintenance who signed safe-for-flight'))
    op.add_column('flight_releases', sa.Column(
        'safe_for_flight_signed_at', sa.DateTime(timezone=True), nullable=True,
        comment='Timestamp of safe-for-flight signature'))

    # PIC acceptance (API-written columns)
    op.add_column('flight_releases', sa.Column(
        'pic_accepted', sa.Boolean(), server_default=sa.text("0"),
        nullable=False,
        comment='True when PIC has accepted the aircraft after maintenance sign-off'))
    op.add_column('flight_releases', sa.Column(
        'pic_accepted_at', sa.DateTime(timezone=True), nullable=True,
        comment='Timestamp of PIC acceptance'))

    # PIC rejection / send-back-to-maintenance
    op.add_column('flight_releases', sa.Column(
        'pic_rejected', sa.Boolean(), server_default=sa.text("0"),
        nullable=False,
        comment='True when PIC rejects the aircraft after maintenance sign-off, sending it back'))
    op.add_column('flight_releases', sa.Column(
        'pic_rejected_at', sa.DateTime(timezone=True), nullable=True,
        comment='Timestamp of PIC rejection'))
    op.add_column('flight_releases', sa.Column(
        'pic_rejected_by', sa.String(255), nullable=True,
        comment='Name/ID of PIC who rejected'))
    op.add_column('flight_releases', sa.Column(
        'pic_rejection_reason', sa.Text(), nullable=True,
        comment='Reason for PIC rejection (gripe description)'))

    # ── Status enum: add 'in_maintenance' ─────────────────────────────────
    if is_sqlite:
        # SQLite uses CHECK constraints, so we batch-recreate the table
        with op.batch_alter_table('flight_releases') as batch_op:
            batch_op.alter_column('status',
                type_=sa.String(20),
                existing_type=sa.String(8),
                existing_nullable=False)
    else:
        op.execute("ALTER TYPE release_status ADD VALUE IF NOT EXISTS 'in_maintenance'")


def downgrade() -> None:
    bind = op.get_context().bind
    is_sqlite = bind.dialect.name == "sqlite"

    # ── Status enum: remove 'in_maintenance' ──────────────────────────────
    if is_sqlite:
        with op.batch_alter_table('flight_releases') as batch_op:
            batch_op.alter_column('status',
                type_=sa.String(8),
                existing_type=sa.String(20),
                existing_nullable=False)
    else:
        op.alter_column('flight_releases', 'status',
            type_=sa.VARCHAR(length=8),
            existing_type=sa.Enum('draft', 'in_maintenance', 'released',
                                  'amended', 'closed',
                                  name='release_status', create_constraint=True),
            existing_nullable=False)

    # ── Drop new columns ──────────────────────────────────────────────────
    op.drop_column('flight_releases', 'pic_rejection_reason')
    op.drop_column('flight_releases', 'pic_rejected_by')
    op.drop_column('flight_releases', 'pic_rejected_at')
    op.drop_column('flight_releases', 'pic_rejected')
    op.drop_column('flight_releases', 'pic_accepted_at')
    op.drop_column('flight_releases', 'pic_accepted')
    op.drop_column('flight_releases', 'safe_for_flight_signed_at')
    op.drop_column('flight_releases', 'safe_for_flight_signed_by')
