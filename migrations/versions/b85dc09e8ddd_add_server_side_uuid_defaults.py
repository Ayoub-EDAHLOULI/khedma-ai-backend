"""add server-side uuid defaults

Revision ID: b85dc09e8ddd
Revises: 3a701b6e34b2
Create Date: 2026-09-06 17:19:17.615400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = 'b85dc09e8ddd'
down_revision: Union[str, Sequence[str], None] = '3a701b6e34b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = ["jobs", "profiles", "matches", "applications"]


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "id", server_default=sa.text("gen_random_uuid()"))


def downgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "id", server_default=None)
