"""widen job scope constraint to allow discard

Revision ID: 3eaf66d230ed
Revises: 3a4c383979a0
Create Date: 2026-09-06 19:30:29.057442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = '3eaf66d230ed'
down_revision: Union[str, Sequence[str], None] = '3a4c383979a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_job_scope", "jobs", type_="check")
    op.create_check_constraint(
        "ck_job_scope", "jobs", "scope in ('local','international','discard')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_job_scope", "jobs", type_="check")
    op.create_check_constraint(
        "ck_job_scope", "jobs", "scope in ('local','international')"
    )
