from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole, native_enum=False), nullable=False, default=UserRole.EMPLOYEE, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    department = relationship("Department", back_populates="users")
    held_assets = relationship("Asset", back_populates="current_user", foreign_keys="Asset.current_user_id")
    received_assignments = relationship("AssetAssignment", back_populates="assigned_to_user", foreign_keys="AssetAssignment.assigned_to_user_id")
    given_assignments = relationship("AssetAssignment", back_populates="assigned_by_user", foreign_keys="AssetAssignment.assigned_by_user_id")
    reported_incidents = relationship("Incident", back_populates="reporter", foreign_keys="Incident.reporter_id")
    assigned_incidents = relationship("Incident", back_populates="assigned_it", foreign_keys="Incident.assigned_it_id")
    performed_histories = relationship("AssetHistory", back_populates="performed_by", foreign_keys="AssetHistory.performed_by_id")

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
