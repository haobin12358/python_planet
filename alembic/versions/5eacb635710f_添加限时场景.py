"""添加限时场景

Revision ID: 5eacb635710f
Revises: 818011ad3817
Create Date: 2019-03-14 00:50:26.571815

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5eacb635710f'
down_revision = '818011ad3817'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ProductScene', sa.Column('PSendtime', sa.DateTime(), nullable=True))
    op.add_column('ProductScene', sa.Column('PSstarttime', sa.DateTime(), nullable=True))
    op.add_column('ProductScene', sa.Column('PStimelimited', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ProductScene', 'PStimelimited')
    op.drop_column('ProductScene', 'PSstarttime')
    op.drop_column('ProductScene', 'PSendtime')
    # ### end Alembic commands ###
