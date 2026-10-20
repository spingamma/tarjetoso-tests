import os
import sys

# Agregar la ruta del backend para importar la BD
BACKEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../spinjob-backend'))
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

from database import SessionLocal
from models import User

def make_admin(email):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ Error: Usuario con email '{email}' no encontrado en la base de datos.")
            return

        if user.is_admin:
            print(f"⚠️ El usuario '{email}' ya era administrador previamente.")
        else:
            user.is_admin = True
            db.commit()
            print(f"✅ Éxito: El usuario '{email}' ahora es administrador.")
    except Exception as e:
        print(f"❌ Error al actualizar la base de datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python make_admin.py <email_del_usuario>")
        sys.exit(1)
    
    target_email = sys.argv[1]
    make_admin(target_email)
