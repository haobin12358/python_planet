"""品牌状态

Revision ID: 002a5c0b049e
Revises: f8dbfb0ad4b3
Create Date: 2018-11-08 14:12:49.404225

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002a5c0b049e'
down_revision = 'f8dbfb0ad4b3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ProductBrand', sa.Column('PBstatus', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ProductBrand', 'PBstatus')
    # ### end Alembic commands ###
