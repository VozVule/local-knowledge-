"""add app_config

Revision ID: 1fe881c343cf
Revises: 404ac47ca991
Create Date: 2026-01-05 21:43:17.262758

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1fe881c343cf'
down_revision = '404ac47ca991'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TABLE IF EXISTS app_config")
    op.create_table(
        'app_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=False),
        sa.Column('model_type', sa.String(length=32), nullable=False),
    )
    op.create_index('ix_app_config_provider', 'app_config', ['provider'])


def downgrade():
    op.drop_index('ix_app_config_provider', table_name='app_config')
    op.drop_table('app_config')
