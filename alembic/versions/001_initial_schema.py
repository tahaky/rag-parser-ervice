"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('format', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create document_structures table
    op.create_table(
        'document_structures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('format', sa.String(50), nullable=False),
        sa.Column('structure', postgresql.JSONB(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=False),
        sa.Column('stats', postgresql.JSONB(), nullable=False),
        sa.Column('parsed_at', sa.DateTime(), nullable=False),
        sa.Column('parse_duration_ms', sa.Integer(), nullable=False),
        sa.Column('parser_version', sa.String(50), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=True),
    )

    # Create indexes
    op.create_index('ix_document_structures_document_id', 'document_structures', ['document_id'])
    op.create_index('ix_document_structures_checksum', 'document_structures', ['checksum'])


def downgrade() -> None:
    op.drop_index('ix_document_structures_checksum')
    op.drop_index('ix_document_structures_document_id')
    op.drop_table('document_structures')
    op.drop_table('documents')
