"""guess num add column

Revision ID: fa4cfe3c88f5
Revises: 2875f4e75e4c
Create Date: 2018-11-23 19:21:02.115050

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa4cfe3c88f5'
down_revision = '2875f4e75e4c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('GuessNum', sa.Column('GNdate', sa.Date(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('GuessNum', 'GNdate')
    # ### end Alembic commands ###
