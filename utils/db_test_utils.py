import os
import sys

# Agregar la ruta del backend para poder importar los modelos
BACKEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../spinjob-backend'))
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

from database import SessionLocal
from models import Business, Specialty, User

class DBTestUtils:
    """
    Clase de utilidades para realizar consultas de pruebas rápidas a la base de datos local o de testing.
    Útil para diagnosticar inconsistencias de datos o como fixtures en pytest.
    """
    
    @staticmethod
    def get_session():
        return SessionLocal()

    @staticmethod
    def get_business_by_name(name: str):
        """Busca un negocio por coincidencia parcial de nombre."""
        db = DBTestUtils.get_session()
        try:
            return db.query(Business).filter(Business.name.ilike(f'%{name}%')).all()
        finally:
            db.close()

    @staticmethod
    def get_businesses_by_category(category_name: str):
        """Devuelve todos los negocios que tengan una especialidad que coincida con la categoría dada."""
        db = DBTestUtils.get_session()
        try:
            specialties = db.query(Specialty).filter(Specialty.category.ilike(f'%{category_name}%')).all()
            businesses = []
            for spec in specialties:
                businesses.extend(spec.businesses)
            
            # Quitar duplicados si un negocio tiene múltiples subcategorías de la misma categoría
            return list({b.id: b for b in businesses}.values())
        finally:
            db.close()

    @staticmethod
    def get_all_categories():
        """Obtiene una lista de todas las categorías únicas en la DB."""
        db = DBTestUtils.get_session()
        try:
            return [cat[0] for cat in db.query(Specialty.category).distinct().all()]
        finally:
            db.close()

    @staticmethod
    def print_business_details(business):
        """Imprime un resumen de los datos relevantes de un negocio."""
        print(f"--- Datos del Negocio: {business.name} ---")
        print(f"ID: {business.id}")
        print(f"Ubicación: {business.state}, {business.country}")
        print(f"Estatus: {business.status} (Verificado: {business.verified})")
        print(f"Especialidades:")
        for spec in business.specialties:
            print(f"  - {spec.category} / {spec.subcategory}")
        print("-" * 40)
