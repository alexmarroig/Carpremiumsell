"""add seller info to normalized listings

Revision ID: 0003_add_seller_reputation
Revises: 0002_add_trust_badge
Create Date: 2024-01-01 00:00:01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_seller_reputation"
down_revision = "0002_add_trust_badge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("normalized_listings", sa.Column("seller_id", sa.String(), nullable=True))
    op.add_column("normalized_listings", sa.Column("seller_reputation", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("normalized_listings", "seller_reputation")
    op.drop_column("normalized_listings", "seller_id")
