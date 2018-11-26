"""商品-活动奖励

Revision ID: b7c22289a5de
Revises: 20b98987f641
Create Date: 2018-11-26 15:57:59.825140

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c22289a5de'
down_revision = '20b98987f641'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('GuessAwardFlow', sa.Column('PRid', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('GuessAwardFlow', 'PRid')
    # ### end Alembic commands ###
