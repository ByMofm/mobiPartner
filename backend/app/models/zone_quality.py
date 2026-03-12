from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ZoneQuality(Base):
    __tablename__ = "zone_qualities"
    __table_args__ = (UniqueConstraint("location_id", name="uq_zone_quality_location"),)

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    safety_score = Column(Integer, nullable=True)  # 1-100
    quality_score = Column(Integer, nullable=True)  # 1-100
    overall_zone_score = Column(Integer, nullable=True)  # 1-100
    source = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    location = relationship("Location", backref="zone_quality")
