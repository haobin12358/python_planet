"""'add'

Revision ID: 64c2674daf14
Revises: d6c789595c6d
Create Date: 2018-11-15 18:21:38.976941

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '64c2674daf14'
down_revision = 'd6c789595c6d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('UserSignIn',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('UIid', sa.String(length=64), nullable=False),
    sa.Column('USid', sa.String(length=64), nullable=True),
    sa.Column('UIintegral', sa.Integer(), nullable=True),
    sa.Column('UIaction', sa.Integer(), nullable=True),
    sa.Column('UItype', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('UIid')
    )
    op.drop_column('Admin', 'ADcreateTime')
    op.drop_column('AdminNotes', 'ANcreateTime')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('AdminNotes', sa.Column('ANcreateTime', mysql.DATETIME(), nullable=True))
    op.add_column('Admin', sa.Column('ADcreateTime', mysql.DATETIME(), nullable=True))
    op.drop_table('UserSignIn')
    # ### end Alembic commands ###