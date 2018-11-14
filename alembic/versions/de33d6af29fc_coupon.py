"""coupon

Revision ID: de33d6af29fc
Revises: 078caa9902de
Create Date: 2018-11-14 13:59:10.662604

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'de33d6af29fc'
down_revision = '078caa9902de'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Coupon',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('COid', sa.String(length=64), nullable=False),
    sa.Column('PCid', sa.String(length=64), nullable=True),
    sa.Column('PRid', sa.String(length=64), nullable=True),
    sa.Column('PBid', sa.String(length=64), nullable=True),
    sa.Column('COname', sa.String(length=32), nullable=True),
    sa.Column('COisAvailable', sa.Boolean(), nullable=True),
    sa.Column('COcanCollect', sa.Boolean(), nullable=True),
    sa.Column('COlimitNum', sa.Integer(), nullable=True),
    sa.Column('COcollectNum', sa.Integer(), nullable=True),
    sa.Column('COsendStarttime', sa.DateTime(), nullable=True),
    sa.Column('COsendEndtime', sa.DateTime(), nullable=True),
    sa.Column('COvalidStartTime', sa.DateTime(), nullable=True),
    sa.Column('COvalieEndTime', sa.DateTime(), nullable=True),
    sa.Column('COdiscount', sa.Float(), nullable=True),
    sa.Column('COdownLine', sa.Float(), nullable=True),
    sa.Column('COsubtration', sa.Float(), nullable=True),
    sa.Column('COdesc', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('COid')
    )
    op.create_table('CouponItem',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('CIid', sa.String(length=64), nullable=False),
    sa.Column('COid', sa.String(length=64), nullable=False),
    sa.Column('ITid', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('CIid')
    )
    op.create_table('UserCoupon',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('UCid', sa.String(length=64), nullable=False),
    sa.Column('COid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=False),
    sa.Column('UCuserStatus', sa.Integer(), nullable=True),
    sa.Column('UCstatus', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('UCid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('UserCoupon')
    op.drop_table('CouponItem')
    op.drop_table('Coupon')
    # ### end Alembic commands ###
