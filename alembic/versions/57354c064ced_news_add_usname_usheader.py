"""news_add_usname_usheader

Revision ID: 57354c064ced
Revises: 1d8a7d1d164c
Create Date: 2018-12-14 20:05:29.518966

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57354c064ced'
down_revision = '1d8a7d1d164c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('News', sa.Column('USheader', sa.Text(), nullable=True))
    op.add_column('News', sa.Column('USname', sa.String(length=255), nullable=True))
    op.add_column('NewsComment', sa.Column('USheader', sa.Text(), nullable=True))
    op.add_column('NewsComment', sa.Column('USname', sa.String(length=255), nullable=True))
    op.add_column('OrderEvaluation', sa.Column('USheader', sa.Text(), nullable=True))
    op.add_column('OrderEvaluation', sa.Column('USname', sa.String(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('OrderEvaluation', 'USname')
    op.drop_column('OrderEvaluation', 'USheader')
    op.drop_column('NewsComment', 'USname')
    op.drop_column('NewsComment', 'USheader')
    op.drop_column('News', 'USname')
    op.drop_column('News', 'USheader')
    # ### end Alembic commands ###
