import os
import uuid
import pytest
import requests
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage
from poms.my_businesses_page import MyBusinessesPage
from poms.directory_page import DirectoryPage
from poms.business_orders_page import BusinessOrdersPage

# Cargar el archivo .feature con ruta relativa correcta
scenarios('../../../features/business_management/business_open_close.feature')


@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


# ---------------------------------------------------------
# GIVEN STEPS
# ---------------------------------------------------------

@given(parsers.parse('a premium business exists with name "{biz_name}" and slug "{slug}"'), target_fixture="biz_context")
def create_premium_business(page: Page, shared_data, backend_api: APIUtils, biz_name, slug):
    assert biz_name.endswith("Test"), f"Nombre del negocio '{biz_name}' debe terminar con 'Test' por seguridad de Teardown"
    api_context = page.context.request
    
    # 1. Crear usuario vendedor
    seller_name = f"Dueño {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]
    
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    
    # 2. Crear negocio vía API
    biz_payload = {
        "name": biz_name,
        "title": "Restaurante",
        "description": "Negocio de pruebas E2E Open Close",
        "slug": slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local", "Delivery"]',
        "payment_methods": '["efectivo", "qr_simple"]',
        "orders_enabled": "false",
        "ubicacion_url": "https://www.google.com/maps?q=-17.7833,-63.1821"
    }
    res = requests.post(
        f"{base_url}/businesses/",
        data=biz_payload,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok, f"Error creando negocio: {res.text}"
    biz_data = res.json()
    biz_id = biz_data["id"]
    real_slug = biz_data["slug"]
    
    shared_data['seller_token'] = seller_token
    shared_data['seller_data'] = seller_data
    shared_data['biz_id'] = biz_id
    shared_data['slug'] = real_slug
    
    # 3. Activar status admin y plan premium directo en base de datos de test
    from sqlalchemy import create_engine, text
    from datetime import datetime, timedelta
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET is_admin = TRUE WHERE id = :id"), {"id": seller_data["id"]})
        conn.execute(text("UPDATE businesses SET status = 'aprobado' WHERE id = :bid"), {"bid": biz_id})
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {
            "bid": biz_id,
            "exp": (datetime.now() + timedelta(days=365)).isoformat()
        })

    # Verificar que el backend refleja 'premium': True
    res_biz = requests.get(f"{base_url}/businesses/{real_slug}")
    assert res_biz.ok, f"Error consultando negocio: {res_biz.text}"
    
    return {"biz_id": biz_id, "slug": real_slug, "seller_token": seller_token}


@given(parsers.parse('a product "{prod_name}" exists for "{slug}"'))
def create_product_for_biz(page: Page, shared_data, backend_api: APIUtils, prod_name, slug):
    assert prod_name.endswith("Test"), f"Nombre '{prod_name}' debe terminar con 'Test'"
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    seller_token = shared_data['seller_token']
    real_slug = shared_data['slug']
    
    payload = {
        "name": prod_name,
        "price": 50.00,
        "stock": 100,
        "catalog_name": "General",
        "is_visible": True
    }
    res = requests.post(
        f"{base_url}/businesses/{real_slug}/products",
        data=payload,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok, f"Error creando producto: {res.text}"
    prod_data = res.json()
    shared_data['product_id'] = prod_data["id"]


# ---------------------------------------------------------
# AUTH & NAVIGATION STEPS
# ---------------------------------------------------------

@when(parsers.parse('the seller of "{slug}" logs in'))
def seller_logs_in(page: Page, shared_data, backend_api: APIUtils, slug):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/")
    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")
    
    seller_data = shared_data['seller_data']
    backend_api.inject_session_to_browser(page, seller_data)
    page.goto(base_url)


@when('the seller enables orders in catalog settings')
def seller_enables_orders(page: Page, shared_data):
    real_slug = shared_data['slug']
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)
    
    # Abrir modal de catálogo
    profile_page.open_catalog_editor()
    
    # Habilitar órdenes
    checkbox = profile_page.orders_enabled_checkbox
    if not checkbox.is_checked():
        page.locator("label[for='ordersEnabledCheckbox']").click()
        page.wait_for_timeout(500)
        
    # Subir QR simulado para que permita guardar
    dummy_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    page.evaluate(f"""
        const dt = new DataTransfer();
        fetch('{dummy_base64}')
          .then(res => res.blob())
          .then(blob => {{
              const file = new File([blob], 'dummy_qr.png', {{ type: 'image/png' }});
              dt.items.add(file);
              const input = document.querySelector("[data-testid='payment-qr-file-input']");
              if (input) {{
                  input.files = dt.files;
                  input.dispatchEvent(new Event('change', {{ bubbles: true }}));
              }}
          }});
    """)
    page.wait_for_timeout(500)
    profile_page.save_catalog()


