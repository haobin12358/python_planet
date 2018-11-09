"""order

Revision ID: 694e0bd72d59
Revises: 9df45281e16e
Create Date: 2018-11-07 15:01:55.492957

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '694e0bd72d59'
down_revision = '9df45281e16e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('OrderRefund',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('ORid', sa.String(length=64), nullable=False),
    sa.Column('OMid', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('ORid')
    )
    op.create_table('OrderRefundApply',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('ORAid', sa.String(length=64), nullable=False),
    sa.Column('OMid', sa.String(length=64), nullable=False),
    sa.Column('OPid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=False),
    sa.Column('ORAstate', sa.Integer(), nullable=True),
    sa.Column('ORAreason', sa.String(length=255), nullable=False),
    sa.Column('ORAstatus', sa.Integer(), nullable=True),
    sa.Column('ORAcheckReason', sa.String(length=255), nullable=True),
    sa.Column('ORAcheckTime', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('ORAid')
    )
    op.add_column('OrderMain', sa.Column('OMinRefund', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('OrderMain', 'OMinRefund')
    op.drop_table('OrderRefundApply')
    op.drop_table('OrderRefund')
    # ### end Alembic commands ###