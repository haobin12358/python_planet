"""'add'

Revision ID: 90334a8dc89e
Revises: 44b846942959
Create Date: 2019-02-24 18:19:55.952456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90334a8dc89e'
down_revision = '44b846942959'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('GuessNumAwardSku', sa.Column('SKUstock', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('GuessNumAwardSku', 'SKUstock')
    # ### end Alembic commands ###
