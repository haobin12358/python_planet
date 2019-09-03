"""alter product and sku

Revision ID: a84bf80f8d7f
Revises: 8ab0a32f9e9b
Create Date: 2018-11-05 18:26:36.963045

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a84bf80f8d7f'
down_revision = '8ab0a32f9e9b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ProductSku', sa.Column('SKUattriteDetail', sa.Text(), nullable=True))
    op.drop_column('ProductSku', 'SKUdetail')
    op.add_column('ProductSkuValue', sa.Column('PCid', sa.String(length=64), nullable=False))
    op.drop_column('ProductSkuValue', 'PRid')
    op.add_column('Products', sa.Column('PRattribute', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Products', 'PRattribute')
    op.add_column('ProductSkuValue', sa.Column('PRid', mysql.VARCHAR(collation='utf8_bin', length=64), nullable=False))
    op.drop_column('ProductSkuValue', 'PCid')
    op.add_column('ProductSku', sa.Column('SKUdetail', mysql.TEXT(collation='utf8_bin'), nullable=True))
    op.drop_column('ProductSku', 'SKUattriteDetail')
    # ### end Alembic commands ###
