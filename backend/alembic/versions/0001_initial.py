from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "listing_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_table(
        "search_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
    )
    op.create_table(
        "raw_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("listing_sources.id"), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "normalized_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("listing_sources.id"), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("brand", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("trim", sa.String()),
        sa.Column("year", sa.Integer()),
        sa.Column("mileage_km", sa.Integer()),
        sa.Column("price_brl", sa.Float()),
        sa.Column("supplier_price_brl", sa.Float()),
        sa.Column("final_price_brl", sa.Float()),
        sa.Column("city", sa.String()),
        sa.Column("state", sa.String()),
        sa.Column("lat", sa.Float()),
        sa.Column("lng", sa.Float()),
        sa.Column("photos", sa.JSON(), server_default=sa.text("'[]'")),
        sa.Column("url", sa.String()),
        sa.Column("seller_type", sa.String()),
        sa.Column("status", sa.String(), server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "market_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("region_key", sa.String(), nullable=False),
        sa.Column("brand", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("trim", sa.String()),
        sa.Column("year_range", sa.String()),
        sa.Column("median_price", sa.Float()),
        sa.Column("p25", sa.Float()),
        sa.Column("p75", sa.Float()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("query_text", sa.String(), nullable=False),
        sa.Column("chosen_listing_id", sa.Integer(), sa.ForeignKey("normalized_listings.id")),
        sa.Column("rationale_text", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("query_json", sa.JSON(), nullable=False),
        sa.Column("region_key", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("recommendations")
    op.drop_table("market_stats")
    op.drop_table("normalized_listings")
    op.drop_table("raw_listings")
    op.drop_table("search_profiles")
    op.drop_table("listing_sources")
    op.drop_table("users")
