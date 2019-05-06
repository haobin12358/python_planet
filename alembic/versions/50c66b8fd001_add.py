"""'add'

Revision ID: 50c66b8fd001
Revises: f1b7f97b51f8
Create Date: 2019-04-27 16:31:31.691079

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '50c66b8fd001'
down_revision = 'f1b7f97b51f8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('CouponCode', sa.Column('CCused', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('CouponCode', 'CCused')
    # ### end Alembic commands ###