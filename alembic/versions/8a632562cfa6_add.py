"""'add'

Revision ID: 8a632562cfa6
Revises: 62233ad25f9f
Create Date: 2019-04-18 16:36:02.752218

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a632562cfa6'
down_revision = '62233ad25f9f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Supplizer', sa.Column('SUgrade', sa.Integer(), nullable=True))
    op.add_column('User', sa.Column('USgrade', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('User', 'USgrade')
    op.drop_column('Supplizer', 'SUgrade')
    # ### end Alembic commands ###
