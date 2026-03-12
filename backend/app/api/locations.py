from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.location import Location
from app.schemas.property import LocationSchema

router = APIRouter()


def build_tree(locations: list[Location], parent_id: int | None = None) -> list[LocationSchema]:
    result = []
    for loc in locations:
        if loc.parent_id == parent_id:
            children = build_tree(locations, loc.id)
            result.append(
                LocationSchema(
                    id=loc.id,
                    name=loc.name,
                    level=loc.level,
                    parent_id=loc.parent_id,
                    children=children,
                )
            )
    return result


@router.get("", response_model=list[LocationSchema])
def list_locations(db: Session = Depends(get_db)):
    locations = db.query(Location).all()
    return build_tree(locations)
