import os
import json
import uuid
import pytest
import requests
from playwright.sync_api import Page, expect
from pytest_bdd import scenario, given, when, then, parsers
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.delivery_dashboard_page import DeliveryDashboardPage

FEATURE_FILE = os.path.join(os.path.dirname(__file__), "../../../features/orders/delivery_dispatch_board.feature")
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
FRONTEND_URL = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
DB_URL = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")

@scenario(FEATURE_FILE, 'Delivery role navigation replacement and distance tiering')
def test_delivery_role_navigation_and_distance_tiering():
    pass

@scenario(FEATURE_FILE, 'Atomic order claiming and delivery modal dismissal vector')
def test_atomic_order_claiming_and_delivery_modal_dismissal():
    pass

@scenario(FEATURE_FILE, 'Delivery earnings settlement report with date range filtering')
def test_delivery_earnings_settlement_report_with_date_range_filtering():
    pass

@pytest.fixture
def shared_data():
    return {}

def _get_auth_token(email: str, name: str, phone: str, is_delivery: bool = False, is_admin: bool = False, state: str = "La Paz"):
    res = requests.post(
        f"{API_BASE}/auth/e2e-login",
        json={
            "email": email,
            "name": name,
            "phone": phone,
            "is_verified": True,
            "is_delivery": is_delivery,
            "is_admin": is_admin
        },
        timeout=10
    )
    assert res.status_code == 200, f"Error logging in: {res.text}"
    user_data = res.json()
    token = user_data["access_token"]
    user_id = user_data["id"]

    # Asegurar departamento en base de datos
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET state = :st WHERE id = :uid"), {"st": state, "uid": user_id})

    return token, user_id, user_data

def _create_paid_order(owner_token: str, client_token: str, biz_slug: str, rest_lat: float, rest_lng: float):
    order_res = requests.post(
        f"{API_BASE}/businesses/{biz_slug}/orders",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "customer_name": "Cliente UI Test",
            "delivery_method": "Delivery",
            "total_price": 50.0,
            "delivery_cost": 15.0,
            "distance_km": 3.0,
            "delivery_location_url": f"https://www.google.com/maps?q={rest_lat + 0.01},{rest_lng + 0.01}",
            "items": [
                {
                    "product_name": "Almuerzo Ejecutivo",
                    "quantity": 1,
                    "price_at_time": 35.0,
                    "subtotal": 35.0
                }
            ]
        },
        timeout=10
    )
    assert order_res.status_code == 200, f"Error creando orden: {order_res.text}"
    order_id = order_res.json()["id"]

    # Marcar pagado por el restaurante
    status_res = requests.put(
        f"{API_BASE}/businesses/{biz_slug}/orders/{order_id}/status",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "pagado"},
        timeout=10
    )
    assert status_res.status_code == 200
    return order_id

def _create_premium_business(owner_token: str, name: str, slug: str, phone: str, lat: float, lng: float):
    biz_res = requests.post(
        f"{API_BASE}/businesses/",
        headers={"Authorization": f"Bearer {owner_token}"},
        data={
            "name": name,
            "slug": slug,
            "description": "Comida de prueba para delivery",
            "category": "Comida Rápida & Burgers",
            "subcategories": '["Hamburguesas"]',
            "phone": phone,
            "country": "Bolivia",
            "state": "La Paz",
            "delivery_methods": '["Delivery"]',
            "orders_enabled": "true",
            "ubicacion_url": f"https://www.google.com/maps?q={lat},{lng}"
        },
        timeout=10
    )
    assert biz_res.status_code == 200, f"Error creando negocio: {biz_res.text}"
    biz_data = biz_res.json()
    biz_id = biz_data["id"]

    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {"bid": biz_id, "exp": (datetime.now() + timedelta(days=365)).isoformat()})

    return biz_id, biz_data["slug"]

# =====================================================================
# GIVEN STEPS
# =====================================================================

