"""refactor: new models (chapters, questions, quiz_attempts, chapter_mastery)

Revision ID: b2c3d4e5f6a7
Revises: a4a442ddffb5
Create Date: 2026-05-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a4a442ddffb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop enum types first (may exist from create_all())
    op.execute("DROP TYPE IF EXISTS documentstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS questiontype CASCADE")
    op.execute("DROP TYPE IF EXISTS difficulty CASCADE")

    # Drop old tables
    op.execute("DROP TABLE IF EXISTS results CASCADE")
    op.execute("DROP TABLE IF EXISTS quizzes CASCADE")
    
    # Drop new tables if they were created by create_all()
    op.execute("DROP TABLE IF EXISTS chapter_mastery CASCADE")
    op.execute("DROP TABLE IF EXISTS quiz_attempts CASCADE")
    op.execute("DROP TABLE IF EXISTS questions CASCADE")
    op.execute("DROP TABLE IF EXISTS chapters CASCADE")

    # Alter documents table (only if old columns exist)
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS preview_text")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS extracted_text")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS file_type")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS file_size")

    # Rename file_url → cloudinary_url if old column exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='file_url'
            ) THEN
                ALTER TABLE documents RENAME COLUMN file_url TO cloudinary_url;
            END IF;
        END $$;
    """)

    # Add new columns if they don't exist
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_filename VARCHAR")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS cloudinary_public_id VARCHAR")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS total_pages INTEGER")

    # Add status column with proper enum handling
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'documentstatus') THEN
                CREATE TYPE documentstatus AS ENUM ('processing', 'ready', 'failed');
            END IF;
        END $$;
    """)
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status documentstatus DEFAULT 'processing'")

    # Create chapters table
    op.create_table('chapters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('knowledge_graph', postgresql.JSONB(), nullable=True),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chapters_id', 'chapters', ['id'], unique=False)

    # Create questions table
    op.create_table('questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('subject_tag', sa.String(), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.Enum('multiple_choice', 'essay', 'short_answer', name='questiontype'), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hots', name='difficulty'), nullable=True, server_default='medium'),
        sa.Column('options', postgresql.JSONB(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('reference_facts', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_questions_id', 'questions', ['id'], unique=False)

    # Create quiz_attempts table
    op.create_table('quiz_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hots', name='difficulty'), nullable=True, server_default='medium'),
        sa.Column('total_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('answers', postgresql.JSONB(), nullable=True),
        sa.Column('time_taken_seconds', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_quiz_attempts_id', 'quiz_attempts', ['id'], unique=False)

    # Create chapter_mastery table
    op.create_table('chapter_mastery',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('mastery_percentage', sa.Float(), nullable=True, server_default='0.0'),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chapter_mastery_id', 'chapter_mastery', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chapter_mastery_id'), table_name='chapter_mastery')
    op.drop_table('chapter_mastery')
    op.drop_index(op.f('ix_quiz_attempts_id'), table_name='quiz_attempts')
    op.drop_table('quiz_attempts')
    op.drop_index(op.f('ix_questions_id'), table_name='questions')
    op.drop_table('questions')
    op.drop_index(op.f('ix_chapters_id'), table_name='chapters')
    op.drop_table('chapters')

    op.alter_column('documents', 'cloudinary_url', new_column_name='file_url')
    op.drop_column('documents', 'status')
    op.drop_column('documents', 'total_pages')
    op.drop_column('documents', 'cloudinary_public_id')
    op.drop_column('documents', 'original_filename')
    op.add_column('documents', sa.Column('file_type', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('extracted_text', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('preview_text', sa.String(length=500), nullable=True))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table('quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='difficultyenum'), nullable=True),
        sa.Column('generated_questions', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_quizzes_id'), 'quizzes', ['id'], unique=False)
    op.create_table('results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('knowledge_gap_analysis', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_results_id'), 'results', ['id'], unique=False)
