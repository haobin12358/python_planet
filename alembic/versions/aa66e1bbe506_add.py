"""'add'

Revision ID: aa66e1bbe506
Revises: c60527e297dd
Create Date: 2019-03-31 21:24:44.041248

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa66e1bbe506'
down_revision = 'c60527e297dd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Products', sa.Column('PRpromotion', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Products', 'PRpromotion')
    # ### end Alembic commands ###
