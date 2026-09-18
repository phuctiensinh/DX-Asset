from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Enum as SQLEnum, Index, func, text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import AssignmentStatus

class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    return_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(AssignmentStatus, native_enum=False), nullable=False, default=AssignmentStatus.ACTIVE, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="assignments")
    assigned_to_user = relationship("User", back_populates="received_assignments", foreign_keys=[assigned_to_user_id])
    assigned_by_user = relationship("User", back_populates="given_assignments", foreign_keys=[assigned_by_user_id])

    __table_args__ = (
        Index(
            "uq_active_asset_assignment",
            "asset_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'")
        ),
    )

    def __repr__(self):
        return f"<AssetAssignment id={self.id} asset_id={self.asset_id} to_user={self.assigned_to_user_id} status='{self.status}'>"