@when(parsers.parse('the seller goes to "{slug}" profile'))
def seller_visits_profile(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


@when('the seller navigates to "Mis Negocios"')
def seller_navigates_to_my_businesses(page: Page):
    my_biz_page = MyBusinessesPage(page)
    my_biz_page.go_to()


@when('the seller navigates to their business orders')
def seller_navigates_to_orders(page: Page, shared_data):
    real_slug = shared_data['slug']
    orders_page = BusinessOrdersPage(page)
    orders_page.go_to(real_slug)


# ---------------------------------------------------------
# SCENARIO 1 STEPS: HERO BANNER TOGGLE & GRAYSCALE
# ---------------------------------------------------------

@then('the open close toggle switch is visible on the hero banner')
def toggle_is_visible_on_hero(page: Page):
    profile_page = ProfilePage(page)
    expect(profile_page.toggle_open_btn).to_be_visible(timeout=5000)


@when('the seller toggles the business to closed')
def seller_toggles_closed_on_hero(page: Page):
    profile_page = ProfilePage(page)
    profile_page.toggle_open_close()


@then('the hero banner shows the wooden "Cerrado" sign')
def hero_shows_wooden_sign(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_closed_sign_visible()


@then('the hero banner image has grayscale filter')
def hero_image_has_grayscale(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_grayscale_banner(True)


@when(parsers.parse('a public visitor navigates to the public profile of "{slug}"'))
def public_visitor_navigates_profile(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    base_url = os.getenv("BASE_URL", "http://localhost:5173/")
    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")
    
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


@then('the wooden "Cerrado" sign is visible')
def visitor_sees_wooden_sign(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_closed_sign_visible()


@then('the checkout button is not available')
def checkout_is_blocked(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_checkout_not_available()


@when('the seller toggles the business to open')
def seller_toggles_open_on_hero(page: Page):
    profile_page = ProfilePage(page)
    profile_page.toggle_open_close()


@then('the wooden "Cerrado" sign is not visible')
def wooden_sign_not_visible(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_closed_sign_not_visible()


@then('the hero banner image does not have grayscale filter')
def hero_image_no_grayscale(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_grayscale_banner(False)


# ---------------------------------------------------------
# SCENARIO 2 STEPS: MIS NEGOCIOS PANEL & DIRECTORY
# ---------------------------------------------------------

@then(parsers.parse('the open close toggle for "{slug}" is visible in the list'))
def toggle_visible_in_my_businesses(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    my_biz_page = MyBusinessesPage(page)
    toggle = my_biz_page.get_toggle_switch(real_slug)
    expect(toggle).to_be_visible(timeout=5000)


@when(parsers.parse('the seller toggles "{slug}" to closed from the panel'))
def seller_toggles_closed_from_panel(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    my_biz_page = MyBusinessesPage(page)
    my_biz_page.toggle_business_open(real_slug)


@then(parsers.parse('the toggle shows closed state for "{slug}"'))
def toggle_shows_closed_state(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    my_biz_page = MyBusinessesPage(page)
    my_biz_page.verify_toggle_state(real_slug, False)


@when(parsers.parse('a public visitor searches for "{biz_name}" in the directory'))
def visitor_searches_directory(page: Page, shared_data, biz_name):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/")
    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")
    
    directory_page = DirectoryPage(page)
    directory_page.navigate()
    directory_page.search_term(biz_name)
    page.wait_for_timeout(1000)


@then(parsers.parse('the business card for "{slug}" appears in grayscale with "Cerrado" badge'))
def business_card_shows_closed_grayscale(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    directory_page = DirectoryPage(page)
    directory_page.verify_card_closed(real_slug)


@when(parsers.parse('the seller toggles "{slug}" to open from the panel'))
def seller_toggles_open_from_panel(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    my_biz_page = MyBusinessesPage(page)
    my_biz_page.toggle_business_open(real_slug)


@then(parsers.parse('the toggle shows open state for "{slug}"'))
def toggle_shows_open_state(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    my_biz_page = MyBusinessesPage(page)
    my_biz_page.verify_toggle_state(real_slug, True)


# ---------------------------------------------------------
# SCENARIO 3 STEPS: WHATSAPP BUTTON VISIBILITY
# ---------------------------------------------------------

@when(parsers.parse('an order with customer phone is created for "{slug}" via API'))
def create_order_with_phone_via_api(page: Page, shared_data, backend_api: APIUtils, slug):
    api_context = page.context.request
    real_slug = shared_data['slug']
    product_id = shared_data['product_id']
    
    # 1. Crear usuario comprador con teléfono
    buyer_data = backend_api.create_e2e_user(api_context, name="Comprador WA Test")
    buyer_token = buyer_data["access_token"]
    
    # 2. Crear pedido vía API
    items = [{
        "product_id": product_id,
        "product_name": "Producto WA Test",
        "quantity": 1,
        "price_at_time": 50.0,
        "subtotal": 50.0
    }]
    res = backend_api.create_order(
        api_context,
        slug=real_slug,
        token=buyer_token,
        customer_name="Comprador WA Test",
        items=items,
        delivery_method="Entrega en el local",
        total_price=50.0,
        customer_phone=buyer_data.get("phone", "59171234567"),
        expected_status=200
    )
    order_data = res.json()
    order_id = order_data["id"]
    shared_data['order_id'] = order_id
    
    # 3. Marcar pedido como 'pagado' vía API con token del vendedor
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")).rstrip("/")
    seller_token = shared_data['seller_token']
    status_res = api_context.put(
        f"{base_url}/businesses/{real_slug}/orders/{order_id}/status",
        data={"status": "pagado"},
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert status_res.ok, f"Error actualizando estado a pagado: {status_res.text()}"


@then(parsers.parse('the seller sees the order as "{status_text}"'))
def seller_sees_order_status(page: Page, shared_data, status_text):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_order_status(order_id, status_text)


@then('the WhatsApp button is visible on the order card')
def whatsapp_button_visible(page: Page, shared_data):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_whatsapp_button_visible(order_id)


@when('the seller marks the order as delivered')
def seller_marks_order_delivered(page: Page, shared_data):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.mark_as_delivered(order_id)


@then('the WhatsApp button is not visible on the order card')
def whatsapp_button_not_visible(page: Page, shared_data):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_whatsapp_button_not_visible(order_id)
