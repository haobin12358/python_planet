"""'add'

Revision ID: 03b5e6076e08
Revises: 8a4e12f109b8
Create Date: 2019-01-07 22:53:53.481031

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03b5e6076e08'
down_revision = '8a4e12f109b8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'ProductSku', ['SKUsn'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'ProductSku', type_='unique')
    # ### end Alembic commands ###
