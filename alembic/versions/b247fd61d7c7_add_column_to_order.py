"""add column to order

Revision ID: b247fd61d7c7
Revises: 98dcbe12bb58
Create Date: 2018-11-02 16:57:02.415229

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b247fd61d7c7'
down_revision = '98dcbe12bb58'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('OrderPart', sa.Column('PRid', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('OrderPart', 'PRid')
    # ### end Alembic commands ###
