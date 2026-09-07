"""add job seniority column

Revision ID: a08d381e0d7e
Revises: 8784120fba51
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a08d381e0d7e'
down_revision: Union[str, Sequence[str], None] = '8784120fba51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("seniority", sa.String(), nullable=True))
    op.create_check_constraint(
        "ck_job_seniority",
        "jobs",
        "seniority in ('junior','mid','senior')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_job_seniority", "jobs", type_="check")
    op.drop_column("jobs", "seniority")
