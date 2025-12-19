"""add trust badge to normalized listings

Revision ID: 0002_add_trust_badge
Revises: 0001_initial
Create Date: 2024-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_trust_badge"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("normalized_listings", sa.Column("trust_badge", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("normalized_listings", "trust_badge")