@given("a delivery agent user logged into the application")
def given_delivery_agent_logged_in(page: Page, shared_data):
    unique = uuid.uuid4().hex[:6]
    email = f"driver_{unique}_Test@example.com"
    name = f"Motoquero {unique} Test"
    phone = f"77{unique[:6]}"

    token, user_id, user_data = _get_auth_token(email, name, phone, is_delivery=True, state="La Paz")
    shared_data["driver_token"] = token
    shared_data["driver_id"] = user_id

    # Inyectar geolocalización fija del repartidor en La Paz (-16.5020, -68.1510)
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation({"latitude": -16.5020, "longitude": -68.1510})

    # Inyectar sesión en localStorage
    session_user = {
        "id": user_id,
        "name": name,
        "email": email,
        "state": "La Paz",
        "is_delivery": True,
        "is_admin": False,
        "is_verified": True
    }
    init_script = f"""
        localStorage.setItem('spingamma_token', '{token}');
        localStorage.setItem('spingamma_user', JSON.stringify({json.dumps(session_user)}));
        localStorage.setItem('tarjetoso_delivery_work_mode', 'true');
        localStorage.setItem('tarjetoso_delivery_department', 'La Paz');
    """
    page.context.add_init_script(init_script)

@given("an available order located 2.0 km from the delivery agent")
def given_close_order(shared_data):
    unique = uuid.uuid4().hex[:6]
    owner_token, owner_id, _ = _get_auth_token(f"owner_close_{unique}_Test@example.com", f"Owner Close {unique} Test", f"71{unique[:6]}", state="La Paz")
    client_token, _, _ = _get_auth_token(f"client_close_{unique}_Test@example.com", f"Client Close {unique} Test", f"72{unique[:6]}", state="La Paz")

    biz_slug = f"rest-cerca-{unique}-test"
    # Restaurante cercano a -16.5000, -68.1500 (a menos de 1 km del repartidor)
    _, real_slug = _create_premium_business(
        owner_token,
        f"Restaurante Cerca {unique} Test",
        biz_slug,
        "59170011223",
        -16.5000,
        -68.1500
    )

    close_order_id = _create_paid_order(owner_token, client_token, real_slug, -16.5000, -68.1500)
    shared_data["close_order_id"] = close_order_id

@given("another available order located 10.0 km from the delivery agent")
def given_far_order(shared_data):
    unique = uuid.uuid4().hex[:6]
    owner_token, owner_id, _ = _get_auth_token(f"owner_far_{unique}_Test@example.com", f"Owner Far {unique} Test", f"73{unique[:6]}", state="La Paz")
    client_token, _, _ = _get_auth_token(f"client_far_{unique}_Test@example.com", f"Client Far {unique} Test", f"74{unique[:6]}", state="La Paz")

    biz_slug = f"rest-lejos-{unique}-test"
    # Restaurante lejano a -16.6500, -68.2500 (~20 km de distancia)
    _, real_slug = _create_premium_business(
        owner_token,
        f"Restaurante Lejos {unique} Test",
        biz_slug,
        "59170011224",
        -16.6500,
        -68.2500
    )

    far_order_id = _create_paid_order(owner_token, client_token, real_slug, -16.6500, -68.2500)
    shared_data["far_order_id"] = far_order_id

@given("an available order ready for dispatch")
def given_order_ready_for_dispatch(shared_data):
    unique = uuid.uuid4().hex[:6]
    owner_token, owner_id, _ = _get_auth_token(f"owner_disp_{unique}_Test@example.com", f"Owner Disp {unique} Test", f"75{unique[:6]}", state="La Paz")
    client_token, _, _ = _get_auth_token(f"client_disp_{unique}_Test@example.com", f"Client Disp {unique} Test", f"76{unique[:6]}", state="La Paz")

    biz_slug = f"rest-disp-{unique}-test"
    _, real_slug = _create_premium_business(
        owner_token,
        f"Restaurante Disp {unique} Test",
        biz_slug,
        "59170011225",
        -16.5010,
        -68.1505
    )

    order_id = _create_paid_order(owner_token, client_token, real_slug, -16.5010, -68.1505)
    shared_data["ready_order_id"] = order_id

