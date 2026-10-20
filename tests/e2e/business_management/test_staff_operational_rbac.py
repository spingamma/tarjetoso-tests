import os
import uuid
import time
import subprocess
import requests
import base64
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage
from poms.my_businesses_page import MyBusinessesPage
from poms.business_orders_page import BusinessOrdersPage
from poms.order_tracking_page import OrderTrackingPage

# Load scenarios from feature file
scenarios('../../../features/business_management/staff_operational_rbac.feature')


@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


def _get_db_engine():
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


def _insert_mock_push_subscription(user_id: str):
    """Inserta una suscripción push mock en la base de datos para el usuario."""
    endpoint = f"https://fcm.googleapis.com/fcm/send/fake-staff-ep-{uuid.uuid4().hex}"
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO push_subscriptions (id, user_id, endpoint, p256dh, auth)
            VALUES (:id, :uid, :ep, 'fake-p256dh-key', 'fake-auth-key')
            ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid.uuid4()),
            "uid": user_id,
            "ep": endpoint
        })
    return endpoint


def _get_docker_logs():
    res = subprocess.run(["docker", "logs", "spinjob_backend", "--tail", "300"], capture_output=True, text=True)
    return (res.stdout or "") + "\n" + (res.stderr or "")


# ---------------------------------------------------------------------------
# GIVEN STEPS
# ---------------------------------------------------------------------------

