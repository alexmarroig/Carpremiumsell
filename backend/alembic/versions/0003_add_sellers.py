"""add seller entities and stats

Revision ID: 0003_add_sellers
Revises: 0002_add_trust_badge
Create Date: 2024-01-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_add_sellers"
down_revision = "0002_add_trust_badge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sellers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("reputation_medal", sa.String(), nullable=True),
        sa.Column("reputation_score", sa.Float(), nullable=True),
        sa.Column("cancellations", sa.Integer(), nullable=True),
        sa.Column("response_time_hours", sa.Float(), nullable=True),
        sa.Column("completed_sales", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["listing_sources.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("origin", "external_id", name="uq_seller_origin_external"),
    )

    op.add_column("normalized_listings", sa.Column("seller_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_normalized_listings_seller_id",
        "normalized_listings",
        "sellers",
        ["seller_id"],
        ["id"],
    )

    op.create_table(
        "seller_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("average_price_brl", sa.Float(), nullable=True),
        sa.Column("listings_count", sa.Integer(), nullable=True),
        sa.Column("completed_sales", sa.Integer(), nullable=True),
        sa.Column("problem_rate", sa.Float(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seller_id"),
    )


def downgrade() -> None:
    op.drop_table("seller_stats")
    op.drop_constraint("fk_normalized_listings_seller_id", "normalized_listings", type_="foreignkey")
    op.drop_column("normalized_listings", "seller_id")
    op.drop_table("sellers")
