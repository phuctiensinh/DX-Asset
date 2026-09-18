from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import AssetStatus

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    brand = Column(String(50), nullable=True)
    model = Column(String(50), nullable=True)
    serial_number = Column(String(100), unique=True, nullable=True, index=True)
    status = Column(SQLEnum(AssetStatus, native_enum=False), nullable=False, default=AssetStatus.IN_STOCK, index=True)
    purchase_date = Column(Date, nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    current_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    location = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    qr_code_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    current_user = relationship("User", back_populates="held_assets", foreign_keys=[current_user_id])
    department = relationship("Department", back_populates="assets", foreign_keys=[department_id])
    assignments = relationship("AssetAssignment", back_populates="asset")
    incidents = relationship("Incident", back_populates="asset")
    histories = relationship("AssetHistory", back_populates="asset")

    def __repr__(self):
        return f"<Asset id={self.id} code='{self.asset_code}' name='{self.name}' status='{self.status}'>"
