"""'add'

Revision ID: f1b7f97b51f8
Revises: ac58b9829363
Create Date: 2019-04-27 15:07:32.872138

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1b7f97b51f8'
down_revision = 'ac58b9829363'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Entry', sa.Column('ENtype', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Entry', 'ENtype')
    # ### end Alembic commands ###