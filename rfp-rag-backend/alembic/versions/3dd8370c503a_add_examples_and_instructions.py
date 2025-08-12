from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Revision identifiers, used by Alembic.
revision = "3dd8370c503a"
# IMPORTANT: set this to your current head. Run `alembic heads` and copy the id
# e.g., down_revision = "3f9c1b2d4e5f"
down_revision = "64bc8e2515ef" # <-- REPLACE with your latest revision id
branch_labels = None
depends_on = None


def upgrade():
    # 1) proposal_examples
    op.create_table(
        "proposal_examples",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("client_type", sa.String(), nullable=True),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("contract_vehicle", sa.String(), nullable=True),
        sa.Column("complexity_tier", sa.String(), nullable=True),
        sa.Column("tags", JSONB, nullable=True),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("ingest_status", sa.String(), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 2) example_sections
    op.create_table(
        "example_sections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("example_id", UUID(as_uuid=True), sa.ForeignKey("proposal_examples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_key", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_example_sections_section_key", "example_sections", ["section_key"], unique=False)

    # 3) section_instructions (history of generated instruction JSON)
    op.create_table(
        "section_instructions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("section_key", sa.String(), nullable=False),
        sa.Column("json", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_section_instructions_project_key",
        "section_instructions",
        ["project_id", "section_key"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_section_instructions_project_key", table_name="section_instructions")
    op.drop_table("section_instructions")
    op.drop_index("ix_example_sections_section_key", table_name="example_sections")
    op.drop_table("example_sections")
    op.drop_table("proposal_examples")
