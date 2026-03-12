from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False)  # provincia, departamento, ciudad, barrio
    parent_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=True)
    centroid = Column(Geometry("POINT", srid=4326), nullable=True)

    parent = relationship("Location", remote_side=[id], backref="children")
    properties = relationship("Property", back_populates="location")