@given("a delivery agent with delivered orders completed today")
def given_agent_with_completed_orders(page: Page, shared_data):
    given_delivery_agent_logged_in(page, shared_data)
    unique = uuid.uuid4().hex[:6]
    owner_token, _, _ = _get_auth_token(f"owner_hist_{unique}_Test@example.com", f"Owner Hist {unique} Test", f"78{unique[:6]}", state="La Paz")
    client_token, _, _ = _get_auth_token(f"client_hist_{unique}_Test@example.com", f"Client Hist {unique} Test", f"79{unique[:6]}", state="La Paz")

    biz_slug = f"rest-hist-{unique}-test"
    _, real_slug = _create_premium_business(
        owner_token,
        f"Restaurante Hist {unique} Test",
        biz_slug,
        "59170011228",
        -16.5000,
        -68.1500
    )

    order_id = _create_paid_order(owner_token, client_token, real_slug, -16.5000, -68.1500)
    
    # Motorizado toma la orden
    driver_token = shared_data["driver_token"]
    claim_res = requests.post(f"{API_BASE}/delivery/orders/{order_id}/claim", headers={"Authorization": f"Bearer {driver_token}"})
    assert claim_res.status_code == 200

    # Motorizado entrega la orden
    deliv_res = requests.post(f"{API_BASE}/delivery/orders/{order_id}/deliver", headers={"Authorization": f"Bearer {driver_token}"})
    assert deliv_res.status_code == 200
    shared_data["completed_order_id"] = order_id

# =====================================================================
# WHEN STEPS
# =====================================================================

@when("the delivery agent visits the home navigation bar")
def when_visit_home(page: Page):
    page.goto(f"{FRONTEND_URL}/")
    page.wait_for_load_state("networkidle")

@when("the delivery agent navigates to the delivery dispatch board")
def when_navigates_to_board(page: Page):
    page.goto(f"{FRONTEND_URL}/tablero-delivery")
    page.wait_for_load_state("networkidle")
    dashboard = DeliveryDashboardPage(page)
    dashboard.verify_page_loaded()
    dashboard.ensure_work_mode_active()

@when("the delivery agent clicks accept order")
def when_clicks_accept_order(page: Page, shared_data):
    if page.url == "about:blank" or not page.url.endswith("/tablero-delivery"):
        page.goto(f"{FRONTEND_URL}/tablero-delivery")
        page.wait_for_load_state("networkidle")
    dashboard = DeliveryDashboardPage(page)
    dashboard.verify_page_loaded()
    dashboard.switch_to_available_tab()
    order_id = shared_data["ready_order_id"]
    dashboard.claim_order(order_id)

