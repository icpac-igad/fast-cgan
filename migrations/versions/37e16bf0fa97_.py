"""empty message

Revision ID: 37e16bf0fa97
Revises:
Create Date: 2024-11-23 19:41:59.678286

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "37e16bf0fa97"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "access_token_blacklist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        schema="web",
    )
    op.create_index(
        op.f("ix_web_access_token_blacklist_token"),
        "access_token_blacklist",
        ["token"],
        unique=True,
        schema="web",
    )
    op.create_table(
        "footer_navigation",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url_path", sa.String(length=250), nullable=False),
        sa.Column("order", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=True,
        ),
        sa.Column(
            "uuid",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("url_path"),
        schema="web",
    )
    op.create_table(
        "forecast_product",
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=False),
        sa.Column("url_path", sa.String(length=250), nullable=False),
        sa.Column("order", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=True,
        ),
        sa.Column(
            "uuid",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("title"),
        sa.UniqueConstraint("url_path"),
        schema="web",
    )
    op.create_table(
        "header_navigation",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url_path", sa.String(length=250), nullable=False),
        sa.Column("order", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=True,
        ),
        sa.Column(
            "uuid",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("url_path"),
        schema="web",
    )
    op.create_table(
        "outcome_timeline",
        sa.Column("task_title", sa.String(length=100), nullable=False),
        sa.Column("outcome_title", sa.String(length=100), nullable=False),
        sa.Column("task_text", sa.String(length=1000), nullable=False),
        sa.Column("outcome_text", sa.String(length=1000), nullable=False),
        sa.Column("task_image", sa.String(length=500), nullable=False),
        sa.Column("outcome_image", sa.String(length=500), nullable=False),
        sa.Column("bg_color", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("final_date", sa.Date(), nullable=False),
        sa.Column(
            "completed",
            sa.Enum(
                "planned",
                "started",
                "progress",
                "final",
                "complete",
                "dropped",
                name="outcomestatus",
            ),
            nullable=False,
        ),
        sa.Column("order", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=True,
        ),
        sa.Column(
            "uuid",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("outcome_title"),
        sa.UniqueConstraint("task_title"),
        schema="web",
    )
    op.create_table(
        "project_partner",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("logo_url", sa.String(length=250), nullable=False),
        sa.Column("link", sa.String(length=250), nullable=False),
        sa.Column("order", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=True,
        ),
        sa.Column(
            "uuid",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("link"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("order"),
        schema="web",
    )
    op.create_table(
        "useful_resource",
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=False),
        sa.Column("bg_color", sa.String(length=100), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=False),
        sa.Column("order", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("current_timestamp(0)"),
            nullable=True,
        ),
        sa.Column(
            "uuid",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("title"),
        schema="web",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("useful_resource", schema="web")
    op.drop_table("project_partner", schema="web")
    op.drop_table("outcome_timeline", schema="web")
    op.drop_table("header_navigation", schema="web")
    op.drop_table("forecast_product", schema="web")
    op.drop_table("footer_navigation", schema="web")
    op.drop_index(
        op.f("ix_web_access_token_blacklist_token"),
        table_name="access_token_blacklist",
        schema="web",
    )
    op.drop_table("access_token_blacklist", schema="web")
    # ### end Alembic commands ###
