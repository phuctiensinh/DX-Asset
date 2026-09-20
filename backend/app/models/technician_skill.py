from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import IncidentCategory

class TechnicianSkill(Base):
    __tablename__ = "technician_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(SQLEnum(IncidentCategory, native_enum=False), nullable=False, index=True)
    skill_level = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_technician_skill_user_category"),
    )

    # Relationships
    user = relationship("User", back_populates="skills")

    def __repr__(self):
        return f"<TechnicianSkill user_id={self.user_id} category='{self.category}' level={self.skill_level}>"
