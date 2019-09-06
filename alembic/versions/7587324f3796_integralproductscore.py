"""integralProductScore

Revision ID: 7587324f3796
Revises: bcc562167299
Create Date: 2019-04-22 16:27:41.578695

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7587324f3796'
down_revision = 'bcc562167299'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('IntegralProduct', sa.Column('IPaverageScore', sa.Float(precision=10), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('IntegralProduct', 'IPaverageScore')
    # ### end Alembic commands ###
