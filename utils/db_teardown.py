import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy import create_engine, text

# Asegurar importación de utils tanto como módulo como script directo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from utils.test_tracker import TestTracker
except ImportError:
    from test_tracker import TestTracker

def _get_cloudinary_auth():
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    
    if not (cloud_name and api_key and api_secret):
        from dotenv import dotenv_values
        backend_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../spinjob-backend/.env.test"))
        if os.path.exists(backend_env_path):
            b_env = dotenv_values(backend_env_path)
            cloud_name = cloud_name or b_env.get("CLOUDINARY_CLOUD_NAME")
            api_key = api_key or b_env.get("CLOUDINARY_API_KEY")
            api_secret = api_secret or b_env.get("CLOUDINARY_API_SECRET")
            
    if not (cloud_name and api_key and api_secret):
        return None, None
        
    return cloud_name, HTTPBasicAuth(api_key, api_secret)

def _delete_cloudinary_folder_tree(cloud_name: str, auth: HTTPBasicAuth, folder: str):
    """Elimina recursivamente recursos, subcarpetas y carpeta raíz en Cloudinary."""
    if not folder.startswith("business_"):
        print(f"[Teardown] Omitiendo carpeta no válida: {folder}")
        return

    try:
        # 1. Eliminar recursos multimedia
        requests.delete(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/resources/image/upload",
            params={"prefix": f"{folder}/"},
            auth=auth,
            timeout=10
        )
        # 2. Descubrir y eliminar subcarpetas
        sub_res = requests.get(f"https://api.cloudinary.com/v1_1/{cloud_name}/folders/{folder}", auth=auth, timeout=10)
        if sub_res.ok:
            for subf in sub_res.json().get("folders", []):
                sub_path = subf.get("path")
                if sub_path:
                    requests.delete(f"https://api.cloudinary.com/v1_1/{cloud_name}/folders/{sub_path}", auth=auth, timeout=10)
        # 3. Eliminar la carpeta raíz
        requests.delete(f"https://api.cloudinary.com/v1_1/{cloud_name}/folders/{folder}", auth=auth, timeout=10)
        print(f"[Teardown] Cloudinary: limpiada carpeta de prueba {folder}")
    except Exception as ex:
        print(f"[Teardown] Cloudinary advertencia para {folder}: {ex}")

def cleanup_cloudinary_business_folders(business_ids: list):
    """Elimina las carpetas de Cloudinary SOLO para los IDs de negocios de prueba confirmados."""
    if not business_ids:
        return
    
    cloud_name, auth = _get_cloudinary_auth()
    if not (cloud_name and auth):
        print("[Teardown] Credenciales de Cloudinary no encontradas. Omitiendo limpieza de imágenes.")
        return
        
    for bid in business_ids:
        folder = f"business_{bid}"
        _delete_cloudinary_folder_tree(cloud_name, auth, folder)


