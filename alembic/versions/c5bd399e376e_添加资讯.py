"""'添加资讯'

Revision ID: c5bd399e376e
Revises: 01bfbbb340b2
Create Date: 2018-11-12 16:09:08.229762

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5bd399e376e'
down_revision = '01bfbbb340b2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('News',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NEid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=False),
    sa.Column('NEtitle', sa.String(length=32), nullable=False),
    sa.Column('NEtext', sa.Text(), nullable=True),
    sa.Column('NEstatus', sa.Integer(), nullable=True),
    sa.Column('NEpageviews', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('NEid')
    )
    op.create_table('NewsComment',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NCid', sa.String(length=64), nullable=False),
    sa.Column('NEid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=False),
    sa.Column('NCtext', sa.String(length=140), nullable=True),
    sa.Column('NCparentid', sa.String(length=64), nullable=True),
    sa.PrimaryKeyConstraint('NCid')
    )
    op.create_table('NewsFavorite',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NEFid', sa.String(length=64), nullable=False),
    sa.Column('NEid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('NEFid')
    )
    op.create_table('NewsImage',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NIid', sa.String(length=64), nullable=False),
    sa.Column('NIimage', sa.String(length=255), nullable=False),
    sa.Column('NIsort', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('NIid')
    )
    op.create_table('NewsTag',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NTid', sa.String(length=64), nullable=False),
    sa.Column('NEid', sa.String(length=64), nullable=False),
    sa.Column('ITid', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('NTid')
    )
    op.create_table('NewsTrample',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NETid', sa.String(length=64), nullable=False),
    sa.Column('NEid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('NETid')
    )
    op.create_table('NewsVideo',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NVid', sa.String(length=64), nullable=False),
    sa.Column('NVvideo', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('NVid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('NewsVideo')
    op.drop_table('NewsTrample')
    op.drop_table('NewsTag')
    op.drop_table('NewsImage')
    op.drop_table('NewsFavorite')
    op.drop_table('NewsComment')
    op.drop_table('News')
    # ### end Alembic commands ###
