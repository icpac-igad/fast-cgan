from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from fastcgan.db.database import Base
from fastcgan.db.enums import OutcomeStatus
from fastcgan.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class HeaderNavigation(TimestampMixin, UUIDMixin, SoftDeleteMixin, Base):
    __tablename__ = "header_navigation"
    __table_args__ = {"schema": "web"}
    name: Mapped[str] = mapped_column(String(length=100), unique=True)
    url_path: Mapped[str] = mapped_column(String(length=250), unique=True)
    order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, unique=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)


class ForecastProduct(TimestampMixin, UUIDMixin, SoftDeleteMixin, Base):
    __tablename__ = "forecast_product"
    __table_args__ = {"schema": "web"}
    title: Mapped[str] = mapped_column(String(length=100), unique=True)
    text: Mapped[str] = mapped_column(String(length=500), nullable=False)
    icon: Mapped[str] = mapped_column(String(length=100), nullable=False)
    url_path: Mapped[str] = mapped_column(String(length=250), unique=True)
    order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, unique=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)


class UsefulResource(TimestampMixin, UUIDMixin, SoftDeleteMixin, Base):
    __tablename__ = "useful_resource"
    __table_args__ = {"schema": "web"}
    title: Mapped[str] = mapped_column(String(length=100), unique=True)
    text: Mapped[str] = mapped_column(String(length=500), nullable=False)
    icon: Mapped[str] = mapped_column(String(length=100), nullable=False)
    bg_color: Mapped[str] = mapped_column(String(length=100), nullable=False)
    link: Mapped[str] = mapped_column(String(length=500), nullable=False)
    order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, unique=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)


class OutcomeTimeline(TimestampMixin, UUIDMixin, SoftDeleteMixin, Base):
    __tablename__ = "outcome_timeline"
    __table_args__ = {"schema": "web"}
    task_title: Mapped[str] = mapped_column(String(length=100), unique=True)
    outcome_title: Mapped[str] = mapped_column(String(length=100), unique=True)
    task_text: Mapped[str] = mapped_column(String(length=1000), nullable=False)
    outcome_text: Mapped[str] = mapped_column(String(length=1000), nullable=False)
    task_image: Mapped[str] = mapped_column(String(length=500))
    outcome_image: Mapped[str] = mapped_column(String(length=500))
    bg_color: Mapped[str] = mapped_column(String(length=100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    final_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed: Mapped[OutcomeStatus] = mapped_column(Enum(OutcomeStatus))
    order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, unique=True)


class FooterNavigation(TimestampMixin, UUIDMixin, SoftDeleteMixin, Base):
    __tablename__ = "footer_navigation"
    __table_args__ = {"schema": "web"}
    name: Mapped[str] = mapped_column(String(length=100), unique=True)
    url_path: Mapped[str] = mapped_column(String(length=250), unique=True)
    order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, unique=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectPartner(TimestampMixin, UUIDMixin, SoftDeleteMixin, Base):
    __tablename__ = "project_partner"
    __table_args__ = {"schema": "web"}
    name: Mapped[str] = mapped_column(String(length=100), unique=True)
    logo_url: Mapped[str] = mapped_column(String(length=250), nullable=False)
    link: Mapped[str] = mapped_column(String(length=250), unique=True)
    order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, unique=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)


class TokenBlacklist(TimestampMixin, Base):
    __tablename__ = "access_token_blacklist"
    __table_args__ = {"schema": "web"}
    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
