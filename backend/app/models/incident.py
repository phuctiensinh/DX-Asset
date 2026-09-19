from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    ticket_code = Column(String(50), unique=True, nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(IncidentCategory, native_enum=False), nullable=False, index=True)
    priority = Column(SQLEnum(IncidentPriority, native_enum=False), nullable=False, index=True)
    status = Column(SQLEnum(IncidentStatus, native_enum=False), nullable=False, default=IncidentStatus.OPEN, index=True)
    assigned_it_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolution_notes = Column(Text, nullable=True)
    repair_cost = Column(Numeric(12, 2), default=0.00, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="incidents")
    reporter = relationship("User", back_populates="reported_incidents", foreign_keys=[reporter_id])
    assigned_it = relationship("User", back_populates="assigned_incidents", foreign_keys=[assigned_it_id])
    maintenances = relationship("Maintenance", back_populates="incident")

    def __repr__(self):
        return f"<Incident id={self.id} code='{self.ticket_code}' priority='{self.priority}' status='{self.status}'>"
