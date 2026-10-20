import os
import uuid
import requests
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from utils.api_testing import APIUtils
from sqlalchemy import create_engine, text

from poms.header_page import HeaderPage
from poms.push_prompt_modal_page import PushPromptModalPage
from poms.create_business_page import CreateBusinessPage
from poms.profile_page import ProfilePage
from poms.checkout_page import CheckoutPage

# Load scenarios
scenarios("../../features/order_push_notifications.feature")

@pytest.fixture
def shared_data():
    return {}

@pytest.fixture
def backend_api(page: Page):
    return APIUtils()

MOCK_PUSH_SCRIPT = """
let currentSubscription = null;
const mockPushManager = {
    subscribe: async () => {
        const uniqueEndpoint = 'https://fcm.googleapis.com/fcm/send/fake-endpoint-test-' + Math.random().toString(36).substring(7);
        currentSubscription = {
            endpoint: uniqueEndpoint,
            keys: { p256dh: 'fake-p256dh', auth: 'fake-auth' },
            toJSON: () => ({
                endpoint: uniqueEndpoint,
                keys: { p256dh: 'fake-p256dh', auth: 'fake-auth' }
            }),
            unsubscribe: async () => {
                currentSubscription = null;
                return true;
            }
        };
        return currentSubscription;
    },
    getSubscription: async () => currentSubscription
};

const mockRegistration = { pushManager: mockPushManager };

Object.defineProperty(navigator, 'serviceWorker', {
    value: {
        ready: Promise.resolve(mockRegistration),
        register: async () => mockRegistration,
        getRegistrations: async () => [mockRegistration],
        addEventListener: () => {},
        removeEventListener: () => {}
    },
    writable: true,
    configurable: true
});
"""

