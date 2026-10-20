import os
import re
import pytest
import requests
from playwright.sync_api import Page, expect
from pytest_bdd import scenario, given, when, then, parsers
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage
from poms.checkout_page import CheckoutPage
from poms.business_orders_page import BusinessOrdersPage


FEATURE_FILE = os.path.join(os.path.dirname(__file__), "../../../features/orders/orders_delivery_mode.feature")


@scenario(FEATURE_FILE, 'Customer quotes and places an order with delivery mode using map')
def test_customer_quotes_and_places_order_with_delivery_mode():
    pass


@scenario(FEATURE_FILE, 'Checkout is blocked when business has no dispatch coordinates')
def test_checkout_blocked_when_business_has_no_dispatch_coordinates():
    pass


@scenario(FEATURE_FILE, 'Submodal dismissal vector preserves parent checkout form state')
def test_submodal_dismissal_vector_preserves_parent_checkout_form():
    pass


@scenario(FEATURE_FILE, 'Catalog delivery methods configuration enforces minimum one invariant')
def test_catalog_delivery_methods_configuration_enforces_minimum_one():
    pass


@scenario(FEATURE_FILE, 'Buyer searches delivery location using Google Maps link in map modal')
def test_buyer_searches_delivery_location_using_google_maps_link():
    pass


@scenario(FEATURE_FILE, 'Road circuity factor increases delivery distance and fee above straight line')
def test_road_circuity_factor_increases_delivery_distance_and_fee():
    pass


@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


def _setup_business(page: Page, backend_api: APIUtils, biz_name: str, slug: str, with_location: bool = True, location_url: str = None, state: str = "Santa Cruz"):
    assert biz_name.endswith("Test"), f"Nombre '{biz_name}' debe terminar con 'Test'"
    api_context = page.context.request
    
    # 1. Crear usuario vendedor
    seller_name = f"Dueño {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]
    
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    
    # 2. Crear negocio
    biz_payload = {
        "name": biz_name,
        "title": "Restaurante Delivery",
        "description": "Comercio para pruebas E2E de delivery",
        "slug": slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": state,
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local", "Delivery"]',
        "payment_methods": '["efectivo", "qr_simple"]',
        "orders_enabled": "true"
    }
    if with_location:
        biz_payload["ubicacion_url"] = location_url or "https://www.google.com/maps?q=-17.7833,-63.1821"

    res = requests.post(
        f"{base_url}/businesses/",
        data=biz_payload,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok, f"Error creando negocio: {res.text}"
    biz_data = res.json()
    biz_id = biz_data["id"]
    real_slug = biz_data["slug"]

    # 3. Forzar rol admin y suscripción premium activa en DB de testing
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET is_admin = TRUE WHERE id = :id"), {"id": seller_data["id"]})
        from datetime import datetime, timedelta
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {
            "bid": biz_id,
            "exp": (datetime.now() + timedelta(days=365)).isoformat()
        })
        conn.execute(text("""
            UPDATE businesses SET orders_enabled = TRUE, qr_payment_url = 'https://fake-qr.com/qr.png'
            WHERE id = :bid
        """), {"bid": biz_id})

    return {
        "biz_id": biz_id,
        "slug": real_slug,
        "seller_data": seller_data,
        "seller_token": seller_token
    }


# =====================================================================
# GIVEN STEPS
# =====================================================================

@given(parsers.parse('a premium business with location exists with name "{biz_name}" and slug "{slug}"'), target_fixture="biz_context")
def given_business_with_location(page: Page, shared_data, backend_api: APIUtils, biz_name: str, slug: str):
    biz = _setup_business(page, backend_api, biz_name, slug, with_location=True)
    shared_data.update(biz)
    return biz


@given(parsers.parse('a premium business without location exists with name "{biz_name}" and slug "{slug}"'), target_fixture="biz_context")
def given_business_without_location(page: Page, shared_data, backend_api: APIUtils, biz_name: str, slug: str):
    biz = _setup_business(page, backend_api, biz_name, slug, with_location=False)
    shared_data.update(biz)
    return biz


@given(parsers.parse('a premium business in La Paz with location exists with name "{biz_name}" and slug "{slug}"'), target_fixture="biz_context")
def given_business_in_la_paz(page: Page, shared_data, backend_api: APIUtils, biz_name: str, slug: str):
    # Coordenadas Obrajes / Bella Vista (-16.5349061, -68.1050929)
    biz = _setup_business(page, backend_api, biz_name, slug, with_location=True, location_url="https://www.google.com/maps?q=-16.5349061,-68.1050929", state="La Paz")
    shared_data.update(biz)
    return biz


