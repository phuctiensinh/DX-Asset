from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class IncidentAttachment(Base):
    __tablename__ = "incident_attachments"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    incident = relationship("Incident", back_populates="attachments")
    uploaded_by = relationship("User", back_populates="uploaded_attachments")

    @property
    def file_url(self) -> str:
        return f"/api/v1/incidents/{self.incident_id}/attachments/{self.id}/file"

    def __repr__(self):
        return f"<IncidentAttachment id={self.id} incident_id={self.incident_id} file_name='{self.file_name}'>"
