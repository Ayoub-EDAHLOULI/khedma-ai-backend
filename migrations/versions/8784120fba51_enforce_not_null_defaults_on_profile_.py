"""enforce not-null defaults on profile array columns

Revision ID: 8784120fba51
Revises: 3eaf66d230ed
Create Date: 2026-09-06 22:19:48.942050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = '8784120fba51'
down_revision: Union[str, Sequence[str], None] = '3eaf66d230ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = ["target_countries", "skills", "preferred_languages"]


def upgrade() -> None:
    for column in COLUMNS:
        op.execute(f"UPDATE profiles SET {column} = '{{}}' WHERE {column} IS NULL")
        op.alter_column("profiles", column, nullable=False, server_default="{}")


def downgrade() -> None:
    for column in COLUMNS:
        op.alter_column("profiles", column, nullable=True, server_default=None)