@given(parsers.parse('a premium business "{biz_name}" with owner "{owner_name}" and slug "{slug}"'), target_fixture="biz_setup")
def setup_premium_business(page: Page, shared_data, backend_api: APIUtils, biz_name, owner_name, slug):
    assert biz_name.endswith("Test"), f"Nombre del negocio '{biz_name}' debe terminar con 'Test'"
    api_context = page.context.request
    unique_suffix = uuid.uuid4().hex[:4]

    # 1. Crear Dueño
    owner_data = backend_api.create_e2e_user(api_context, name=f"{owner_name} {unique_suffix}", is_seller=True)
    owner_token = owner_data["access_token"]
    owner_id = owner_data["user"]["id"] if "user" in owner_data else owner_data.get("id")

    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    # 2. Crear Negocio (Nombre <= 30 caracteres)
    final_biz_name = f"{biz_name} {unique_suffix}"[:30]
    biz_payload = {
        "name": final_biz_name,
        "title": "Restaurante Staff",
        "description": "Negocio de pruebas E2E Staff RBAC",
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": owner_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "payment_methods": '["efectivo", "qr_simple"]',
        "orders_enabled": "true"
    }
    res = requests.post(
        f"{base_url}/businesses/",
        data=biz_payload,
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res.ok, f"Error creando negocio: {res.text}"
    biz_data = res.json()
    biz_id = biz_data["id"]
    real_slug = biz_data["slug"]

    # 3. Crear Producto de prueba
    prod_res = requests.post(
        f"{base_url}/businesses/{real_slug}/products",
        data={"name": f"Menu {unique_suffix} Test", "price": 50.0, "stock": 100, "catalog_name": "General", "is_visible": True},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert prod_res.ok, f"Error creando producto: {prod_res.text}"
    prod_data = prod_res.json()

    # 4. Activar status aprobado y plan premium en DB
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET is_admin = TRUE WHERE id = :id"), {"id": owner_id})
        conn.execute(text("UPDATE businesses SET status = 'aprobado' WHERE id = :bid"), {"bid": biz_id})
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {
            "bid": biz_id,
            "exp": (datetime.now() + timedelta(days=365)).isoformat()
        })

    shared_data['owner_name'] = owner_name
    shared_data['owner_data'] = owner_data
    shared_data['owner_token'] = owner_token
    shared_data['owner_id'] = owner_id
    shared_data['biz_id'] = biz_id
    shared_data['slug'] = real_slug
    shared_data['biz_name'] = final_biz_name
    shared_data['prod_id'] = prod_data["id"]

    return {"biz_id": biz_id, "slug": real_slug, "owner_token": owner_token}


@given(parsers.parse('a registered collaborator "{collab_name}" is assigned to the business with default permissions'))
def assign_collaborator_to_business(page: Page, shared_data, backend_api: APIUtils, collab_name):
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    owner_token = shared_data['owner_token']
    unique_suffix = uuid.uuid4().hex[:4]

    collab_display_name = f"{collab_name} {unique_suffix}"
    collab_data = backend_api.create_e2e_user(api_context, name=collab_display_name)
    collab_id = collab_data["user"]["id"] if "user" in collab_data else collab_data.get("id")
    collab_token = collab_data["access_token"]

    # Agregar colaborador vía API
    res = requests.post(
        f"{base_url}/businesses/{slug}/staff",
        json={"query": collab_data["email"]},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res.ok, f"Error vinculando colaborador: {res.text}"
    staff_record = res.json()

    shared_data['collab_name'] = collab_name
    shared_data['collab_display_name'] = collab_display_name
    shared_data['collab_data'] = collab_data
    shared_data['collab_id'] = collab_id
    shared_data['collab_token'] = collab_token
    shared_data['staff_id'] = staff_record["id"]


# ---------------------------------------------------------------------------
# SCENARIO 1: MY BUSINESSES & OPEN-CLOSE TOGGLE
# ---------------------------------------------------------------------------

@when('the collaborator logs in and navigates to the my businesses page')
def collaborator_visits_my_businesses(page: Page, shared_data, backend_api: APIUtils):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/").rstrip("/")
    collab_data = shared_data['collab_data']

    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")

    backend_api.inject_session_to_browser(page, collab_data)
    my_biz = MyBusinessesPage(page)
    my_biz.go_to()


@then('the business card displays the "Colaborador" badge')
def verify_collab_badge(page: Page):
    my_biz = MyBusinessesPage(page)
    my_biz.verify_collaborator_badge_visible()


@then('the public card and open-close toggle buttons are visible')
def verify_public_card_and_toggle_visible(page: Page, shared_data):
    slug = shared_data['slug']
    my_biz = MyBusinessesPage(page)
    toggle = my_biz.get_toggle_switch(slug)
    expect(toggle).to_be_visible(timeout=5000)
    public_card_link = page.locator(f"a[href*='/perfil/{slug}']").first
    expect(public_card_link).to_be_visible(timeout=5000)


@then('the metrics and delete request buttons are not visible for the collaborator')
def verify_restricted_buttons_hidden(page: Page):
    my_biz = MyBusinessesPage(page)
    my_biz.verify_metrics_button_not_visible()
    my_biz.verify_delete_button_not_visible()


@when('the collaborator toggles the open-close switch')
def collaborator_clicks_toggle(page: Page, shared_data):
    slug = shared_data['slug']
    my_biz = MyBusinessesPage(page)
    my_biz.toggle_business_open(slug)


@then('the toggle shows closed state for the business')
def verify_toggle_shows_closed(page: Page, shared_data):
    slug = shared_data['slug']
    my_biz = MyBusinessesPage(page)
    my_biz.verify_toggle_state(slug, False)


@when('the owner revokes the "can_toggle_open" permission for the collaborator via API')
def owner_revokes_toggle_permission(page: Page, shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    staff_id = shared_data['staff_id']
    owner_token = shared_data['owner_token']

    res = requests.patch(
        f"{base_url}/businesses/{slug}/staff/{staff_id}",
        json={"can_toggle_open": False},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res.ok, f"Error updating permissions: {res.text}"


@when('the collaborator attempts to toggle open-close via API')
def collaborator_attempts_toggle_api(page: Page, shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    collab_token = shared_data['collab_token']

    res = requests.patch(
        f"{base_url}/businesses/{slug}/toggle-open",
        headers={"Authorization": f"Bearer {collab_token}"}
    )
    shared_data['collab_toggle_res'] = res


@then('the API rejects the toggle with status 403 and permission denied message')
def verify_collab_toggle_forbidden(shared_data):
    res = shared_data['collab_toggle_res']
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    assert "No tienes permisos" in res.text or "permiso" in res.text.lower()


# ---------------------------------------------------------------------------
# SCENARIO 2: DIRECT SALE & HANDLED_BY TRACEABILITY
# ---------------------------------------------------------------------------

@when('the collaborator processes a direct sale order of 50 Bs via API')
def process_direct_sale_order(page: Page, shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    collab_token = shared_data['collab_token']
    prod_id = shared_data['prod_id']

    payload = {
        "customer_name": "Venta Directa Cliente Test",
        "delivery_method": "Entrega en el local",
        "total_price": 50.0,
        "is_direct_sale": True,
        "items": [
            {
                "product_id": prod_id,
                "product_name": "Menu Test",
                "quantity": 1,
                "price_at_time": 50.0,
                "subtotal": 50.0
            }
        ]
    }
    res = requests.post(
        f"{base_url}/businesses/{slug}/orders",
        json=payload,
        headers={"Authorization": f"Bearer {collab_token}"}
    )
    assert res.ok, f"Error processing direct sale: {res.text}"
    order_data = res.json()
    shared_data['direct_sale_order_id'] = order_data["id"]


@then('the order is created with status "completado" and handled_by assigned to the collaborator')
def verify_direct_sale_db_fields(shared_data):
    engine = _get_db_engine()
    order_id = shared_data['direct_sale_order_id']
    collab_id = shared_data['collab_id']

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, handled_by FROM orders WHERE id = :oid"),
            {"oid": order_id}
        ).fetchone()
        assert row is not None, f"Order {order_id} not found in DB"
        assert row[0] == "completado", f"Expected status 'completado', got {row[0]}"
        assert str(row[1]) == str(collab_id), f"Expected handled_by {collab_id}, got {row[1]}"


@when(parsers.parse('the collaborator logs in and navigates to orders page for "{slug}"'))
def collaborator_visits_orders_page(page: Page, shared_data, backend_api: APIUtils, slug):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/").rstrip("/")
    real_slug = shared_data['slug']
    collab_data = shared_data['collab_data']

    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")

    backend_api.inject_session_to_browser(page, collab_data)
    orders_page = BusinessOrdersPage(page)
    orders_page.go_to(real_slug)


@then(parsers.parse('the direct sale order card displays "Atendido por: {collab_name}"'))
def verify_direct_sale_handled_by_card(page: Page, shared_data, collab_name):
    order_id = shared_data['direct_sale_order_id']
    display_name = shared_data['collab_display_name']
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_handled_by(order_id, display_name)


@when('a customer creates an order with QR payment and submits a receipt')
def customer_creates_order_and_submits_receipt(page: Page, shared_data, backend_api: APIUtils):
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    prod_id = shared_data['prod_id']
    unique_suffix = uuid.uuid4().hex[:4]

    cust_name = f"Cliente QR {unique_suffix} Test"
    customer = backend_api.create_e2e_user(api_context, name=cust_name)
    customer_token = customer["access_token"]

    # 1. Crear Pedido
    order_payload = {
        "customer_name": cust_name,
        "delivery_method": "Entrega en el local",
        "total_price": 50.0,
        "is_direct_sale": False,
        "items": [
            {
                "product_id": prod_id,
                "product_name": "Menu Test",
                "quantity": 1,
                "price_at_time": 50.0,
                "subtotal": 50.0
            }
        ]
    }
    res_order = requests.post(
        f"{base_url}/businesses/{slug}/orders",
        json=order_payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res_order.ok, f"Error creating customer order: {res_order.text}"
    customer_order_id = res_order.json()["id"]

    # 2. Subir Comprobante (cambia a pago_enviado)
    png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    files = {"receipt": ("comprobante_test.png", png_bytes, "image/png")}
    res_receipt = requests.post(
        f"{base_url}/businesses/{slug}/orders/{customer_order_id}/receipt",
        files=files,
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res_receipt.ok, f"Error uploading receipt: {res_receipt.text}"

    shared_data['customer_order_id'] = customer_order_id


@then('the customer order is in status "pago_enviado" with handled_by unassigned')
def verify_customer_order_unassigned(shared_data):
    engine = _get_db_engine()
    order_id = shared_data['customer_order_id']
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, handled_by FROM orders WHERE id = :oid"),
            {"oid": order_id}
        ).fetchone()
        assert row is not None
        assert row[0] == "pago_enviado"
        assert row[1] is None, f"Expected handled_by None, got {row[1]}"


@when('the collaborator verifies and approves the customer payment')
def collaborator_approves_payment(page: Page, shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    collab_token = shared_data['collab_token']
    order_id = shared_data['customer_order_id']

    res = requests.put(
        f"{base_url}/businesses/{slug}/orders/{order_id}/status",
        json={"status": "pagado"},
        headers={"Authorization": f"Bearer {collab_token}"}
    )
    assert res.ok, f"Error verifying payment: {res.text}"


@then('the customer order status is updated to "pagado" and handled_by is assigned to the collaborator')
def verify_customer_order_handled_by_assigned(shared_data):
    engine = _get_db_engine()
    order_id = shared_data['customer_order_id']
    collab_id = shared_data['collab_id']

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, handled_by FROM orders WHERE id = :oid"),
            {"oid": order_id}
        ).fetchone()
        assert row is not None
        assert row[0] == "pagado"
        assert str(row[1]) == str(collab_id), f"Expected handled_by {collab_id}, got {row[1]}"


@when(parsers.parse('the owner logs in and navigates to orders page for "{slug}"'))
def owner_visits_orders_page(page: Page, shared_data, backend_api: APIUtils, slug):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/").rstrip("/")
    real_slug = shared_data['slug']
    owner_data = shared_data['owner_data']

    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")

    backend_api.inject_session_to_browser(page, owner_data)
    orders_page = BusinessOrdersPage(page)
    orders_page.go_to(real_slug)


@then(parsers.parse('the customer order card displays "Atendido por: {collab_name}"'))
def verify_customer_order_handled_by_card(page: Page, shared_data, collab_name):
    order_id = shared_data['customer_order_id']
    display_name = shared_data['collab_display_name']
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_handled_by(order_id, display_name)


# ---------------------------------------------------------------------------
# SCENARIO 3: MULTI-RECIPIENT PUSH NOTIFICATIONS
# ---------------------------------------------------------------------------

@given(parsers.parse('a collaborator "{staff_name}" with payment notifications enabled and web push subscription'))
def setup_staff_with_push_enabled(page: Page, shared_data, backend_api: APIUtils, staff_name):
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    owner_token = shared_data['owner_token']
    unique_suffix = uuid.uuid4().hex[:4]

    staff_data = backend_api.create_e2e_user(api_context, name=f"{staff_name} {unique_suffix}")
    staff_id = staff_data["user"]["id"] if "user" in staff_data else staff_data.get("id")

    res = requests.post(
        f"{base_url}/businesses/{slug}/staff",
        json={"query": staff_data["email"]},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res.ok, f"Error adding staff with push enabled: {res.text}"

    _insert_mock_push_subscription(staff_id)
    shared_data['staff_on_id'] = staff_id
    shared_data['staff_on_name'] = staff_name


@given(parsers.parse('a collaborator "{staff_name}" with payment notifications disabled and web push subscription'))
def setup_staff_with_push_disabled(page: Page, shared_data, backend_api: APIUtils, staff_name):
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    owner_token = shared_data['owner_token']
    unique_suffix = uuid.uuid4().hex[:4]

    staff_data = backend_api.create_e2e_user(api_context, name=f"{staff_name} {unique_suffix}")
    staff_id = staff_data["user"]["id"] if "user" in staff_data else staff_data.get("id")

    res = requests.post(
        f"{base_url}/businesses/{slug}/staff",
        json={"query": staff_data["email"]},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res.ok, f"Error adding staff: {res.text}"
    record = res.json()

    # Desactivar can_receive_payment_notifications
    res_perm = requests.patch(
        f"{base_url}/businesses/{slug}/staff/{record['id']}",
        json={"can_receive_payment_notifications": False},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res_perm.ok, f"Error revoking push permissions: {res_perm.text}"

    _insert_mock_push_subscription(staff_id)
    shared_data['staff_off_id'] = staff_id
    shared_data['staff_off_name'] = staff_name


@given('the owner has an active web push subscription')
def setup_owner_push_subscription(shared_data):
    owner_id = shared_data['owner_id']
    _insert_mock_push_subscription(owner_id)


@when('a customer creates an order and uploads a payment receipt')
def customer_orders_and_uploads_receipt(page: Page, shared_data, backend_api: APIUtils):
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    prod_id = shared_data['prod_id']
    unique_suffix = uuid.uuid4().hex[:4]

    cust_name = f"Push Customer {unique_suffix} Test"
    customer = backend_api.create_e2e_user(api_context, name=cust_name)
    customer_token = customer["access_token"]

    order_payload = {
        "customer_name": cust_name,
        "delivery_method": "Entrega en el local",
        "total_price": 50.0,
        "is_direct_sale": False,
        "items": [
            {
                "product_id": prod_id,
                "product_name": "Menu Test",
                "quantity": 1,
                "price_at_time": 50.0,
                "subtotal": 50.0
            }
        ]
    }
    res_order = requests.post(
        f"{base_url}/businesses/{slug}/orders",
        json=order_payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res_order.ok, f"Error creating order: {res_order.text}"
    order_id = res_order.json()["id"]

    png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    files = {"receipt": ("comprobante_test.png", png_bytes, "image/png")}
    res_receipt = requests.post(
        f"{base_url}/businesses/{slug}/orders/{order_id}/receipt",
        files=files,
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res_receipt.ok, f"Error uploading receipt: {res_receipt.text}"


@then('the background task dispatches push notifications to the business team')
def wait_for_push_background_dispatch():
    time.sleep(2.5)


@then('the owner receives the payment push notification with dollar icon')
def verify_owner_received_push(shared_data):
    owner_id = shared_data['owner_id']
    logs = _get_docker_logs()
    assert f"[DEBUG PUSH] Iniciando envío de push para el usuario: {owner_id}" in logs, (
        f"Owner {owner_id} did not receive push in backend logs"
    )
    assert "dollar-notification.png" in logs or "Pago Enviado" in logs


@then(parsers.parse('"{staff_name}" receives the payment push notification'))
def verify_staff_on_received_push(shared_data, staff_name):
    staff_on_id = shared_data['staff_on_id']
    logs = _get_docker_logs()
    assert f"[DEBUG PUSH] Iniciando envío de push para el usuario: {staff_on_id}" in logs, (
        f"Staff ON {staff_on_id} did not receive push in backend logs"
    )


@then(parsers.parse('"{staff_name}" does not receive the payment push notification'))
def verify_staff_off_not_received_push(shared_data, staff_name):
    staff_off_id = shared_data['staff_off_id']
    logs = _get_docker_logs()
    assert f"[DEBUG PUSH] Iniciando envío de push para el usuario: {staff_off_id}" not in logs, (
        f"Staff OFF {staff_off_id} unexpectedly received push in backend logs"
    )
