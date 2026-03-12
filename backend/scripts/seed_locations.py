"""Seed Tucumán locations into the database."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.location import Location


TUCUMAN_LOCATIONS = {
    "Tucumán": {
        "level": "provincia",
        "children": {
            "Capital": {
                "level": "departamento",
                "children": {
                    "San Miguel de Tucumán": {
                        "level": "ciudad",
                        "children": {
                            "Centro": {"level": "barrio"},
                            "Barrio Norte": {"level": "barrio"},
                            "Barrio Sur": {"level": "barrio"},
                            "Parque 9 de Julio": {"level": "barrio"},
                            "Barrio Jardín": {"level": "barrio"},
                            "Villa Luján": {"level": "barrio"},
                            "Ciudadela": {"level": "barrio"},
                            "Villa Urquiza": {"level": "barrio"},
                            "Barrio Belgrano": {"level": "barrio"},
                            "Las Talitas": {"level": "barrio"},
                            "Villa Alem": {"level": "barrio"},
                            "Barrio Independencia": {"level": "barrio"},
                            "Barrio Oeste": {"level": "barrio"},
                            "Villa 9 de Julio": {"level": "barrio"},
                            "Marcos Paz": {"level": "barrio"},
                        },
                    },
                },
            },
            "Yerba Buena": {
                "level": "departamento",
                "children": {
                    "Yerba Buena": {
                        "level": "ciudad",
                        "children": {
                            "Centro Yerba Buena": {"level": "barrio"},
                            "Marcos Paz": {"level": "barrio"},
                            "Country Jockey Club": {"level": "barrio"},
                            "Las Praderas": {"level": "barrio"},
                        },
                    },
                },
            },
            "Tafí Viejo": {
                "level": "departamento",
                "children": {
                    "Tafí Viejo": {
                        "level": "ciudad",
                        "children": {
                            "Centro Tafí Viejo": {"level": "barrio"},
                            "Villa Mariano Moreno": {"level": "barrio"},
                        },
                    },
                },
            },
            "Cruz Alta": {
                "level": "departamento",
                "children": {
                    "Banda del Río Salí": {
                        "level": "ciudad",
                        "children": {
                            "Centro Banda": {"level": "barrio"},
                        },
                    },
                    "Alderetes": {
                        "level": "ciudad",
                        "children": {},
                    },
                },
            },
            "Lules": {
                "level": "departamento",
                "children": {
                    "Lules": {
                        "level": "ciudad",
                        "children": {},
                    },
                    "San Pablo": {
                        "level": "ciudad",
                        "children": {},
                    },
                },
            },
            "Famaillá": {
                "level": "departamento",
                "children": {
                    "Famaillá": {"level": "ciudad", "children": {}},
                },
            },
            "Monteros": {
                "level": "departamento",
                "children": {
                    "Monteros": {"level": "ciudad", "children": {}},
                },
            },
            "Concepción": {
                "level": "departamento",
                "children": {
                    "Concepción": {"level": "ciudad", "children": {}},
                },
            },
            "Tafí del Valle": {
                "level": "departamento",
                "children": {
                    "Tafí del Valle": {"level": "ciudad", "children": {}},
                },
            },
            "Aguilares": {
                "level": "departamento",
                "children": {
                    "Aguilares": {"level": "ciudad", "children": {}},
                },
            },
        },
    },
}


def seed_recursive(data: dict, parent_id: int | None, db):
    for name, info in data.items():
        existing = (
            db.query(Location)
            .filter(Location.name == name, Location.level == info["level"], Location.parent_id == parent_id)
            .first()
        )
        if existing:
            print(f"  Skipping existing: {name} ({info['level']})")
            loc = existing
        else:
            loc = Location(name=name, level=info["level"], parent_id=parent_id)
            db.add(loc)
            db.flush()
            print(f"  Created: {name} ({info['level']})")

        children = info.get("children", {})
        if children:
            seed_recursive(children, loc.id, db)


def main():
    db = SessionLocal()
    try:
        print("Seeding Tucumán locations...")
        seed_recursive(TUCUMAN_LOCATIONS, None, db)
        db.commit()
        print("Done!")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
