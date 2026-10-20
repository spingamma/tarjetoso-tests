import os
import uuid
import pytest
import datetime
import requests
from playwright.sync_api import Page, expect
from utils.api_testing import APIUtils
from sqlalchemy import create_engine, text

@pytest.fixture
def backend_api():
    return APIUtils()

@pytest.fixture(autouse=True)
def cleanup_social_test_data():
    yield
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    try:
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM business_social_links WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Social Media Business%')"))
            conn.execute(text("DELETE FROM business_subscriptions WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Social Media Business%')"))
            conn.execute(text("DELETE FROM business_specialties WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Social Media Business%')"))
            conn.execute(text("DELETE FROM businesses WHERE name LIKE '%Social Media Business%'"))
            conn.execute(text("DELETE FROM users WHERE email LIKE '%@test.com' OR name LIKE '%Social Test User%'"))
    except Exception as e:
        print(f"Error during teardown: {e}")

def test_social_media_links_are_rendered(page: Page, backend_api: APIUtils):
    api_context = page.context.request
    
    # 1. Crear usuario vendedor
    seller = backend_api.create_e2e_user(api_context, name="Social Test User", is_seller=True)
    
    # 2. Crear negocio usando request directa
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {seller['access_token']}"}
    
    unique_suffix = uuid.uuid4().hex[:4]
    slug = f"social-test-biz-{unique_suffix}"
    
    biz_payload = {
        "name": f"Social Media Business {unique_suffix}",
        "description": "Test social",
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "title": "Redes Sociales Test",
        "slug": slug,
        "phone": "59170000000",
        "ubicacion_url": "https://maps.app.goo.gl/testlocation"
    }
    res = requests.post(f"{base_url}/businesses/", data=biz_payload, headers=headers)
    assert res.status_code in [200, 201], f"Failed to create biz: {res.text}"
    biz = res.json()
    actual_slug = biz.get("slug", slug)
    biz_id = biz["id"]
    
    # 3. Inyectar redes sociales directamente en la tabla business_social_links
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE businesses 
            SET status = 'aprobado'
            WHERE id = :bid
        """), {"bid": biz_id})
        
        # Insertar o actualizar redes sociales en business_social_links
        social_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO business_social_links (id, business_id, facebook, instagram, website)
            VALUES (:sid, :bid, 'https://facebook.com/testbiz', 'https://instagram.com/testbiz', 'https://testbiz.com')
            ON CONFLICT (business_id) DO UPDATE
            SET facebook = EXCLUDED.facebook,
                instagram = EXCLUDED.instagram,
                website = EXCLUDED.website
        """), {"sid": social_id, "bid": biz_id})
        
        exp_date = datetime.datetime.now() + datetime.timedelta(days=365)
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {"bid": biz_id, "exp": exp_date})
        
    # 4. Configurar viewport móvil e ir al perfil público
    page.set_viewport_size({"width": 412, "height": 915})
    front_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(f"{front_url}/perfil/{actual_slug}")
    page.wait_for_load_state("networkidle")
    
    # 5. Verificar controles del rediseño en la cabecera
    expect(page.locator("[data-testid='back-button']")).to_be_visible(timeout=10000)
    expect(page.locator("[data-testid='profile-share-btn']")).to_be_visible()
    expect(page.locator("[data-testid='profile-qr-btn']")).to_be_visible()
    expect(page.locator("[data-testid='profile-bookmark-btn']")).to_be_visible()

    # 6. Verificar que las redes se muestran, incluyendo Ubicación
    expect(page.locator("button[aria-label='Ir a Facebook']")).to_be_visible()
    expect(page.locator("button[aria-label='Ir a Instagram']")).to_be_visible()
    expect(page.locator("button[aria-label='Ir a Sitio Web']")).to_be_visible()
    expect(page.locator("[data-testid='profile-location-btn']")).to_be_visible()
    expect(page.locator("button[aria-label='Ir a Ubicación']")).to_be_visible()

    # 7. Captura de pantalla en el directorio de artefactos
    artifact_screenshot = "/home/jhonatanflorescardenas/.gemini/antigravity-ide/brain/dc6c224b-10a5-4a89-aecd-601f010a4d91/redesign_mobile.png"
    page.screenshot(path=artifact_screenshot, full_page=True)
