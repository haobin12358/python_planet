"""news_add_coupon_and_product

Revision ID: 3541b44d30e9
Revises: 039440f58f61
Create Date: 2018-11-26 10:48:51.899583

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3541b44d30e9'
down_revision = '039440f58f61'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('News', sa.Column('COid', sa.Text(), nullable=True))
    op.add_column('News', sa.Column('PRid', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('News', 'PRid')
    op.drop_column('News', 'COid')
    # ### end Alembic commands ###
