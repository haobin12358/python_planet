"""记录

Revision ID: d36b852b6041
Revises: 915526dd2a4f
Create Date: 2018-12-11 14:55:12.029103

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd36b852b6041'
down_revision = '915526dd2a4f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Coupon', sa.Column('SUid', sa.String(length=64), nullable=True))
    op.add_column('OrderPart', sa.Column('OPsubTrueTotal', sa.Float(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('OrderPart', 'OPsubTrueTotal')
    op.drop_column('Coupon', 'SUid')
    # ### end Alembic commands ###
