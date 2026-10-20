import os
import uuid
import json
import base64
import subprocess
import requests
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.order_tracking_page import OrderTrackingPage
from poms.business_orders_page import BusinessOrdersPage

# Load scenarios
scenarios("../../features/payment_notifications.feature")

@pytest.fixture
def shared_data():
    return {}

@pytest.fixture
def backend_api():
    return APIUtils()


def _get_db_engine():
    db_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or "postgresql://test_user:test_password@localhost:5433/tarjetoso_test"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


def _insert_mock_push_subscription(user_id: str):
    """Inserta una suscripción push mock en la base de datos para el usuario."""
    endpoint = f"https://fcm.googleapis.com/fcm/send/fake-test-endpoint-{uuid.uuid4().hex}"
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


def _get_docker_push_payloads():
    """Obtiene los últimos payloads de push registrados en los logs del backend."""
    res = subprocess.run(["docker", "logs", "spinjob_backend", "--tail", "250"], capture_output=True, text=True)
    combined = (res.stdout or "") + "\n" + (res.stderr or "")
    payloads = []
    for line in combined.splitlines():
        if "[DEBUG PUSH PAYLOAD]" in line:
            json_str = line.split("[DEBUG PUSH PAYLOAD]", 1)[1].strip()
            try:
                payloads.append(json.loads(json_str))
            except Exception:
                pass
    return payloads


def _wait_for_push_payload(filter_fn, timeout: float = 6.0):
    """Espera a que FastAPI BackgroundTasks termine de despachar y loguear el push."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        payloads = _get_docker_push_payloads()
        matching = [p for p in payloads if filter_fn(p)]
        if matching:
            return matching[-1]
        time.sleep(0.3)
    return None


def _setup_business_and_order(page: Page, backend_api: APIUtils, biz_name: str, buyer_name: str) -> dict:
    api_context = page.context.request
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    unique_suffix = uuid.uuid4().hex[:6]

    # 1. Crear Dueño
    seller_name = f"{biz_name} Owner {unique_suffix} Test"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True, is_admin=True)
    seller_token = seller_data["access_token"]
    seller_id = seller_data["user"]["id"] if "user" in seller_data else seller_data.get("id")

    # Registrar suscripción push para el dueño
    _insert_mock_push_subscription(seller_id)

    # 2. Crear Negocio
    short_slug = f"pn{unique_suffix}"
    biz_payload = {
        "name": f"{biz_name} {unique_suffix} Test",
        "title": "Comercio",
        "description": "Comercio para pruebas de notificaciones",
        "slug": short_slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "payment_methods": '["qr_simple", "efectivo"]',
        "orders_enabled": "true"
    }
    res = requests.post(f"{base_url}/businesses/", data=biz_payload, headers={"Authorization": f"Bearer {seller_token}"})
    assert res.ok, f"Error creando negocio: {res.text}"
    biz_id = res.json()["id"]

    # 3. Actualizar negocio en DB (aprobado, premium, slug corto)
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE businesses 
            SET slug = :sslug,
                status = 'aprobado'
            WHERE id = :bid
        """), {"bid": biz_id, "sslug": short_slug})

        conn.execute(text("""
            UPDATE business_subscriptions 
            SET premium = TRUE, 
                plan_months = 12, 
                expiration_date = NOW() + INTERVAL '365 days'
            WHERE business_id = :bid
        """), {"bid": biz_id})

    # 4. Crear Producto
    prod_payload = {
        "name": f"Producto Notif {unique_suffix} Test",
        "price": 100.0,
        "description": "Producto de prueba",
        "category": "General",
        "stock": 10
    }
    prod_res = requests.post(f"{base_url}/businesses/{short_slug}/products", data=prod_payload, headers={"Authorization": f"Bearer {seller_token}"})
    assert prod_res.ok, f"Error creando producto: {prod_res.text}"
    prod_id = prod_res.json()["id"]

    # 5. Crear Comprador
    customer_data = backend_api.create_e2e_user(api_context, name=f"{buyer_name} {unique_suffix} Test", is_seller=False)
    customer_token = customer_data["access_token"]
    customer_id = customer_data["user"]["id"] if "user" in customer_data else customer_data.get("id")

    # Registrar suscripción push para el cliente
    _insert_mock_push_subscription(customer_id)

    return {
        "slug": short_slug,
        "biz_id": biz_id,
        "owner_id": seller_id,
        "owner_token": seller_token,
        "customer_id": customer_id,
        "customer_token": customer_token,
        "customer_name": f"{buyer_name} {unique_suffix} Test",
        "product_id": prod_id
    }


# =============================================================================
# Step Definitions: Scenario 1
# =============================================================================

@given(parsers.parse('a premium business "{biz_name}" with push enabled for the owner'))
def premium_business_with_push(page: Page, shared_data, backend_api: APIUtils, biz_name):
    data = _setup_business_and_order(page, backend_api, biz_name, "Client Notif")
    shared_data.update(data)


