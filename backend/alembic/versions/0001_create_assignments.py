from alembic import op
import sqlalchemy as sa

revision = "0001_create_assignments"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("course", sa.String(length=120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assignments_due_date", "assignments", ["due_date"])

def downgrade():
    op.drop_index("ix_assignments_due_date", table_name="assignments")
    op.drop_table("assignments")
