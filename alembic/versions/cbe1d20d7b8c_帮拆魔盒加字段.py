"""帮拆魔盒加字段

Revision ID: cbe1d20d7b8c
Revises: 1c027d2dd396
Create Date: 2018-12-05 19:45:17.851615

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'cbe1d20d7b8c'
down_revision = '1c027d2dd396'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('FreshManFirstApply',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('FMFAid', sa.String(length=64), nullable=False),
    sa.Column('SUid', sa.String(length=64), nullable=False),
    sa.Column('PRid', sa.String(length=64), nullable=False),
    sa.Column('FMFAstartTime', sa.DateTime(), nullable=False),
    sa.Column('FMFAendTime', sa.DateTime(), nullable=False),
    sa.Column('FMFAstatus', sa.Integer(), nullable=True),
    sa.Column('AgreeStartime', sa.Date(), nullable=True),
    sa.Column('AgreeEndtime', sa.Date(), nullable=True),
    sa.PrimaryKeyConstraint('FMFAid', 'SUid')
    )
    op.drop_table('FreshManFirst')
    op.add_column('MagixBoxOpen', sa.Column('USname', sa.String(length=64), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('MagixBoxOpen', 'USname')
    op.create_table('FreshManFirst',
    sa.Column('isdelete', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('createtime', mysql.DATETIME(), nullable=True),
    sa.Column('updatetime', mysql.DATETIME(), nullable=True),
    sa.Column('FMFAid', mysql.VARCHAR(length=64), nullable=False),
    sa.Column('SUid', mysql.VARCHAR(length=64), nullable=False),
    sa.Column('PRid', mysql.VARCHAR(length=64), nullable=False),
    sa.Column('FMFAstartTime', mysql.DATETIME(), nullable=False),
    sa.Column('FMFAendTime', mysql.DATETIME(), nullable=False),
    sa.Column('FMFAstatus', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column('AgreeStartime', sa.DATE(), nullable=True),
    sa.Column('AgreeEndtime', sa.DATE(), nullable=True),
    sa.PrimaryKeyConstraint('FMFAid', 'SUid'),
    mysql_default_charset='utf8',
    mysql_engine='InnoDB'
    )
    op.drop_table('FreshManFirstApply')
    # ### end Alembic commands ###
