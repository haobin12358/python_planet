"""add_news_changelog

Revision ID: 2a0cfc521241
Revises: aeadee3b5044
Create Date: 2018-12-29 15:45:07.584950

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a0cfc521241'
down_revision = 'aeadee3b5044'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('NewsChangelog',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('NCLid', sa.String(length=64), nullable=False),
    sa.Column('NEid', sa.String(length=64), nullable=False),
    sa.Column('ADid', sa.String(length=64), nullable=False),
    sa.Column('NCLoperation', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('NCLid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('NewsChangelog')
    # ### end Alembic commands ###
