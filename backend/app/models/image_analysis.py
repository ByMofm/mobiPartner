from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class ImageAnalysis(Base):
    __tablename__ = "image_analyses"
    __table_args__ = (UniqueConstraint("property_id", name="uq_image_analysis_property"),)

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    condition_score = Column(Integer, nullable=True)  # 1-100
    condition_label = Column(String(50), nullable=True)  # excelente/bueno/regular/malo
    renovation_state = Column(String(50), nullable=True)  # nuevo/renovado/original/necesita_reforma
    natural_light = Column(Integer, nullable=True)  # 1-5
    cleanliness = Column(Integer, nullable=True)  # 1-5
    raw_analysis = Column(JSONB, nullable=True)
    images_analyzed = Column(Integer, default=0)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    property = relationship("Property", backref="image_analysis")