@when("the delivery agent opens the deliver confirmation modal")
def when_opens_deliver_modal(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    order_id = shared_data["ready_order_id"]
    dashboard.open_deliver_modal(order_id)

@when("the delivery agent clicks not yet to dismiss the modal")
def when_dismisses_modal(page: Page):
    dashboard = DeliveryDashboardPage(page)
    dashboard.dismiss_deliver_modal()

@when("the delivery agent confirms order delivered")
def when_confirms_delivered(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    order_id = shared_data["ready_order_id"]
    dashboard.confirm_delivery(order_id)

@when("the delivery agent switches to the completed deliveries subtab")
def when_switches_to_history(page: Page):
    if page.url == "about:blank" or not page.url.endswith("/tablero-delivery"):
        page.goto(f"{FRONTEND_URL}/tablero-delivery")
        page.wait_for_load_state("networkidle")
    dashboard = DeliveryDashboardPage(page)
    dashboard.verify_page_loaded()
    dashboard.switch_to_history_subtab()

@when("filters the history by today date range")
def when_filters_today(page: Page):
    dashboard = DeliveryDashboardPage(page)
    today_str = datetime.now().strftime("%Y-%m-%d")
    dashboard.filter_today_button.click()

# =====================================================================
# THEN STEPS
# =====================================================================

@then("the navigation menu should display the delivery motorcycle button instead of my businesses")
def then_verify_moto_button(page: Page):
    # En desktop o mobile menu debe figurar el enlace /tablero-delivery
    moto_btn = page.locator("a[href='/tablero-delivery'], button:has-text('Delivery')").first
    expect(moto_btn).to_be_visible(timeout=10000)
    # Prohibido mostrar botón 'Mis negocios'
    my_biz_btn = page.locator("button:has-text('Mis negocios'), a:has-text('Mis negocios')")
    expect(my_biz_btn).not_to_be_visible()

@then("the close order card should display a green badge and an active accept button")
def then_verify_close_order(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    close_id = shared_data["close_order_id"]
    close_card = dashboard.get_available_card(close_id)
    expect(close_card).to_be_visible(timeout=10000)
    # Badge verde
    green_badge = close_card.locator("text=🟢")
    expect(green_badge).to_be_visible(timeout=10000)
    # Botón activo
    accept_btn = dashboard.get_accept_button(close_id)
    expect(accept_btn).to_be_visible(timeout=10000)
    expect(accept_btn).to_be_enabled()

@then("the far order card should display a red badge and a disabled button with distance warning")
def then_verify_far_order(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    far_id = shared_data["far_order_id"]
    far_card = dashboard.get_available_card(far_id)
    expect(far_card).to_be_visible(timeout=10000)
    # Badge rojo
    expect(far_card.locator("text=🔴")).to_be_visible(timeout=10000)
    # Botón bloqueado
    blocked_btn = dashboard.get_blocked_button(far_id)
    expect(blocked_btn).to_be_visible(timeout=10000)
    expect(blocked_btn).to_be_disabled()
    # Advertencia visible
    expect(far_card.locator("text=Debes estar más cerca para aceptar el pedido")).to_be_visible()

@then("the order should vanish from available orders")
def then_order_vanishes(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    order_id = shared_data["ready_order_id"]
    expect(dashboard.get_available_card(order_id)).not_to_be_visible()

@then("the view should switch to active deliveries showing the order in transit")
def then_view_switches_to_active(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    order_id = shared_data["ready_order_id"]
    active_card = dashboard.get_active_card(order_id)
    expect(active_card).to_be_visible(timeout=10000)
    expect(active_card.locator("text=En camino al cliente")).to_be_visible()

@then("the confirmation modal should close and the order should remain in transit")
def then_modal_closed_order_in_transit(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    order_id = shared_data["ready_order_id"]
    active_card = dashboard.get_active_card(order_id)
    expect(active_card).to_be_visible()

@then("the order should transition to completed with a success notification")
def then_order_transition_completed(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    order_id = shared_data["ready_order_id"]
    # Debe desaparecer de activas
    expect(dashboard.get_active_card(order_id)).not_to_be_visible(timeout=10000)
    # En completadas debe aparecer
    dashboard.switch_to_history_subtab()
    completed_card = dashboard.get_completed_card(order_id)
    expect(completed_card).to_be_visible(timeout=10000)

@then("the settlement summary card should display the total completed runs and accumulated earnings")
def then_verify_settlement_summary(page: Page, shared_data):
    dashboard = DeliveryDashboardPage(page)
    expect(dashboard.summary_card).to_be_visible(timeout=10000)
    # Debe reflejar al menos 1 carrera y ganancias en Bs.
    expect(dashboard.summary_card.locator("text=/1 carrera|carreras/i")).to_be_visible()
    expect(dashboard.summary_card.locator("text=/Bs\\./i").first).to_be_visible()
