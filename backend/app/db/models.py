import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(Text)
    row_count: Mapped[int | None] = mapped_column(Integer)
    col_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, server_default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    current_agent: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    finished_at: Mapped[datetime | None] = mapped_column()

    dataset: Mapped["Dataset"] = relationship(back_populates="analysis_runs")
    agent_outputs: Mapped[list["AgentOutput"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AgentOutput(Base):
    __tablename__ = "agent_outputs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    run: Mapped["AnalysisRun"] = relationship(back_populates="agent_outputs")


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(Text)
    chart_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    run: Mapped["AnalysisRun"] = relationship(back_populates="insights")
