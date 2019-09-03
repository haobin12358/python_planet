"""'add'

Revision ID: 454bbe682c11
Revises: 96e7be500f3f
Create Date: 2019-04-23 13:12:00.115190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '454bbe682c11'
down_revision = '96e7be500f3f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('UserActivationCode', sa.Column('ACAid', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('UserActivationCode', 'ACAid')
    # ### end Alembic commands ###