def _setup_business_for_owner(user_data: dict, backend_api: APIUtils, biz_name: str, is_premium: bool = True):
    owner_token = user_data["access_token"]
    owner_id = user_data["user"]["id"] if "user" in user_data else user_data.get("id")
    
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    
    unique_suffix = uuid.uuid4().hex[:4]
    requested_slug = f"biz-{unique_suffix}"
    
    biz_payload = {
        "name": f"{biz_name} {unique_suffix}",
        "title": "Comercio",
        "description": "Comercio para pruebas Push",
        "slug": requested_slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": user_data["email"],
        "delivery_methods": '[]',
        "payment_methods": '["efectivo"]',
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
    final_slug = biz_data.get("slug", requested_slug)
    
    # Crear producto para compras
    prod_payload = {
        "name": f"Producto Test {unique_suffix}",
        "price": 25.0,
        "description": "Producto de prueba",
        "category": "General",
        "stock": 10
    }
    prod_res = requests.post(
        f"{base_url}/businesses/{final_slug}/products",
        data=prod_payload,
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert prod_res.ok, f"Error creando producto: {prod_res.text}"
    
    # Asegurar que el negocio sea Premium en base de datos
    db_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or "postgresql://test_user:test_password@localhost:5433/tarjetoso_test"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE businesses
            SET status = 'aprobado'
            WHERE id = :bid
        """), {"bid": biz_id})
        conn.execute(text("""
            UPDATE business_subscriptions 
            SET premium = TRUE, 
                plan_months = 3, 
                expiration_date = NOW() + INTERVAL '90 days'
            WHERE business_id = :bid
        """), {"bid": biz_id})
        
    return {
        "id": biz_id,
        "slug": final_slug,
        "owner_id": owner_id,
        "owner_token": owner_token
    }

@given(parsers.parse('a seller user registered and logged in with "{user_name}"'))
def seller_logged_in(page: Page, shared_data, user_name, backend_api: APIUtils):
    assert user_name.endswith("Test"), f"Nombre '{user_name}' debe terminar con 'Test'"
    api_request_context = page.context.request
    page.add_init_script(MOCK_PUSH_SCRIPT)
    
    user_data = backend_api.create_e2e_user(api_request_context, name=user_name, is_seller=True)
    backend_api.inject_session_to_browser(page, user_data)
    
    biz_info = _setup_business_for_owner(user_data, backend_api, user_name, is_premium=True)
    
    shared_data['owner_token'] = biz_info["owner_token"]
    shared_data['owner_id'] = biz_info["owner_id"]
    shared_data['business_slug'] = biz_info["slug"]
    
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))

@given(parsers.parse('a standard business owner registered and logged in with "{user_name}"'))
def standard_owner_logged_in(page: Page, shared_data, user_name, backend_api: APIUtils):
    assert user_name.endswith("Test"), f"Nombre '{user_name}' debe terminar con 'Test'"
    api_request_context = page.context.request
    page.add_init_script(MOCK_PUSH_SCRIPT)
    
    # Pure owner: is_seller=False, is_admin=False
    user_data = backend_api.create_e2e_user(api_request_context, name=user_name, is_seller=False, is_admin=False)
    backend_api.inject_session_to_browser(page, user_data)
    
    biz_info = _setup_business_for_owner(user_data, backend_api, user_name, is_premium=True)
    
    shared_data['owner_token'] = biz_info["owner_token"]
    shared_data['owner_id'] = biz_info["owner_id"]
    shared_data['business_slug'] = biz_info["slug"]
    
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))

@given('the owner has enabled push notifications')
def owner_enables_push(page: Page, shared_data):
    header = HeaderPage(page)
    header.verify_page_loaded()
    
    with page.expect_response("**/usuarios/push/subscribe") as response_info:
        header.click_notifications_toggle()
        modal = PushPromptModalPage(page)
        modal.verify_page_loaded()
        modal.click_permitir()
        
    response = response_info.value
    assert response.status == 200, f"Expected 200, got {response.status}"
    header.expect_notifications_active()

@when('the owner clicks the notifications toggle to disable')
def owner_disables_push(page: Page, shared_data):
    header = HeaderPage(page)
    
    with page.expect_response("**/usuarios/push/unsubscribe*") as response_info:
        header.click_notifications_toggle()
        
    response = response_info.value
    assert response.status == 200, f"Expected 200, got {response.status}"
    header.expect_notifications_inactive()

@given('a customer Test is browsing the owner\'s business')
@when('a customer Test is browsing the owner\'s business')
def customer_browsing(page: Page, shared_data, backend_api: APIUtils):
    page.context.clear_cookies()
    page.evaluate("() => localStorage.clear()")
    
    api_request_context = page.context.request
    customer_data = backend_api.create_e2e_user(api_request_context, name="Customer Buyer Test", is_seller=False)
    backend_api.inject_session_to_browser(page, customer_data)
    
    shared_data['customer_token'] = customer_data["access_token"]
    
    slug = shared_data['business_slug']
    profile = ProfilePage(page)
    profile.go_to(slug)

@given('an admin buyer Test is browsing the owner\'s business')
def admin_buyer_browsing(page: Page, shared_data, backend_api: APIUtils):
    page.context.clear_cookies()
    page.evaluate("() => localStorage.clear()")
    
    api_request_context = page.context.request
    admin_data = backend_api.create_e2e_user(api_request_context, name="Admin Buyer Test", is_seller=False, is_admin=True)
    backend_api.inject_session_to_browser(page, admin_data)
    
    shared_data['customer_token'] = admin_data["access_token"]
    
    slug = shared_data['business_slug']
    profile = ProfilePage(page)
    profile.go_to(slug)

@when('the customer places a new order')
def customer_places_order(page: Page, shared_data):
    profile = ProfilePage(page)
    profile.verify_page_loaded()
    
    # Agregar producto al carrito
    profile.add_random_product_to_cart()
    profile.go_to_checkout()
    
    # Completar Checkout
    checkout = CheckoutPage(page)
    checkout.verify_page_loaded()
    
    with page.expect_response("**/orders") as response_info:
        checkout.confirm_order()
        
    response = response_info.value
    assert response.status == 200, f"Failed to place order: {response.status}"
    shared_data['order_status'] = response.status

@then('the order is created in pending payment status without sending push notification')
def verify_order_created_silent(page: Page, shared_data, backend_api: APIUtils):
    owner_id = shared_data.get('owner_id')
    assert owner_id is not None, "Owner ID must be present in shared_data"
    
    db_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or "postgresql://test_user:test_password@localhost:5433/tarjetoso_test"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # 1. Assert owner has an active push subscription registered
        subs = conn.execute(text("SELECT endpoint FROM push_subscriptions WHERE user_id = :uid"), {"uid": owner_id}).fetchall()
        assert len(subs) > 0, f"Owner {owner_id} must have at least 1 active push subscription in DB"
        
        # 2. Assert business owner matches
        biz = conn.execute(text("SELECT owner_id FROM businesses WHERE slug = :slug"), {"slug": shared_data['business_slug']}).fetchone()
        assert biz is not None and biz[0] == owner_id, f"Business owner {biz} does not match expected {owner_id}"
        
        # 3. Assert order was successfully registered in DB
        order = conn.execute(text("""
            SELECT id, status, total_price 
            FROM orders 
            WHERE business_id = (SELECT id FROM businesses WHERE slug = :slug) 
            ORDER BY created_at DESC LIMIT 1
        """), {"slug": shared_data['business_slug']}).fetchone()
        assert order is not None, "Order was not found in DB for the business"
        assert order[1] in ["pendiente_de_pago", "completado"], f"Unexpected order status: {order[1]}"

        # 4. Assert NO push notification payload was dispatched for new order received
        import subprocess
        res = subprocess.run(["docker", "logs", "spinjob_backend", "--tail", "50"], capture_output=True, text=True)
        recent_logs = (res.stdout or "") + "\n" + (res.stderr or "")
        assert f"Has recibido un pedido por {order[2]}" not in recent_logs, "Push de Nuevo Pedido no debería haberse enviado"

@then('the business owner does NOT receive a push notification')
def verify_no_push_received(page: Page, shared_data):
    owner_id = shared_data.get('owner_id')
    assert owner_id is not None
    
    db_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or "postgresql://test_user:test_password@localhost:5433/tarjetoso_test"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    engine = create_engine(db_url)
    with engine.connect() as conn:
        subs = conn.execute(text("SELECT count(*) FROM push_subscriptions WHERE user_id = :uid"), {"uid": owner_id}).scalar()
        assert subs == 0, f"Expected 0 active push subscriptions after opt-out, found {subs}"

@then('the order is placed and push dispatch is skipped without error')
def verify_order_placed_no_push_error(page: Page, shared_data):
    owner_id = shared_data.get('owner_id')
    assert owner_id is not None
    assert shared_data.get('order_status') == 200, "Order should be placed with 200 OK"
    
    db_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or "postgresql://test_user:test_password@localhost:5433/tarjetoso_test"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    engine = create_engine(db_url)
    with engine.connect() as conn:
        subs = conn.execute(text("SELECT count(*) FROM push_subscriptions WHERE user_id = :uid"), {"uid": owner_id}).scalar()
        assert subs == 0, f"Owner should have 0 push subscriptions, found {subs}"
        
        order = conn.execute(text("""
            SELECT id, status 
            FROM orders 
            WHERE business_id = (SELECT id FROM businesses WHERE slug = :slug) 
            ORDER BY created_at DESC LIMIT 1
        """), {"slug": shared_data['business_slug']}).fetchone()
        assert order is not None, "Order must be created successfully even without push subscription"
