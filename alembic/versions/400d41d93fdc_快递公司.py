"""快递公司

Revision ID: 400d41d93fdc
Revises: c5bd399e376e
Create Date: 2018-11-12 17:57:30.138918

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '400d41d93fdc'
down_revision = 'c5bd399e376e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('LogisticsCompnay',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('_id', sa.String(length=64), nullable=False),
    sa.Column('LCname', sa.String(length=32), nullable=False),
    sa.Column('LCcode', sa.String(length=32), nullable=False),
    sa.PrimaryKeyConstraint('_id')
    )
    op.create_index(op.f('ix_LogisticsCompnay_LCcode'), 'LogisticsCompnay', ['LCcode'], unique=False)
    op.create_index(op.f('ix_LogisticsCompnay_LCname'), 'LogisticsCompnay', ['LCname'], unique=False)
    op.drop_column('NewsImage', 'NEid')
    op.drop_column('NewsVideo', 'NEid')
    op.add_column('ProductSkuValue', sa.Column('PRid', sa.String(length=64), nullable=False))
    op.drop_column('ProductSkuValue', 'PCid')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ProductSkuValue', sa.Column('PCid', mysql.VARCHAR(collation='utf8_bin', length=64), nullable=False))
    op.drop_column('ProductSkuValue', 'PRid')
    op.add_column('NewsVideo', sa.Column('NEid', mysql.VARCHAR(length=64), nullable=False))
    op.add_column('NewsImage', sa.Column('NEid', mysql.VARCHAR(length=64), nullable=False))
    op.drop_index(op.f('ix_LogisticsCompnay_LCname'), table_name='LogisticsCompnay')
    op.drop_index(op.f('ix_LogisticsCompnay_LCcode'), table_name='LogisticsCompnay')
    op.drop_table('LogisticsCompnay')
    # ### end Alembic commands ###