@given(parsers.parse('a product "{prod_name}" exists for "{slug}"'))
def given_product_exists(page: Page, shared_data, backend_api: APIUtils, prod_name: str, slug: str):
    assert prod_name.endswith("Test"), f"Nombre '{prod_name}' debe terminar con 'Test'"
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    seller_token = shared_data['seller_token']
    real_slug = shared_data['slug']

    payload = {
        "name": prod_name,
        "price": 50.00,
        "stock": 50,
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


@given(parsers.parse('the seller of "{slug}" has orders and delivery enabled'))
def seller_has_orders_and_delivery_enabled(page: Page, shared_data, slug: str):
    # Ya asegurado mediante DB en _setup_business
    pass


@given('a buyer user is logged in')
def given_buyer_logged_in(page: Page, backend_api: APIUtils):
    api_context = page.context.request
    buyer_data = backend_api.create_e2e_user(api_context, name="Comprador Delivery Test")
    backend_api.inject_session_to_browser(page, buyer_data)


# =====================================================================
# WHEN STEPS
# =====================================================================

@when(parsers.parse('the buyer goes to "{slug}" profile'))
def buyer_visits_profile(page: Page, shared_data, slug: str):
    real_slug = shared_data['slug']
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


@when(parsers.parse('the buyer adds "{prod_name}" to the cart'))
def buyer_adds_product_to_cart(page: Page, shared_data, prod_name: str):
    profile_page = ProfilePage(page)
    product_id = shared_data['product_id']
    profile_page.add_to_cart(product_id)
    plus_btn = page.locator(f"[data-testid='add-to-cart-btn-{product_id}']").first
    expect(plus_btn).to_be_visible(timeout=5000)


@when('the buyer adds a product to cart and goes to checkout')
def buyer_adds_any_product_and_goes_to_checkout(page: Page, shared_data):
    profile_page = ProfilePage(page)
    product_id = shared_data['product_id']
    profile_page.add_to_cart(product_id)
    profile_page.go_to_checkout()
    expect(page.locator("h1", has_text="Tu Pedido")).to_be_visible(timeout=5000)


@when('the buyer proceeds to checkout')
def buyer_proceeds_to_checkout(page: Page):
    profile_page = ProfilePage(page)
    profile_page.go_to_checkout()
    expect(page.locator("h1", has_text="Tu Pedido")).to_be_visible(timeout=5000)


@when(parsers.parse('the buyer fills customer name "{cust_name}"'))
def buyer_fills_customer_name(page: Page, cust_name: str):
    checkout_page = CheckoutPage(page)
    checkout_page.fill_customer_name(cust_name)


@when(parsers.parse('the buyer selects "{method}" delivery method'))
def buyer_selects_delivery_method(page: Page, method: str):
    checkout_page = CheckoutPage(page)
    checkout_page.select_delivery_method(method)


@when('the buyer opens the delivery map modal')
def buyer_opens_delivery_map(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.open_delivery_map()
    expect(page.locator("[data-testid='map-close-button']")).to_be_visible(timeout=10000)


@when(parsers.parse('the buyer searches "{query}" in the delivery map'))
def buyer_searches_in_delivery_map(page: Page, query: str):
    checkout_page = CheckoutPage(page)
    checkout_page.search_in_delivery_map(query)


@when('the buyer confirms delivery location on the map')
def buyer_confirms_delivery_location(page: Page):
    # Esperar a que el mapa Leaflet esté listo
    page.wait_for_selector(".leaflet-container", timeout=10000)
    # Hacer clic en un punto desplazado del mapa para simular una distancia de entrega
    leaflet_map = page.locator(".leaflet-container")
    leaflet_map.click(position={"x": 100, "y": 80})
    checkout_page = CheckoutPage(page)
    checkout_page.confirm_delivery_map()


@when('the buyer confirms the searched delivery location on the map')
def buyer_confirms_searched_location(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.confirm_delivery_map()


@when('the buyer confirms the order')
def buyer_confirms_order(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.confirm_order()


@when(parsers.parse('the seller of "{slug}" logs in'))
def seller_logs_in(page: Page, shared_data, backend_api: APIUtils, slug: str):
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")
    seller_data = shared_data['seller_data']
    backend_api.inject_session_to_browser(page, seller_data)
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))


@when('the seller navigates to their business orders')
def seller_navigates_to_orders(page: Page, shared_data):
    slug = shared_data['slug']
    orders_page = BusinessOrdersPage(page)
    orders_page.go_to(slug)


@when('the seller opens the catalog editor')
def seller_opens_catalog_editor(page: Page, shared_data):
    slug = shared_data['slug']
    profile_page = ProfilePage(page)
    profile_page.go_to(slug)
    profile_page.open_catalog_editor()


@when('the seller unchecks the pickup delivery method')
def seller_unchecks_pickup_method(page: Page):
    profile_page = ProfilePage(page)
    if profile_page.is_delivery_pickup_checked():
        profile_page.toggle_delivery_pickup()


@when('the seller attempts to uncheck the delivery courier method')
def seller_attempts_uncheck_courier_method(page: Page):
    profile_page = ProfilePage(page)
    profile_page.toggle_delivery_courier()


@when('the seller saves the catalog configuration')
def seller_saves_catalog_config(page: Page):
    profile_page = ProfilePage(page)
    profile_page.save_catalog()


@when('the buyer cancels and closes the delivery map modal')
def buyer_cancels_delivery_map(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.cancel_delivery_map()


# =====================================================================
# THEN STEPS
# =====================================================================

@then('the confirm order button is disabled')
def confirm_order_btn_is_disabled(page: Page):
    checkout_page = CheckoutPage(page)
    assert checkout_page.is_confirm_button_disabled(), "El botón de confirmar pedido debería estar deshabilitado"


@then('the confirm order button is enabled')
def confirm_order_btn_is_enabled(page: Page):
    checkout_page = CheckoutPage(page)
    assert not checkout_page.is_confirm_button_disabled(), "El botón de confirmar pedido debería estar habilitado"


@then('the delivery location confirmed card is visible')
def delivery_location_confirmed_card_visible(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_delivery_confirmed_visible()


@then('the buyer sees order tracking with delivery fee')
def buyer_sees_tracking_with_delivery_fee(page: Page, shared_data):
    expect(page).to_have_url(re.compile(r".*/orden/.*"), timeout=10000)
    order_id = page.url.split("/")[-1]
    shared_data['order_id'] = order_id
    # Verificar que el badge Delivery esté visible en tracking
    expect(page.locator("text=/Delivery/i").first).to_be_visible(timeout=5000)
    expect(page.locator("text=/Inc\\. envío/i").first).to_be_visible(timeout=5000)


@then('the seller sees the order with delivery badge and map link')
def seller_sees_delivery_badge_and_map_link(page: Page, shared_data):
    order_id = shared_data['order_id']
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_delivery_info(order_id)
    orders_page.verify_delivery_map_link_visible(order_id)


@then('the business no location alert is displayed')
def business_no_location_alert_displayed(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_business_no_location_alert_visible()


@then('the business no location alert is not visible')
def business_no_location_alert_not_visible(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_business_no_location_alert_not_visible()


@then('the delivery map modal is not visible')
def delivery_map_modal_not_visible(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_delivery_map_not_visible()


@then(parsers.parse('the parent checkout form remains visible with customer name "{expected_name}"'))
def parent_checkout_form_remains_visible(page: Page, expected_name: str):
    name_input = page.locator("[data-testid='customer-name-input']")
    expect(name_input).to_be_visible(timeout=5000)
    expect(name_input).to_have_value(expected_name)


@then('the confirm order button remains disabled')
def confirm_order_btn_remains_disabled(page: Page):
    checkout_page = CheckoutPage(page)
    assert checkout_page.is_confirm_button_disabled(), "El botón de confirmar debe permanecer deshabilitado tras cancelar el mapa"


@then('the delivery courier method remains checked')
def delivery_courier_method_remains_checked(page: Page):
    profile_page = ProfilePage(page)
    assert profile_page.is_delivery_courier_checked(), "El checkbox de Delivery debe mantenerse marcado por el invariante de mínimo 1 método"


@then(parsers.parse('the delivery method select only contains "{expected_method}"'))
def delivery_method_select_only_contains(page: Page, expected_method: str):
    checkout_page = CheckoutPage(page)
    options = checkout_page.get_available_delivery_options()
    assert options == [expected_method], f"Se esperaba únicamente '{expected_method}', pero se encontró: {options}"


@then('the delivery distance is greater than straight line distance')
def delivery_distance_greater_than_straight_line(page: Page):
    checkout_page = CheckoutPage(page)
    page.wait_for_selector("[data-testid='delivery-distance-info']", timeout=10000)
    # Dar un instante para que el hook complete la consulta vial asíncrona
    page.wait_for_timeout(1000)
    dist = checkout_page.get_delivery_distance_value()
    # La distancia recta entre Obrajes y Sopocachi es ~3.64 km. Con factor 1.8x o OSRM es >= 6.0 km.
    assert dist >= 6.0, f"Se esperaba una distancia vial >= 6.0 km (con factor de sinuosidad 1.8x o OSRM), pero se obtuvo: {dist} km"


@then('the delivery fee reflects the urban circuity road factor')
def delivery_fee_reflects_circuity_factor(page: Page):
    checkout_page = CheckoutPage(page)
    fee = checkout_page.get_delivery_fee_value()
    # A 4.50 Bs/km, >= 6.0 km resulta en >= 27.00 Bs (frente a 16.38 Bs en línea recta)
    assert fee >= 27.0, f"Se esperaba una tarifa vial >= Bs 27.00 (a 4.50 Bs/km), pero se obtuvo: Bs {fee}"
