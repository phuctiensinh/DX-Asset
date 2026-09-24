from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Enum as SQLEnum,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import ProcessEventSource, ProcessEventTimestampQuality, ProcessEventType


class ProcessEvent(Base):
    __tablename__ = "process_events"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("process_cases.id", ondelete="RESTRICT"), nullable=False)
    maintenance_id = Column(Integer, ForeignKey("maintenances.id", ondelete="RESTRICT"), nullable=True)
    event_type = Column(SQLEnum(ProcessEventType, native_enum=False), nullable=False)
    from_status = Column(String(40), nullable=True)
    to_status = Column(String(40), nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    case_sequence = Column(Integer, nullable=False)
    source = Column(SQLEnum(ProcessEventSource, native_enum=False), nullable=False)
    timestamp_quality = Column(SQLEnum(ProcessEventTimestampQuality, native_enum=False), nullable=False)
    source_event_key = Column(String(200), nullable=True, unique=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    process_case = relationship("ProcessCase")

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('INCIDENT_CREATED', 'INCIDENT_STATUS_CHANGED', 'TECHNICIAN_ASSIGNED', "
            "'MAINTENANCE_CREATED', 'MAINTENANCE_STATUS_CHANGED')",
            name="ck_process_events_event_type",
        ),
        CheckConstraint("source IN ('LIVE', 'BACKFILL')", name="ck_process_events_source"),
        CheckConstraint(
            "timestamp_quality IN ('ACTION_TIME', 'LEGACY_FIELD', 'AMBIGUOUS')",
            name="ck_process_events_timestamp_quality",
        ),
        CheckConstraint(
            "(event_type = 'INCIDENT_CREATED' AND from_status IS NULL AND to_status IS NOT NULL) OR "
            "(event_type IN ('INCIDENT_STATUS_CHANGED', 'MAINTENANCE_STATUS_CHANGED') "
            "AND from_status IS NOT NULL AND to_status IS NOT NULL) OR "
            "(event_type NOT IN ('INCIDENT_CREATED', 'INCIDENT_STATUS_CHANGED', 'MAINTENANCE_STATUS_CHANGED') "
            "AND from_status IS NULL AND to_status IS NULL)",
            name="ck_process_events_status_fields",
        ),
        CheckConstraint("case_sequence > 0", name="ck_process_events_positive_sequence"),
        UniqueConstraint("case_id", "case_sequence", name="uq_process_events_case_sequence"),
        Index("ix_process_events_case_time_sequence", "case_id", "occurred_at", "case_sequence"),
        Index("ix_process_events_time_case", "occurred_at", "case_id"),
        Index("ix_process_events_type_time", "event_type", "occurred_at"),
    )

    def __repr__(self) -> str:
        return f"<ProcessEvent id={self.id} case_id={self.case_id} type='{self.event_type}'>"
