"""Allow text-only complaints."""
from alembic import op
import sqlalchemy as sa


revision = "0002_nullable_complaint_media_type"
down_revision = "0001_initial_rail_madad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("complaints") as batch_op:
        batch_op.alter_column("media_type", existing_type=sa.Enum("image", "video", "audio", name="mediatype"), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("complaints") as batch_op:
        batch_op.alter_column("media_type", existing_type=sa.Enum("image", "video", "audio", name="mediatype"), nullable=False)