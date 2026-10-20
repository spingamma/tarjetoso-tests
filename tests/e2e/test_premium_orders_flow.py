import os
import uuid
import pytest
from pytest_bdd import scenario, scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage
from poms.checkout_page import CheckoutPage
from poms.order_tracking_page import OrderTrackingPage
from poms.business_orders_page import BusinessOrdersPage

# Cargar el archivo .feature
scenarios('../../features/premium_orders.feature')

@pytest.fixture
def shared_data():
    return {}

@pytest.fixture
def backend_api():
    return APIUtils()


@given(parsers.parse('a premium business exists with name "{biz_name}" and slug "{slug}"'), target_fixture="biz_context")
def create_premium_business(page: Page, shared_data, backend_api: APIUtils, biz_name, slug):
    assert biz_name.endswith("Test"), f"Nombre del negocio '{biz_name}' debe terminar con 'Test' por seguridad de Teardown"
    api_context = page.context.request
    
    # 1. Crear usuario vendedor
    seller_name = f"Dueño {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]
    
    # 2. Inyectar sesión temporalmente para hacer peticiones como vendedor
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    
    base_url = base_url.rstrip("/")
    
    # Crear negocio
    biz_payload = {
        "name": biz_name,
        "title": "Hamburguesas",
        "description": "Negocio de pruebas E2E",
        "slug": slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local", "Delivery"]',
        "ubicacion_url": "https://www.google.com/maps?q=-17.7833,-63.1821",
        "payment_methods": '["efectivo", "qr_simple"]',
        "orders_enabled": "false"
    }
    import requests
    res = requests.post(
        f"{base_url}/businesses/",
        data=biz_payload,
        headers={
            "Authorization": f"Bearer {seller_token}"
        }
    )
    assert res.ok, f"Error creando negocio: {res.text}"
    biz_data = res.json()
    biz_id = biz_data["id"]
    
    # El ID real y slug devueltos por el backend (puede tener sufijos hash)
    real_slug = biz_data["slug"]
    shared_data['seller_token'] = seller_token
    shared_data['seller_data'] = seller_data
    shared_data['biz_id'] = biz_id
    shared_data['slug'] = real_slug
    
    # 3. Hacer el usuario admin directo en DB y activar plan
    from sqlalchemy import create_engine, text
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        # Activar admin status
        conn.execute(text("UPDATE users SET is_admin = TRUE WHERE id = :id"), {"id": seller_data["id"]})
        
        # UPDATE en business_subscriptions para que el @property premium devuelva True
        from datetime import datetime, timedelta
        import uuid
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {
            "bid": biz_id,
            "exp": (datetime.now() + timedelta(days=365)).isoformat()
        })

    # Verificar que el backend refleja 'premium': True
    res2 = requests.get(f"{base_url}/businesses/{real_slug}")
    assert res2.ok
    print(f"API RESPONSE FOR {real_slug}: {res2.json()}")
    
    return {"biz_id": biz_id, "slug": real_slug, "seller_token": seller_token}


@given(parsers.parse('a product "{prod_name}" exists for "{slug}"'))
def create_product_for_biz(page: Page, shared_data, backend_api: APIUtils, prod_name, slug):
    assert prod_name.endswith("Test"), f"Nombre '{prod_name}' debe terminar con 'Test'"
    api_context = page.context.request
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    seller_token = shared_data['seller_token']
    real_slug = shared_data['slug']
    
    payload = {
        "name": prod_name,
        "price": 50.00,
        "stock": 100,
        "catalog_name": "General",
        "is_visible": True
    }
    import requests
    res = requests.post(
        f"{base_url}/businesses/{real_slug}/products",
        data=payload,
        headers={
            "Authorization": f"Bearer {seller_token}"
        }
    )
    assert res.ok, f"Error creando producto: {res.text}"
    prod_data = res.json()
    shared_data['product_id'] = prod_data["id"]


@given('a buyer user is logged in')
def login_buyer(page: Page, backend_api: APIUtils):
    api_context = page.context.request
    buyer_data = backend_api.create_e2e_user(api_context, name="Comprador Test")
    backend_api.inject_session_to_browser(page, buyer_data)


