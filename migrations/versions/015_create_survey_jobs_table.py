"""Create survey_jobs table

Revision ID: 015_create_survey_jobs_table
Revises: 014_allow_null_email_in_surveys_table
Create Date: 2025-09-26 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '015_create_survey_jobs_table'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Create survey_jobs table
    op.create_table('survey_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['survey_id'], ['surveys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'success', 'failed')", name='check_survey_job_status')
    )
    
    # Create indexes for performance
    op.create_index('ix_survey_jobs_survey_id', 'survey_jobs', ['survey_id'])
    op.create_index('ix_survey_jobs_status', 'survey_jobs', ['status'])
    op.create_index('ix_survey_jobs_next_retry_at', 'survey_jobs', ['next_retry_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_survey_jobs_next_retry_at', 'survey_jobs')
    op.drop_index('ix_survey_jobs_status', 'survey_jobs')
    op.drop_index('ix_survey_jobs_survey_id', 'survey_jobs')
    
    # Drop table
    op.drop_table('survey_jobs')