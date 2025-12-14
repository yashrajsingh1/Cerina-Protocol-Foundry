from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.db import Base


class SessionStatusEnum(str):
    CREATED = "created"
    RUNNING = "running"
    HALTED_FOR_HUMAN = "halted_for_human"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


class ProtocolSession(Base):
    __tablename__ = "protocol_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    intent: Mapped[str] = mapped_column(String(512), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    status: Mapped[str] = mapped_column(String(32), default=SessionStatusEnum.CREATED, nullable=False)

    latest_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_edited_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_protocol: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    safety_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    empathy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    drafts: Mapped[list[DraftVersion]] = relationship(
        "DraftVersion", back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    logs: Mapped[list[AgentLog]] = relationship(
        "AgentLog", back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )


class DraftVersion(Base):
    __tablename__ = "draft_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("protocol_sessions.id", ondelete="CASCADE"))

    version_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    safety_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    empathy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session: Mapped[ProtocolSession] = relationship("ProtocolSession", back_populates="drafts")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("protocol_sessions.id", ondelete="CASCADE"))

    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session: Mapped[ProtocolSession] = relationship("ProtocolSession", back_populates="logs")
