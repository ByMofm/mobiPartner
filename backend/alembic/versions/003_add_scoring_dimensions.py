"""Add zone_score, condition_score, overall_score columns and zone_qualities/image_analyses tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns on properties
    op.add_column("properties", sa.Column("zone_score", sa.Integer(), nullable=True))
    op.add_column("properties", sa.Column("condition_score", sa.Integer(), nullable=True))
    op.add_column("properties", sa.Column("overall_score", sa.Integer(), nullable=True))

    # zone_qualities table
    op.create_table(
        "zone_qualities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("safety_score", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("overall_zone_score", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("location_id", name="uq_zone_quality_location"),
    )

    # image_analyses table
    op.create_table(
        "image_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("condition_score", sa.Integer(), nullable=True),
        sa.Column("condition_label", sa.String(50), nullable=True),
        sa.Column("renovation_state", sa.String(50), nullable=True),
        sa.Column("natural_light", sa.Integer(), nullable=True),
        sa.Column("cleanliness", sa.Integer(), nullable=True),
        sa.Column("raw_analysis", JSONB(), nullable=True),
        sa.Column("images_analyzed", sa.Integer(), default=0),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("property_id", name="uq_image_analysis_property"),
    )


def downgrade() -> None:
    op.drop_table("image_analyses")
    op.drop_table("zone_qualities")
    op.drop_column("properties", "overall_score")
    op.drop_column("properties", "condition_score")
    op.drop_column("properties", "zone_score")
