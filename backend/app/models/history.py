from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import AssetActionType

class AssetHistory(Base):
    __tablename__ = "asset_histories"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    action_type = Column(SQLEnum(AssetActionType, native_enum=False), nullable=False, index=True)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="histories")
    performed_by = relationship("User", back_populates="performed_histories", foreign_keys=[performed_by_id])

    def __repr__(self):
        return f"<AssetHistory id={self.id} asset_id={self.asset_id} action='{self.action_type}'>"
