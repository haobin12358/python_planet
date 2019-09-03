"""改表名

Revision ID: 9770a0c9c59f
Revises: de33d6af29fc
Create Date: 2018-11-14 14:24:56.620502

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '9770a0c9c59f'
down_revision = 'de33d6af29fc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('CouponUser',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('UCid', sa.String(length=64), nullable=False),
    sa.Column('COid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=False),
    sa.Column('UCalreadyUse', sa.Integer(), nullable=True),
    sa.Column('UCstatus', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('UCid')
    )
    op.drop_table('UserCoupon')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('UserCoupon',
    sa.Column('isdelete', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('createtime', mysql.DATETIME(), nullable=True),
    sa.Column('updatetime', mysql.DATETIME(), nullable=True),
    sa.Column('UCid', mysql.VARCHAR(length=64), nullable=False),
    sa.Column('COid', mysql.VARCHAR(length=64), nullable=False),
    sa.Column('USid', mysql.VARCHAR(length=64), nullable=False),
    sa.Column('UCalreadyUse', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column('UCstatus', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('UCid'),
    mysql_default_charset='utf8',
    mysql_engine='InnoDB'
    )
    op.drop_table('CouponUser')
    # ### end Alembic commands ###