@given(parsers.parse('a customer "{buyer_name}" with push enabled'))
def customer_with_push(page: Page, shared_data):
    # La sesión del cliente ya se preparó con push subscription en _setup_business_and_order
    assert "customer_id" in shared_data, "Customer ID must exist in shared_data"


@when('the customer places an order with "Transferencia / QR" payment')
def customer_places_qr_order(shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data["slug"]
    
    order_payload = {
        "customer_name": shared_data["customer_name"],
        "delivery_method": "Entrega en el local",
        "total_price": 100.0,
        "items": [
            {
                "product_id": shared_data["product_id"],
                "product_name": "Producto Notif Test",
                "price_at_time": 100.0,
                "quantity": 1,
                "subtotal": 100.0
            }
        ]
    }
    res = requests.post(
        f"{base_url}/businesses/{slug}/orders",
        json=order_payload,
        headers={"Authorization": f"Bearer {shared_data['customer_token']}"}
    )
    assert res.ok, f"Error creando orden: {res.text}"
    shared_data["order_id"] = res.json()["id"]


@when('the customer uploads a payment receipt')
def customer_uploads_receipt(shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data["slug"]
    order_id = shared_data["order_id"]

    png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    files = {"receipt": ("comprobante_test.png", png_bytes, "image/png")}
    
    res = requests.post(
        f"{base_url}/businesses/{slug}/orders/{order_id}/receipt",
        files=files,
        headers={"Authorization": f"Bearer {shared_data['customer_token']}"}
    )
    assert res.ok, f"Error subiendo comprobante: {res.text}"
    
    # Verificar en DB que el estado pasó a pago_enviado
    engine = _get_db_engine()
    with engine.connect() as conn:
        st = conn.execute(text("SELECT status FROM orders WHERE id = :oid"), {"oid": order_id}).scalar()
        assert st == "pago_enviado", f"Esperado pago_enviado, obtenido {st}"


@then('the backend sends a payment push to the owner with dollar icon')
def verify_payment_push_to_owner(shared_data):
    owner_id = shared_data["owner_id"]
    # 1. Verificar suscripción en DB
    engine = _get_db_engine()
    with engine.connect() as conn:
        subs = conn.execute(text("SELECT count(*) FROM push_subscriptions WHERE user_id = :uid"), {"uid": owner_id}).scalar()
        assert subs > 0, f"Owner {owner_id} debe tener suscripción push activa"

    # 2. Verificar que se despachó el payload con ícono del dólar y título
    slug = shared_data["slug"]
    last_payload = _wait_for_push_payload(
        lambda p: "Pago Enviado" in p.get("title", "") and slug in p.get("url", "")
    )
    assert last_payload is not None, f"No se encontró payload de Pago Enviado para el negocio {slug} en logs."
    assert last_payload.get("icon") == "/dollar-notification.png", f"Icono esperado /dollar-notification.png, recibido {last_payload.get('icon')}"
    shared_data["last_owner_payload"] = last_payload


@then(parsers.parse('the owner push URL redirects to "{expected_url_pattern}"'))
def verify_owner_push_url(shared_data, expected_url_pattern):
    slug = shared_data["slug"]
    expected_url = expected_url_pattern.replace("{slug}", slug)
    payload = shared_data.get("last_owner_payload") or {}
    assert payload.get("url") == expected_url, f"URL esperada {expected_url}, obtenida {payload.get('url')}"


@when('the business owner marks the order as paid')
def owner_marks_order_as_paid(shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data["slug"]
    order_id = shared_data["order_id"]

    res = requests.put(
        f"{base_url}/businesses/{slug}/orders/{order_id}/status",
        json={"status": "pagado"},
        headers={"Authorization": f"Bearer {shared_data['owner_token']}"}
    )
    assert res.ok, f"Error actualizando estado a pagado: {res.text}"

    # Verificar en DB
    engine = _get_db_engine()
    with engine.connect() as conn:
        st = conn.execute(text("SELECT status FROM orders WHERE id = :oid"), {"oid": order_id}).scalar()
        assert st == "pagado", f"Esperado pagado, obtenido {st}"


@then('the backend sends a payment accepted push to the customer')
def verify_payment_accepted_push(shared_data):
    customer_id = shared_data["customer_id"]
    # 1. Verificar suscripción en DB
    engine = _get_db_engine()
    with engine.connect() as conn:
        subs = conn.execute(text("SELECT count(*) FROM push_subscriptions WHERE user_id = :uid"), {"uid": customer_id}).scalar()
        assert subs > 0, f"Customer {customer_id} debe tener suscripción push activa"

    # 2. Verificar que se despachó el payload de pago aceptado
    order_id = shared_data["order_id"]
    last_payload = _wait_for_push_payload(
        lambda p: "pago ha sido aceptado" in p.get("title", "").lower() and order_id in p.get("url", "")
    )
    assert last_payload is not None, f"No se encontró payload de Pago Aceptado para la orden {order_id} en logs."
    shared_data["last_customer_payload"] = last_payload


@then(parsers.parse('the customer push URL redirects to "{expected_url_pattern}"'))
def verify_customer_push_url(shared_data, expected_url_pattern):
    slug = shared_data["slug"]
    order_id = shared_data["order_id"]
    expected_url = expected_url_pattern.replace("{slug}", slug).replace("{order_id}", order_id)
    payload = shared_data.get("last_customer_payload") or {}
    assert payload.get("url") == expected_url, f"URL esperada {expected_url}, obtenida {payload.get('url')}"


# =============================================================================
# Step Definitions: Scenario 2 (Rejection & Retry)
# =============================================================================

@given(parsers.parse('a premium business "{biz_name}" with a "pago_enviado" order'))
def business_with_pago_enviado_order(page: Page, shared_data, backend_api: APIUtils, biz_name):
    data = _setup_business_and_order(page, backend_api, biz_name, "Reject Client")
    shared_data.update(data)
    
    # Crear orden y subir comprobante inicial
    customer_places_qr_order(shared_data, backend_api)
    customer_uploads_receipt(shared_data, backend_api)


@when(parsers.parse('the business owner rejects the payment with reason "{reason}"'))
def owner_rejects_payment(shared_data, backend_api: APIUtils, reason):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data["slug"]
    order_id = shared_data["order_id"]

    res = requests.put(
        f"{base_url}/businesses/{slug}/orders/{order_id}/status",
        json={"status": "pendiente_de_pago", "payment_rejection_reason": reason},
        headers={"Authorization": f"Bearer {shared_data['owner_token']}"}
    )
    assert res.ok, f"Error rechazando pago: {res.text}"
    shared_data["rejection_reason"] = reason


@then('the order returns to "pendiente_de_pago" status')
def verify_order_status_pendiente(shared_data):
    order_id = shared_data["order_id"]
    engine = _get_db_engine()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status, payment_rejection_reason FROM orders WHERE id = :oid"), {"oid": order_id}).fetchone()
        assert row is not None
        assert row[0] == "pendiente_de_pago", f"Esperado pendiente_de_pago, obtenido {row[0]}"
        assert row[1] == shared_data.get("rejection_reason"), f"Razón esperada {shared_data.get('rejection_reason')}, obtenida {row[1]}"


@then('the receipt URL is cleared')
def verify_receipt_url_cleared(shared_data):
    order_id = shared_data["order_id"]
    engine = _get_db_engine()
    with engine.connect() as conn:
        receipt_url = conn.execute(text("SELECT receipt_url FROM orders WHERE id = :oid"), {"oid": order_id}).scalar()
        assert receipt_url is None or receipt_url == "", f"receipt_url debe ser None tras rechazo, obtenido {receipt_url}"


@then('the backend sends a payment rejected push to the customer')
def verify_payment_rejected_push(shared_data):
    customer_id = shared_data["customer_id"]
    order_id = shared_data["order_id"]
    engine = _get_db_engine()
    with engine.connect() as conn:
        subs = conn.execute(text("SELECT count(*) FROM push_subscriptions WHERE user_id = :uid"), {"uid": customer_id}).scalar()
        assert subs > 0, f"Customer {customer_id} debe tener suscripción push activa"

    last_payload = _wait_for_push_payload(
        lambda p: "rechazado" in p.get("title", "").lower() and order_id in p.get("url", "")
    )
    assert last_payload is not None, f"No se encontró payload de Pago Rechazado para la orden {order_id} en logs."
    assert "Comprobante ilegible" in last_payload.get("body", "")
    shared_data["last_rejection_payload"] = last_payload


@when('the customer uploads a new receipt')
def customer_uploads_new_receipt(shared_data, backend_api: APIUtils):
    customer_uploads_receipt(shared_data, backend_api)


@then('the order status changes to "pago_enviado"')
def verify_order_status_pago_enviado(shared_data):
    order_id = shared_data["order_id"]
    engine = _get_db_engine()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status, receipt_url FROM orders WHERE id = :oid"), {"oid": order_id}).fetchone()
        assert row is not None
        assert row[0] == "pago_enviado", f"Esperado pago_enviado, obtenido {row[0]}"
        assert row[1] is not None and len(row[1]) > 0, "receipt_url debe estar presente"


@then('a new push notification is sent to the business owner')
def verify_new_push_notification_to_owner(shared_data):
    verify_payment_push_to_owner(shared_data)


@then('a payment accepted push notification is sent to the customer')
def verify_payment_accepted_push_notification(shared_data):
    verify_payment_accepted_push(shared_data)
