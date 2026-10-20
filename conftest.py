import pytest
import allure
import os
import sys

# Agregar ruta de utilidades
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def patch_allure_logger():
    """
    Parchea el reporter de Allure en tiempo de ejecución para traducir los nombres
    de los fixtures de 'Set up' y 'Tear down' a nombres legibles, o ignorar los que
    sean puramente internos (ruido).
    """
    try:
        from allure_commons.reporter import AllureReporter
        
        original_start_before = AllureReporter.start_before_fixture
        original_stop_before = AllureReporter.stop_before_fixture
        original_start_after = AllureReporter.start_after_fixture
        original_stop_after = AllureReporter.stop_after_fixture
        
        ignored_prefixes = (
            "_pytest", "pytestconfig", "_verify", "base_url", "browser_name", 
            "browser_type", "request", "browser_context_args", "_artifacts", "_pw", 
            "new_context", "pytestbdd_stepdef", "_skip_sensitive", "pytestbdd_", 
            "worker_id", "page", "browser", "device", "connect_options", "output_path"
        )
        
        translations = {
            "delete_output_dir": "[Setup] Clean previous results",
            "backend_api": "[Setup] Backend API Connection",
            "db_utils": "[Setup] Database Test Utilities",
            "playwright": "[Setup] Initialize UI Engine (Playwright)",
            "launch_browser": "[Setup] Launch Web Browser",
            "context": "[Setup] Isolate Browser Context",
            "shared_data": "[Setup] Shared Test Data Container"
        }
        
        def custom_start_before(self, parent_uuid, uuid, fixture):
            if any(fixture.name.startswith(p) for p in ignored_prefixes) and fixture.name not in translations:
                self._ignored_fixtures = getattr(self, "_ignored_fixtures", set())
                self._ignored_fixtures.add(uuid)
                return
            
            fixture.name = translations.get(fixture.name, fixture.name)
            original_start_before(self, parent_uuid, uuid, fixture)
            
        def custom_stop_before(self, uuid, *args, **kwargs):
            if hasattr(self, "_ignored_fixtures") and uuid in self._ignored_fixtures:
                return
            original_stop_before(self, uuid, *args, **kwargs)
            
        def custom_start_after(self, parent_uuid, uuid, fixture):
            base_name = fixture.name.split("::")[0]
            if any(base_name.startswith(p) for p in ignored_prefixes) and base_name not in translations:
                self._ignored_fixtures = getattr(self, "_ignored_fixtures", set())
                self._ignored_fixtures.add(uuid)
                return
                
            # Ignore pytest internal lambda finalizers that cause 'Unknown' status
            if "::<lambda>" in fixture.name:
                self._ignored_fixtures = getattr(self, "_ignored_fixtures", set())
                self._ignored_fixtures.add(uuid)
                return
                
            trans_name = translations.get(base_name, base_name)
            # Remove any suffix like (1) by not appending the split value
            fixture.name = f"[Teardown] {trans_name.replace('[Setup] ', '')}"
                
            original_start_after(self, parent_uuid, uuid, fixture)
            
        def custom_stop_after(self, uuid, *args, **kwargs):
            if hasattr(self, "_ignored_fixtures") and uuid in self._ignored_fixtures:
                return
            original_stop_after(self, uuid, *args, **kwargs)
            
        AllureReporter.start_before_fixture = custom_start_before
        AllureReporter.stop_before_fixture = custom_stop_before
        AllureReporter.start_after_fixture = custom_start_after
        AllureReporter.stop_after_fixture = custom_stop_after
        
    except ImportError:
        pass

# Ejecutar el parche
patch_allure_logger()

def pytest_bdd_before_scenario(request, feature, scenario):
    allure.dynamic.description(scenario.name)

def pytest_sessionfinish(session, exitstatus):
    """
    Hook global de Teardown al finalizar cualquier sesión de pruebas en tarjetoso-tests.
    Purga entidades de prueba de la base de datos y sus correspondientes carpetas en Cloudinary.
    """
    if getattr(session, "_tarjetoso_teardown_done", False):
        return
    session._tarjetoso_teardown_done = True
    
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    try:
        import requests
        response = requests.delete(f"{api_base}/e2e/cleanup-test-data", timeout=15)
        if response.status_code == 200:
            try:
                from utils.test_tracker import TestTracker
                TestTracker.clear()
            except Exception:
                pass
            return
    except Exception:
        pass

    try:
        from utils.db_teardown import clean_test_data
        clean_test_data()
    except Exception as e:
        print(f"[Conftest Teardown] Error en limpieza directa: {e}")