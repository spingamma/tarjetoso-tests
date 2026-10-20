import os
import pytest
import allure_commons
import logging
from uuid import uuid4
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env variables proactively before any tests run
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from utils.screenshot_utils import capture_screenshot_on_failure, capture_success_assert_screenshot


# =============================================================================
# Allure BDD Step Injection — Cada paso Gherkin aparece como sub-step en Allure
# =============================================================================

@pytest.hookimpl
def pytest_bdd_before_step(request, feature, scenario, step, step_func):
    """
    Inyecta dinámicamente los pasos del archivo .feature (Gherkin) en el reporte de Allure
    antes de que se ejecuten.
    """
    step_uuid = uuid4()
    step.allure_uuid = str(step_uuid)
    step_name = f"{step.keyword} {step.name}"
    
    allure_commons.plugin_manager.hook.start_step(
        uuid=step.allure_uuid, 
        title=step_name, 
        params={}
    )

@pytest.hookimpl
def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    """
    Cierra el paso inyectado dinámicamente en Allure como exitoso (passed)
    y captura screenshot si es un paso 'Then'.
    """
    if hasattr(step, "allure_uuid"):
        allure_commons.plugin_manager.hook.stop_step(
            uuid=step.allure_uuid,
            exc_type=None,
            exc_val=None,
            exc_tb=None
        )

    if step.keyword.lower() == "then":
        try:
            if "page" in request.fixturenames:
                page = request.getfixturevalue("page")
                if page and not page.is_closed() and page.url != "about:blank":
                    capture_success_assert_screenshot(page, step.name)
        except Exception as e:
            print(f"No se pudo capturar el assert {step.name}: {e}")

@pytest.hookimpl
def pytest_bdd_step_error(request, feature, scenario, step, step_func, step_func_args, exception):
    """
    Cierra el paso en Allure marcándolo como fallido y adjunta un screenshot 
    directamente en memoria si se trata de un test de UI.
    """
    if hasattr(step, "allure_uuid"):
        import sys
        import allure
        exc_type, exc_val, exc_tb = sys.exc_info()
        
        # --- NUEVA LÓGICA CERO RIESGOS ---
        if "page" in request.fixturenames:
            try:
                page = request.getfixturevalue("page")
                if page and not page.is_closed() and page.url != "about:blank":
                    screenshot_bytes = page.screenshot(full_page=True)
                    allure.attach(
                        screenshot_bytes,
                        name=f"Screenshot de Fallo: {step.name}",
                        attachment_type=allure.attachment_type.PNG
                    )
            except Exception as e:
                # Fallback silencioso absoluto
                pass
        # ---------------------------------

        allure_commons.plugin_manager.hook.stop_step(
            uuid=step.allure_uuid,
            exc_type=exc_type,
            exc_val=exc_val,
            exc_tb=exc_tb
        )

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Ejecuta todos los hooks de makereport y luego intercepta el fallo para la captura."""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        try:
            if "page" in item.fixturenames:
                page = item.funcargs.get("page")
                if page and not page.is_closed() and page.url != "about:blank":
                    capture_screenshot_on_failure(page, item.name)
        except Exception as e:
            print(f"Error capturando fallo en {item.name}: {e}")


# =============================================================================
# Global Teardown — Purga de datos de test al finalizar la sesión
# =============================================================================

def pytest_sessionfinish(session, exitstatus):
    """
    Global Teardown hook to purge all 'Test' entities created during E2E runs.
    Uses the backend API (not direct SQL) to clean up test data and Cloudinary images.
    """
    if getattr(session, "_tarjetoso_teardown_done", False):
        return
    session._tarjetoso_teardown_done = True

    api_base = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    logger.info("Executing global E2E Teardown...")
    
    try:
        import requests
        
        # 1. Intentar llamar al endpoint de cleanup del backend (que limpia DB y Cloudinary)
        response = requests.delete(f"{api_base}/e2e/cleanup-test-data", timeout=15)
        if response.status_code == 200:
            logger.info(f"Global teardown completed via backend API: {response.json()}")
            return
        else:
            logger.warning(f"Backend teardown returned status {response.status_code}: {response.text}. Usando fallback directo...")
    except Exception as e:
        logger.warning(f"Error conectando con endpoint de teardown: {e}. Usando fallback directo...")
        
    # 2. Fallback directo a base de datos y Cloudinary
    try:
        from utils.db_teardown import clean_test_data
        clean_test_data()
        logger.info("Global teardown completado mediante fallback directo (DB + Cloudinary).")
    except Exception as fallback_err:
        logger.error(f"Error en fallback de teardown: {fallback_err}")

