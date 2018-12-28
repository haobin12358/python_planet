"""佣金表加字段

Revision ID: 72d56935126b
Revises: ac5192fdd476
Create Date: 2018-12-28 17:31:06.024678

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '72d56935126b'
down_revision = 'ac5192fdd476'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('AdminPermission',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('ADPid', sa.String(length=64), nullable=False),
    sa.Column('ADid', sa.String(length=64), nullable=True),
    sa.Column('PIid', sa.String(length=64), nullable=True),
    sa.PrimaryKeyConstraint('ADPid')
    )
    op.create_table('PermissionItems',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('PIid', sa.String(length=64), nullable=False),
    sa.Column('PIname', sa.Text(), nullable=True),
    sa.Column('PIstatus', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('PIid')
    )
    op.create_table('PermissionNotes',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('PNid', sa.String(length=64), nullable=False),
    sa.Column('ADid', sa.String(length=64), nullable=True),
    sa.Column('PNcontent', sa.String(length=64), nullable=True),
    sa.Column('PINaction', sa.Text(), nullable=True),
    sa.Column('PNType', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('PNid')
    )
    op.create_table('PermissionType',
    sa.Column('isdelete', sa.Boolean(), nullable=True),
    sa.Column('createtime', sa.DateTime(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('PTid', sa.String(length=64), nullable=False),
    sa.Column('PTname', sa.Text(), nullable=True),
    sa.Column('PTmodelName', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('PTid')
    )
    op.add_column('Approval', sa.Column('PTid', sa.String(length=64), nullable=True))
    op.drop_column('Approval', 'AVtype')
    op.alter_column('MagicBoxApply', 'SUid',
               existing_type=mysql.VARCHAR(length=64),
               nullable=True)
    op.add_column('Permission', sa.Column('PIid', sa.String(length=64), nullable=True))
    op.add_column('Permission', sa.Column('PTid', sa.String(length=64), nullable=True))
    op.drop_column('Permission', 'ADid')
    op.drop_column('Permission', 'PEtype')
    op.add_column('UserCommission', sa.Column('FromUsid', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('UserCommission', 'FromUsid')
    op.add_column('Permission', sa.Column('PEtype', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False))
    op.add_column('Permission', sa.Column('ADid', mysql.VARCHAR(length=64), nullable=False))
    op.drop_column('Permission', 'PTid')
    op.drop_column('Permission', 'PIid')
    op.alter_column('MagicBoxApply', 'SUid',
               existing_type=mysql.VARCHAR(length=64),
               nullable=False)
    op.add_column('Approval', sa.Column('AVtype', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.drop_column('Approval', 'PTid')
    op.drop_table('PermissionType')
    op.drop_table('PermissionNotes')
    op.drop_table('PermissionItems')
    op.drop_table('AdminPermission')
    # ### end Alembic commands ###
