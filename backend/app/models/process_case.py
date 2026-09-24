from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, UniqueConstraint, func

from app.core.database import Base
from app.models.enums import ProcessCaseType


class ProcessCase(Base):
    __tablename__ = "process_cases"

    id = Column(Integer, primary_key=True)
    case_type = Column(SQLEnum(ProcessCaseType, native_enum=False), nullable=False)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=True)
    maintenance_id = Column(Integer, ForeignKey("maintenances.id", ondelete="RESTRICT"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "case_type IN ('INCIDENT', 'MAINTENANCE')",
            name="ck_process_cases_case_type",
        ),
        CheckConstraint(
            "(incident_id IS NOT NULL AND maintenance_id IS NULL) OR "
            "(incident_id IS NULL AND maintenance_id IS NOT NULL)",
            name="ck_process_cases_exactly_one_entity",
        ),
        UniqueConstraint("incident_id", name="uq_process_cases_incident_id"),
        UniqueConstraint("maintenance_id", name="uq_process_cases_maintenance_id"),
    )

    def __repr__(self) -> str:
        return f"<ProcessCase id={self.id} type='{self.case_type}'>"