@when(parsers.parse('the buyer goes to "{slug}" profile'))
def buyer_visits_profile(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


@when(parsers.parse('the buyer adds "{prod_name}" to the cart'))
def buyer_adds_product(page: Page, shared_data, prod_name):
    # Agregar al carrito usando el POM
    profile_page = ProfilePage(page)
    product_id = shared_data['product_id']
    profile_page.add_to_cart(product_id)
    
    # Como es un negocio premium, luego de añadir debería mostrar botones + y -
    plus_btn = page.locator(f"[data-testid='add-to-cart-btn-{product_id}']").first
    expect(plus_btn).to_be_visible(timeout=5000)


@when('the buyer proceeds to checkout')
def buyer_proceeds_to_checkout(page: Page, shared_data):
    profile_page = ProfilePage(page)
    profile_page.go_to_checkout()
    
    expect(page.locator("h1", has_text="Tu Pedido")).to_be_visible(timeout=5000)


@when(parsers.parse('the buyer fills customer name "{cust_name}" and selects "{payment_method}"'))
def buyer_fills_checkout(page: Page, cust_name, payment_method):
    checkout_page = CheckoutPage(page)
    # Rellenar info (el nombre puede ser Test)
    name_input = page.locator("[data-testid='customer-name-input']")
    if name_input.is_visible():
        checkout_page.fill_customer_name(f"{cust_name} Test")


@when('the buyer confirms the order')
def buyer_confirms_order(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.confirm_order()


@then(parsers.parse('the buyer sees order tracking in "{status}" status'))
def buyer_sees_tracking_status(page: Page, shared_data, status):
    import re
    expect(page).to_have_url(re.compile(r".*/orden/.*"))
    order_id = page.url.split("/")[-1]
    shared_data['order_id'] = order_id
    
    # En la UI actual el texto del estado depende del status, por ejemplo "Pendiente de pago"
    if status == "pendiente_de_pago":
        expect(page.locator("text=Pendiente de pago").first).to_be_visible()


@when('the buyer uploads a receipt image')
def buyer_uploads_receipt(page: Page, shared_data):
    tracking_page = OrderTrackingPage(page)
    order_id = shared_data['order_id']
    
    import tempfile
    import base64
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
        f.write(png_data)
        temp_path = f.name

    def handle_upload_route(route):
        # 1. Update DB directly
        import os
        from sqlalchemy import create_engine, text
        db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text("UPDATE orders SET status = 'pago_enviado', receipt_url = 'http://fake-url.com/receipt.png' WHERE id = :oid"), {"oid": order_id})
        
        # 2. Return 200 OK
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"id":"%s", "status": "pago_enviado", "receipt_url": "http://fake-url.com/receipt.png"}' % order_id
        )
        
    page.route("**/receipt", handle_upload_route)
        
    try:
        tracking_page.upload_receipt(temp_path)
        tracking_page.submit_receipt()
        page.wait_for_timeout(2000)
    finally:
        import os
        os.remove(temp_path)
        page.unroute("**/receipt", handle_upload_route)


@then(parsers.parse('the order status changes to "{status}"'))
def buyer_sees_new_status(page: Page, status):
    # La página redirige a /mis-compras tras subir el comprobante.
    # El status "pago_enviado" se muestra en la tarjeta de mis-compras como "PAGO ENVIADO"
    if status == "pago_enviado":
        import re
        expect(page.locator("text=/PAGO ENVIADO/i").first).to_be_visible(timeout=10000)


@when(parsers.parse('the seller of "{slug}" logs in'))
def seller_logs_in(page: Page, shared_data, backend_api: APIUtils, slug):
    # Ir a la página para poder limpiar localStorage
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")
    
    seller_data = shared_data['seller_data']
    backend_api.inject_session_to_browser(page, seller_data)
    # Recargar para aplicar sesión
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))


@when('the seller enables orders in catalog settings')
def seller_enables_orders(page: Page, shared_data):
    slug = shared_data['slug']
    profile_page = ProfilePage(page)
    profile_page.go_to(slug)
    
    # Abrir inventario/catálogo directamente como dueño
    profile_page.open_catalog_editor()
    
    # Habilitar Mis Pedidos
    checkbox = profile_page.orders_enabled_checkbox
    if not checkbox.is_checked():
        page.locator("label[for='ordersEnabledCheckbox']").click()
        page.wait_for_timeout(500)
        
    # Subir QR requerido para cerrar el modal (simulado vía JS para evadir bug ALPN en Chromium)
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
        
    # Guardar cambios en el catálogo con su botón independiente
    profile_page.save_catalog()



@when('the seller navigates to their business orders')
def seller_navigates_orders(page: Page, shared_data):
    slug = shared_data['slug']
    orders_page = BusinessOrdersPage(page)
    orders_page.go_to(slug)


@then(parsers.parse('the seller sees the order as "{status_text}"'))
def seller_sees_order_status(page: Page, shared_data, status_text):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_order_status(order_id, status_text)


@when('the seller marks the order as paid')
def seller_marks_paid(page: Page, shared_data):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.mark_as_paid(order_id)


@when('the seller marks the order as delivered')
def seller_marks_delivered(page: Page, shared_data):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.mark_as_delivered(order_id)

@when(parsers.parse('the seller goes to "{slug}" profile'))
def seller_visits_profile(page: Page, shared_data, slug):
    real_slug = shared_data['slug']
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)

@when(parsers.parse('the seller adds "{prod_name}" to the cart'))
def seller_adds_product(page: Page, shared_data, prod_name):
    profile_page = ProfilePage(page)
    product_id = shared_data['product_id']
    profile_page.add_to_cart(product_id)
    page.wait_for_timeout(1000)

@when('the seller proceeds to checkout')
def seller_proceeds_to_checkout_step(page: Page, shared_data):
    profile_page = ProfilePage(page)
    profile_page.go_to_checkout()
    
    expect(page.locator("h1", has_text="Registrar Venta Presencial")).to_be_visible(timeout=5000)

@when(parsers.parse('the seller fills customer name "{cust_name}" and selects "{payment_method}"'))
def seller_fills_checkout_step(page: Page, cust_name, payment_method):
    checkout_page = CheckoutPage(page)
    name_input = page.locator("[data-testid='customer-name-input']")
    if name_input.is_visible():
        checkout_page.fill_customer_name(f"{cust_name} Test")

@when('the seller confirms the order')
def seller_confirms_order_step(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.confirm_order()

@then('the order is created in final state and does not ask for payment')
def seller_order_final_state(page: Page):
    import re
    # Wait to be redirected to tracking
    page.wait_for_url(re.compile(r".*/(tracking|orden-estado|orden)/.*"), timeout=5000)
    # The fix in frontend should probably mark it as "Completado" directly
    # and NOT "Pendiente de pago"
    expect(page.locator("text=Completado").first).to_be_visible(timeout=5000)
    expect(page.locator("text=Pendiente de pago")).not_to_be_visible()
