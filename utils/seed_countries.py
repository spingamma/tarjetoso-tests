import os
import sys

# Agregar la ruta del backend para poder importar los modelos
BACKEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../spinjob-backend'))
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_PATH, ".env"))

from database import SessionLocal
from models import Location

BOLIVIA_DEPARTMENTS = [
    "La Paz",
    "Santa Cruz",
    "Cochabamba",
    "Oruro",
    "Potosí",
    "Tarija",
    "Chuquisaca",
    "Beni",
    "Pando"
]

def seed_countries():
    db = SessionLocal()
    try:
        # Verificar si ya existe Bolivia
        existing = db.query(Location).filter(Location.country == "Bolivia").first()
        if existing:
            print("Los países ya han sido poblados previamente. Omitiendo seed.")
            return

        print("Poblando base de datos con departamentos de Bolivia...")
        locations_to_add = []
        for depto in BOLIVIA_DEPARTMENTS:
            loc = Location(country="Bolivia", state=depto)
            locations_to_add.append(loc)
        
        db.add_all(locations_to_add)
        db.commit()
        print(f"Éxito: {len(locations_to_add)} departamentos de Bolivia insertados correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error al poblar la base de datos: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_countries()