def clean_test_data():
    """
    Limpieza quirúrgica y segura de datos de prueba:
    1. Si los tests registraron entidades en tiempo de ejecución (TestTracker), se limpian preferentemente esas.
    2. Como respaldo, solo se eliminan entidades que cumplen con la firma inequívoca de testing:
       - Negocios cuyo nombre termina estrictamente en 'Test' (excluyendo 'spingamma').
       - Usuarios cuyo nombre termina en 'Test' y su email pertenece al dominio de testing (@e2e.com / @test.com).
    3. NUNCA se tocan negocios reales ni se realizan barridos ciegos en Cloudinary.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[Teardown] DATABASE_URL no encontrada en .env. Omitiendo limpieza.")
        return

    # Salvaguarda estricta: Jamás correr teardown sobre base de datos Neon de producción
    if "neon.tech" in database_url or "pooler" in database_url:
        raise RuntimeError("[Teardown] BLOQUEADO: DATABASE_URL apunta a Neon/producción. No se permite teardown en producción.")

    tracked = TestTracker.get_tracked_entities()
    tracked_biz_ids = tracked.get("business_ids", [])
    tracked_user_ids = tracked.get("user_ids", [])

    print(f"[Teardown] Iniciando limpieza segura (Entidades rastreadas en sesión: {len(tracked_biz_ids)} negocios, {len(tracked_user_ids)} usuarios)...")
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        try:
            # 1. Identificar Negocios de Prueba (Firma: name LIKE '%Test' y no spingamma)
            if tracked_biz_ids:
                # Si tenemos IDs rastreados, verificar que efectivamente sean de prueba en la DB
                result = conn.execute(
                    text("SELECT id FROM businesses WHERE id IN :bids AND name LIKE '%Test' AND slug != 'spingamma'"),
                    {"bids": tuple(tracked_biz_ids)}
                )
                business_ids = [row[0] for row in result.fetchall()]
            else:
                result = conn.execute(text("SELECT id FROM businesses WHERE name LIKE '%Test' AND slug != 'spingamma'"))
                business_ids = [row[0] for row in result.fetchall()]
            
            if business_ids:
                print(f"[Teardown] Encontrados {len(business_ids)} negocios con firma de prueba. Eliminando...")
                
                # Limpiar imágenes en Cloudinary SOLO para estos negocios de prueba
                cleanup_cloudinary_business_folders(business_ids)
                
                bids_tuple = tuple(business_ids)
                
                # Order Items y Orders
                conn.execute(
                    text("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE business_id IN :bids)"),
                    {"bids": bids_tuple}
                )
                conn.execute(
                    text("DELETE FROM orders WHERE business_id IN :bids"),
                    {"bids": bids_tuple}
                )
                
                # Tablas dependientes del negocio
                for table in ['interactions', 'resenas', 'products', 'saved_cards', 'business_subscriptions', 'business_staff']:
                    conn.execute(
                        text(f"DELETE FROM {table} WHERE business_id IN :bids"), 
                        {"bids": bids_tuple}
                    )
                
                # Especialidades
                conn.execute(
                    text("DELETE FROM business_specialties WHERE business_id IN :bids"), 
                    {"bids": bids_tuple}
                )
                
                # Borrar los negocios
                conn.execute(
                    text("DELETE FROM businesses WHERE id IN :bids"), 
                    {"bids": bids_tuple}
                )
                print(f"[Teardown] {len(business_ids)} negocios de prueba eliminados exitosamente.")

            # 2. Identificar Usuarios de Prueba (Firma: name LIKE '%Test' y email de testing)
            if tracked_user_ids:
                result = conn.execute(
                    text("SELECT id FROM users WHERE id IN :uids AND (name LIKE '%Test' OR email LIKE '%@e2e.com' OR email LIKE '%@test.com') AND email != 'hellospingamma@gmail.com'"),
                    {"uids": tuple(tracked_user_ids)}
                )
                user_ids = [row[0] for row in result.fetchall()]
            else:
                result = conn.execute(text(
                    "SELECT id FROM users WHERE (name LIKE '%Test' OR name IN ('Api Seller', 'Api User')) AND (email LIKE '%@e2e.com' OR email LIKE '%@test.com') AND email != 'hellospingamma@gmail.com'"
                ))
                user_ids = [row[0] for row in result.fetchall()]
            
            if user_ids:
                print(f"[Teardown] Encontrados {len(user_ids)} usuarios con firma de prueba. Eliminando dependencias...")
                uids_tuple = tuple(user_ids)
                
                # Negocios adicionales de prueba asociados a estos usuarios
                result = conn.execute(
                    text("SELECT id FROM businesses WHERE (owner_id IN :uids OR referred_by IN :uids) AND slug != 'spingamma' AND name LIKE '%Test'"),
                    {"uids": uids_tuple}
                )
                extra_business_ids = [row[0] for row in result.fetchall()]
                
                if extra_business_ids:
                    print(f"[Teardown] Eliminando {len(extra_business_ids)} negocios de prueba adicionales asociados...")
                    cleanup_cloudinary_business_folders(extra_business_ids)
                    extra_bids_tuple = tuple(extra_business_ids)
                    for table in ['interactions', 'resenas', 'products', 'saved_cards', 'business_subscriptions', 'business_staff']:
                        conn.execute(text(f"DELETE FROM {table} WHERE business_id IN :bids"), {"bids": extra_bids_tuple})
                    conn.execute(text("DELETE FROM business_specialties WHERE business_id IN :bids"), {"bids": extra_bids_tuple})
                    conn.execute(text("DELETE FROM businesses WHERE id IN :bids"), {"bids": extra_bids_tuple})

                # Pedidos del usuario
                conn.execute(
                    text("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id IN :uids)"),
                    {"uids": uids_tuple}
                )
                conn.execute(
                    text("DELETE FROM orders WHERE user_id IN :uids"),
                    {"uids": uids_tuple}
                )

                # Tablas dependientes de usuario
                for table in ['interactions', 'resenas', 'saved_cards', 'business_staff']:
                    conn.execute(
                        text(f"DELETE FROM {table} WHERE user_id IN :uids"), 
                        {"uids": uids_tuple}
                    )
                
                # Borrar usuarios
                conn.execute(
                    text("DELETE FROM users WHERE id IN :uids"), 
                    {"uids": uids_tuple}
                )
                print(f"[Teardown] {len(user_ids)} usuarios de prueba eliminados.")

            conn.commit()
            TestTracker.clear()
            print("[Teardown] Limpieza completada con éxito.")
            
        except Exception as e:
            conn.rollback()
            print(f"[Teardown] Error durante la limpieza: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    clean_test_data()
