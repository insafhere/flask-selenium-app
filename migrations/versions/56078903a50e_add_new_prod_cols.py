"""Add new prod cols

Revision ID: 56078903a50e
Revises: 88498aedff10
Create Date: 2024-11-18 14:06:51.393880

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '56078903a50e'
down_revision = '88498aedff10'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ads_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('product_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('product_link', sa.String(length=400), nullable=True))
        batch_op.add_column(sa.Column('product_created_date', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('product_created_days_ago', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ads_data', schema=None) as batch_op:
        batch_op.drop_column('product_created_days_ago')
        batch_op.drop_column('product_created_date')
        batch_op.drop_column('product_link')
        batch_op.drop_column('product_name')

    # ### end Alembic commands ###
