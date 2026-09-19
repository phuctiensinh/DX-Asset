from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import MaintenanceStatus

class Maintenance(Base):
    __tablename__ = "maintenances"

    id = Column(Integer, primary_key=True, index=True)
    maintenance_code = Column(String(50), unique=True, nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    technician_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(MaintenanceStatus, native_enum=False), nullable=False, default=MaintenanceStatus.IN_PROGRESS, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    repair_cost = Column(Numeric(12, 2), default=0.00, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="maintenances")
    incident = relationship("Incident", back_populates="maintenances")
    technician = relationship("User", foreign_keys=[technician_id])

    def __repr__(self):
        return f"<Maintenance id={self.id} code='{self.maintenance_code}' asset_id={self.asset_id} status='{self.status}'>"
