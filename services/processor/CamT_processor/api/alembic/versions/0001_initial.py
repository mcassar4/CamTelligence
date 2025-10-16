"""Initial schema for CamTelligence"""

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "media_assets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("media_type", sa.Enum("frame", "person_crop", "vehicle_crop", "other", name="mediatype"), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False, unique=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "vehicle_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("camera", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frame_asset_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("media_assets.id"), nullable=True),
        sa.Column("crop_asset_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("media_assets.id"), nullable=True),
        sa.Column("score", sa.Integer, nullable=True),
        sa.Column("label", sa.String(length=128), nullable=False, server_default="vehicle"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vehicle_events_occurred_at", "vehicle_events", ["occurred_at"])

    op.create_table(
        "person_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("camera", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frame_asset_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("media_assets.id"), nullable=True),
        sa.Column("crop_asset_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("media_assets.id"), nullable=True),
        sa.Column("score", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_person_events_occurred_at", "person_events", ["occurred_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("event_type", sa.Enum("person", "vehicle", name="eventtype"), nullable=False),
        sa.Column("event_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Enum("pending", "sent", "failed", name="notificationstatus"), nullable=False, server_default="pending"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.Enum("queued", "started", "finished", "failed", "dropped", name="jobstatus"), nullable=False, server_default="queued"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("jobs")
    op.drop_table("notifications")
    op.drop_index("ix_person_events_occurred_at", table_name="person_events")
    op.drop_table("person_events")
    op.drop_index("ix_vehicle_events_occurred_at", table_name="vehicle_events")
    op.drop_table("vehicle_events")
    op.drop_table("settings")
    op.drop_table("media_assets")
