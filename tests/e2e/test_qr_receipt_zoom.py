import os
import uuid
import requests
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.order_tracking_page import OrderTrackingPage

# Load scenarios
scenarios("../../features/qr_receipt_zoom.feature")

@pytest.fixture
def shared_data():
    return {}

@pytest.fixture
def backend_api():
    return APIUtils()


def _setup_qr_order(page: Page, backend_api: APIUtils, status: str = "pendiente_de_pago", receipt_url: str = None) -> dict:
    """Helper para crear negocio con QR, producto, cliente y orden para los tests de Zoom."""
    api_context = page.context.request
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    unique_suffix = uuid.uuid4().hex[:6]

    # 1. Crear vendedor
    seller_name = f"Seller Zoom {unique_suffix} Test"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True, is_admin=True)
    seller_token = seller_data["access_token"]

    # 2. Crear negocio con qr_simple
    slug = f"zm{unique_suffix}"
    biz_payload = {
        "name": f"Zoom Business {unique_suffix} Test",
        "title": "Restaurante",
        "description": "Comercio de prueba para zoom de QR y comprobantes",
        "slug": slug,
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
    biz_data = res.json()
    biz_id = biz_data["id"]
    real_slug = biz_data.get("slug", slug)

    # 3. Crear producto
    prod_payload = {
        "name": f"Producto Zoom {unique_suffix} Test",
        "price": 50.0,
        "description": "Producto de prueba",
        "category": "General",
        "stock": 10
    }
    prod_res = requests.post(f"{base_url}/businesses/{real_slug}/products", data=prod_payload, headers={"Authorization": f"Bearer {seller_token}"})
    assert prod_res.ok, f"Error creando producto: {prod_res.text}"
    prod_id = prod_res.json()["id"]

    # 4. Actualizar negocio en DB: Premium, Aprobado, slug corto y con qr_payment_url
    short_slug = f"zm{unique_suffix}"
    fake_qr = "https://res.cloudinary.com/dummy/image/upload/v1/qr_test.png"
    db_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or "postgresql://test_user:test_password@localhost:5433/tarjetoso_test"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE businesses 
            SET slug = :sslug,
                status = 'aprobado', 
                qr_payment_url = :qr 
            WHERE id = :bid
        """), {"bid": biz_id, "sslug": short_slug, "qr": fake_qr})

        conn.execute(text("""
            UPDATE business_subscriptions 
            SET premium = TRUE, 
                plan_months = 12, 
                expiration_date = NOW() + INTERVAL '365 days'
            WHERE business_id = :bid
        """), {"bid": biz_id})

    real_slug = short_slug

    # 5. Crear comprador y sesión
    buyer_name = f"Buyer Zoom {unique_suffix} Test"
    buyer_data = backend_api.create_e2e_user(api_context, name=buyer_name, is_seller=False)
    buyer_token = buyer_data["access_token"]
    buyer_id = buyer_data["user"]["id"] if "user" in buyer_data else buyer_data.get("id")

    # 6. Crear orden vía API como comprador
    order_payload = {
        "customer_name": buyer_name,
        "delivery_method": "Entrega en el local",
        "total_price": 50.0,
        "items": [
            {
                "product_id": prod_id,
                "product_name": f"Producto Zoom {unique_suffix} Test",
                "price_at_time": 50.0,
                "quantity": 1,
                "subtotal": 50.0
            }
        ]
    }
    order_res = requests.post(
        f"{base_url}/businesses/{real_slug}/orders",
        json=order_payload,
        headers={"Authorization": f"Bearer {buyer_token}"}
    )
    assert order_res.ok, f"Error creando orden: {order_res.text}"
    order_data = order_res.json()
    order_id = order_data["id"]

    # Si se pide estado específico o receipt_url, actualizar en DB
    if status != "pendiente_de_pago" or receipt_url:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE orders 
                SET status = :st, 
                    receipt_url = :rurl 
                WHERE id = :oid
            """), {"st": status, "rurl": receipt_url, "oid": order_id})

    # 7. Inyectar sesión de comprador en navegador
    backend_api.inject_session_to_browser(page, buyer_data)

    return {
        "slug": real_slug,
        "order_id": order_id,
        "buyer_token": buyer_token,
        "seller_token": seller_token,
        "qr_url": fake_qr
    }


# =============================================================================
# Step Definitions
# =============================================================================

@given('a pending order with QR payment method')
def pending_order_with_qr(page: Page, shared_data, backend_api: APIUtils):
    info = _setup_qr_order(page, backend_api, status="pendiente_de_pago")
    shared_data.update(info)
    
    frontend_base = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(f"{frontend_base}/perfil/{info['slug']}/orden/{info['order_id']}")
    tracking = OrderTrackingPage(page)
    tracking.verify_page_loaded()


@given('an order in "pago_enviado" status with uploaded receipt')
def order_with_uploaded_receipt(page: Page, shared_data, backend_api: APIUtils):
    fake_receipt = "https://res.cloudinary.com/dummy/image/upload/v1/receipt_test.png"
    info = _setup_qr_order(page, backend_api, status="pago_enviado", receipt_url=fake_receipt)
    shared_data.update(info)
    
    frontend_base = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(f"{frontend_base}/perfil/{info['slug']}/orden/{info['order_id']}")
    tracking = OrderTrackingPage(page)
    tracking.verify_page_loaded()


@when('the customer clicks the QR payment image in tracking')
def click_qr_image_in_tracking(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.click_qr_image()


@then('a fullscreen modal appears with the enlarged QR image')
def verify_enlarged_qr_modal(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.verify_zoom_modal_open("QR de Pago")


@then('the modal has a dark backdrop and a close button')
def verify_modal_backdrop_and_close_button(page: Page):
    modal = page.locator("[data-testid='enlarged-image-modal']")
    expect(modal).to_be_visible()
    close_btn = page.locator("[data-testid='close-enlarged-image-btn']")
    expect(close_btn).to_be_visible()


@when('the customer clicks the close button')
def click_close_modal_button(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.close_zoom_modal_via_button()


@then('the modal closes and the page returns to normal')
def verify_modal_closed(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.verify_zoom_modal_closed()


@when('the customer clicks the receipt image in tracking')
def click_receipt_image_in_tracking(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.click_receipt_image()


@then('a fullscreen modal appears with the enlarged receipt')
def verify_enlarged_receipt_modal(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.verify_zoom_modal_open("Comprobante de Pago")


@when('the customer clicks outside the modal')
def click_outside_modal_backdrop(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.close_zoom_modal_via_backdrop()


@then('the modal closes')
def verify_modal_closed_again(page: Page):
    tracking = OrderTrackingPage(page)
    tracking.verify_zoom_modal_closed()
