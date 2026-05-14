"""Add new fields: user profile, question details, xp, notifications

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-14 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users: add new profile fields
    for col, col_type in [
        ("academic_level", sa.String()),
        ("major", sa.String()),
    ]:
        op.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} VARCHAR")
    for col, col_type, default in [
        ("xp_points", sa.Integer(), "0"),
        ("streak_days", sa.Integer(), "0"),
        ("subjects_mastered", sa.Integer(), "0"),
    ]:
        op.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} INTEGER DEFAULT {default}")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_date DATE")

    # Questions: add new fields
    op.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_description TEXT")
    op.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS hint TEXT")
    op.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
    op.execute("ALTER TABLE questions ALTER COLUMN correct_answer DROP NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN correct_answer TYPE VARCHAR USING correct_answer::VARCHAR")

    # Quiz attempts: add xp_gained
    op.execute("ALTER TABLE quiz_attempts ADD COLUMN IF NOT EXISTS xp_gained INTEGER DEFAULT 0")

    # Chapter mastery: add updated_at
    op.execute("ALTER TABLE chapter_mastery ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

    # Chapters: add created_at
    op.execute("ALTER TABLE chapters ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

    # Create notifications table
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('body', sa.String(), nullable=False),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notifications_id', table_name='notifications')
    op.drop_table('notifications')

    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS academic_level")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS major")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS xp_points")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS streak_days")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_active_date")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS subjects_mastered")

    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS question_description")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS hint")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS created_at")

    op.execute("ALTER TABLE quiz_attempts DROP COLUMN IF EXISTS xp_gained")
    op.execute("ALTER TABLE chapter_mastery DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE chapters DROP COLUMN IF EXISTS created_at")
