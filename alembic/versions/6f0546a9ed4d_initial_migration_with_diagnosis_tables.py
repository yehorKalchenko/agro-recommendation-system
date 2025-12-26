from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6f0546a9ed4d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pg_trgm extension for trigram text search
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    op.create_table('api_keys',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('key_hash', sa.String(length=128), nullable=False),
    sa.Column('key_name', sa.String(length=100), nullable=False),
    sa.Column('is_active', sa.Integer(), nullable=False),
    sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
    sa.Column('total_requests', sa.Integer(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('created_by', sa.String(length=100), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)
    op.create_table('diagnosis_cases',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('crop', sa.String(length=50), nullable=False),
    sa.Column('growth_stage', sa.String(length=50), nullable=True),
    sa.Column('symptoms_text', sa.Text(), nullable=False),
    sa.Column('location_lat', sa.Float(), nullable=True),
    sa.Column('location_lon', sa.Float(), nullable=True),
    sa.Column('candidates', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('action_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('disclaimers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('debug_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('visual_features', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_created_crop', 'diagnosis_cases', ['created_at', 'crop'], unique=False)
    op.create_index('idx_symptoms_text_gin', 'diagnosis_cases', ['symptoms_text'], unique=False, postgresql_using='gin', postgresql_ops={'symptoms_text': 'gin_trgm_ops'})
    op.create_index(op.f('ix_diagnosis_cases_created_at'), 'diagnosis_cases', ['created_at'], unique=False)
    op.create_index(op.f('ix_diagnosis_cases_crop'), 'diagnosis_cases', ['crop'], unique=False)
    op.create_table('diagnosis_images',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('case_id', sa.UUID(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=50), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('image_data', sa.LargeBinary(), nullable=True),
    sa.Column('s3_url', sa.String(length=512), nullable=True),
    sa.Column('s3_bucket', sa.String(length=128), nullable=True),
    sa.Column('s3_key', sa.String(length=512), nullable=True),
    sa.Column('width', sa.Integer(), nullable=True),
    sa.Column('height', sa.Integer(), nullable=True),
    sa.Column('exif_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_case_images', 'diagnosis_images', ['case_id', 'uploaded_at'], unique=False)
    op.create_index(op.f('ix_diagnosis_images_case_id'), 'diagnosis_images', ['case_id'], unique=False)
    op.create_table('usage_metrics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('endpoint', sa.String(length=100), nullable=False),
    sa.Column('method', sa.String(length=10), nullable=False),
    sa.Column('crop', sa.String(length=50), nullable=True),
    sa.Column('response_time_ms', sa.Float(), nullable=False),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('cv_time_ms', sa.Float(), nullable=True),
    sa.Column('retrieval_time_ms', sa.Float(), nullable=True),
    sa.Column('rules_time_ms', sa.Float(), nullable=True),
    sa.Column('llm_time_ms', sa.Float(), nullable=True),
    sa.Column('api_key_id', sa.UUID(), nullable=True),
    sa.Column('error_type', sa.String(length=100), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_timestamp_endpoint', 'usage_metrics', ['timestamp', 'endpoint'], unique=False)
    op.create_index(op.f('ix_usage_metrics_api_key_id'), 'usage_metrics', ['api_key_id'], unique=False)
    op.create_index(op.f('ix_usage_metrics_crop'), 'usage_metrics', ['crop'], unique=False)
    op.create_index(op.f('ix_usage_metrics_endpoint'), 'usage_metrics', ['endpoint'], unique=False)
    op.create_index(op.f('ix_usage_metrics_timestamp'), 'usage_metrics', ['timestamp'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_usage_metrics_timestamp'), table_name='usage_metrics')
    op.drop_index(op.f('ix_usage_metrics_endpoint'), table_name='usage_metrics')
    op.drop_index(op.f('ix_usage_metrics_crop'), table_name='usage_metrics')
    op.drop_index(op.f('ix_usage_metrics_api_key_id'), table_name='usage_metrics')
    op.drop_index('idx_timestamp_endpoint', table_name='usage_metrics')
    op.drop_table('usage_metrics')
    op.drop_index(op.f('ix_diagnosis_images_case_id'), table_name='diagnosis_images')
    op.drop_index('idx_case_images', table_name='diagnosis_images')
    op.drop_table('diagnosis_images')
    op.drop_index(op.f('ix_diagnosis_cases_crop'), table_name='diagnosis_cases')
    op.drop_index(op.f('ix_diagnosis_cases_created_at'), table_name='diagnosis_cases')
    op.drop_index('idx_symptoms_text_gin', table_name='diagnosis_cases', postgresql_using='gin', postgresql_ops={'symptoms_text': 'gin_trgm_ops'})
    op.drop_index('idx_created_crop', table_name='diagnosis_cases')
    op.drop_table('diagnosis_cases')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')
    # ### end Alembic commands ###
