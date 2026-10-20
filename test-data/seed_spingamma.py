import os
import sys

# Agregar la ruta del backend para importar la BD
BACKEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../spinjob-backend'))
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

from database import SessionLocal
from models import Business, User

def seed_spingamma():
    db = SessionLocal()
    try:
        # Verificar si existe el negocio
        business = db.query(Business).filter(Business.slug == "spingamma").first()
        if business:
            print("⚠️ El negocio 'spingamma' ya existe en la base de datos.")
            return

        print("Creando el negocio base 'spingamma'...")
        
        # Buscar al usuario admin de pruebas para asignarle la propiedad del negocio (opcional)
        owner = db.query(User).filter(User.email == "hellospingamma@gmail.com").first()
        owner_id = owner.id if owner else None

        new_business = Business(
            name="Spingamma Base Test",
            title="Soporte y QA",
            description="Negocio base del sistema usado para anclar pruebas y datos iniciales. Creado automáticamente.",
            slug="spingamma", # IMPORTANTE: El slug que busca el Frontend y el Teardown
            country="Bolivia",
            state="La Paz",
            status="aprobado",
            verified=True,
            is_admin=True,
            orders_enabled=True,
            owner_id=owner_id
        )
        
        db.add(new_business)
        db.commit()
        print("✅ Negocio 'spingamma' creado con éxito en tu base local.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al crear el negocio 'spingamma': {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_spingamma()
