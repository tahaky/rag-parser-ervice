"""Rename metadata column to doc_metadata

Revision ID: 002
Revises: 001
Create Date: 2026-01-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename metadata column to doc_metadata in document_structures table
    op.alter_column('document_structures', 'metadata', new_column_name='doc_metadata')


def downgrade() -> None:
    # Rename doc_metadata column back to metadata
    op.alter_column('document_structures', 'doc_metadata', new_column_name='metadata')
