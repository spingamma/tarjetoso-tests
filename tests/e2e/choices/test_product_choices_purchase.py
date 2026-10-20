import os
import json
import pytest
import requests
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage
from poms.choices_screen_page import ChoicesScreenPage
from poms.checkout_page import CheckoutPage
from poms.business_orders_page import BusinessOrdersPage

# Vincular escenarios de product_choices_purchase.feature
scenarios("../../../features/choices/product_choices_purchase.feature")


@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


# ---------------------------------------------------------
# GIVEN STEPS
# ---------------------------------------------------------
@given(parsers.parse('a premium business "{biz_name}" with slug "{slug}" exists via API'))
def premium_business_exists(page: Page, shared_data: dict, backend_api: APIUtils, biz_name: str, slug: str):
    assert biz_name.endswith("Test"), f"Nombre '{biz_name}' debe terminar en 'Test' por seguridad de Teardown"
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    # 1. Crear vendedor
    seller_name = f"Dueño {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]

    # 2. Crear negocio vía API
    biz_payload = {
        "name": biz_name,
        "title": "Restaurante de Hamburguesas",
        "description": "Negocio para pruebas E2E de complementos",
        "slug": slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "payment_methods": '["efectivo", "qr_simple"]',
        "orders_enabled": "true",
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

    # 3. Activar suscripción premium en DB
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE business_subscriptions SET premium = TRUE WHERE business_id = :bid"),
            {"bid": biz_id}
        )

    shared_data["seller_token"] = seller_token
    shared_data["seller_data"] = seller_data
    shared_data["biz_id"] = biz_id
    shared_data["slug"] = real_slug


@given(parsers.parse('orders are enabled for "{slug}"'))
def orders_are_enabled_for_business(shared_data: dict):
    # Verificado: el negocio se crea con orders_enabled = "true" en el setup inicial
    assert "slug" in shared_data


@given(parsers.parse('a product "{prod_name}" with choices \'{choices_str}\' exists for "{slug}"'))
def product_with_choices_exists(page: Page, shared_data: dict, backend_api: APIUtils, prod_name: str, choices_str: str, slug: str):
    assert prod_name.endswith("Test"), f"Nombre '{prod_name}' debe terminar en 'Test'"
    api_context = page.context.request
    seller_token = shared_data["seller_token"]
    real_slug = shared_data["slug"]

    response = backend_api.create_product_with_choices(
        api_context=api_context,
        slug=real_slug,
        name=prod_name,
        token=seller_token,
        price="45.00",
        stock=50,
        choices=choices_str,
        expected_status=200,
    )
    prod_data = response.json()
    shared_data["product_id"] = prod_data["id"]
    shared_data["product_name"] = prod_name
    shared_data["product_choices"] = choices_str


@given(parsers.parse('a product "{prod_name}" without choices exists for "{slug}"'))
def product_without_choices_exists(page: Page, shared_data: dict, backend_api: APIUtils, prod_name: str, slug: str):
    assert prod_name.endswith("Test"), f"Nombre '{prod_name}' debe terminar en 'Test'"
    api_context = page.context.request
    seller_token = shared_data["seller_token"]
    real_slug = shared_data["slug"]

    response = backend_api.create_product_with_choices(
        api_context=api_context,
        slug=real_slug,
        name=prod_name,
        token=seller_token,
        price="30.00",
        stock=50,
        choices=None,
        expected_status=200,
    )
    prod_data = response.json()
    shared_data["product_id"] = prod_data["id"]
    shared_data["product_name"] = prod_name
    shared_data["product_choices"] = None


@given('a buyer user is logged in')
def buyer_user_logged_in(page: Page, shared_data: dict, backend_api: APIUtils):
    api_context = page.context.request
    buyer_name = f"Buyer User Test"
    buyer_data = backend_api.create_e2e_user(api_context, name=buyer_name, is_seller=False)
    backend_api.inject_session_to_browser(page, buyer_data)
    shared_data["buyer_token"] = buyer_data["access_token"]
    shared_data["buyer_data"] = buyer_data


# ---------------------------------------------------------
# WHEN STEPS
# ---------------------------------------------------------
@when(parsers.parse('the buyer navigates to the "{slug}" profile'))
def buyer_navigates_to_profile(page: Page, shared_data: dict, slug: str):
    real_slug = shared_data.get("slug", slug)
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


@when(parsers.parse('the buyer adds "{prod_name}" to the cart'))
def buyer_adds_product_to_cart(page: Page, shared_data: dict, prod_name: str):
    product_id = shared_data.get("product_id")
    profile_page = ProfilePage(page)
    if product_id:
        profile_page.add_to_cart(product_id)
    else:
        profile_page.add_random_product_to_cart()


@when('the buyer clicks the order button')
def buyer_clicks_order_button(page: Page):
    profile_page = ProfilePage(page)
    profile_page.go_to_checkout()


@when(parsers.parse('the buyer selects "{choice1}" and "{choice2}" as choices'))
def buyer_selects_two_choices(page: Page, choice1: str, choice2: str):
    choices_page = ChoicesScreenPage(page)
    choices_page.toggle_choice(choice1)
    choices_page.toggle_choice(choice2)


@when(parsers.parse('the buyer selects "{choice}" and then deselects "{choice}"'))
def buyer_selects_and_deselects_choice(page: Page, choice: str):
    choices_page = ChoicesScreenPage(page)
    choices_page.toggle_choice(choice)
    # Segundo click para deseleccionar
    choices_page.toggle_choice(choice)


@when('the buyer clicks "Continuar al Pedido"')
def buyer_clicks_continue_to_order(page: Page):
    choices_page = ChoicesScreenPage(page)
    choices_page.continue_to_order()


@when(parsers.parse('the buyer completes the checkout with name "{customer_name}" and payment "{payment_method}"'))
def buyer_completes_checkout(page: Page, shared_data: dict, customer_name: str, payment_method: str):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_page_loaded()
    checkout_page.fill_customer_name(customer_name)
    checkout_page.confirm_order()


@when(parsers.parse('the seller of "{slug}" logs in and views their orders'))
def seller_logs_in_and_views_orders(page: Page, shared_data: dict, backend_api: APIUtils, slug: str):
    seller_data = shared_data["seller_data"]
    real_slug = shared_data.get("slug", slug)
    backend_api.inject_session_to_browser(page, seller_data)
    orders_page = BusinessOrdersPage(page)
    orders_page.go_to(real_slug)


# ---------------------------------------------------------
# THEN STEPS
# ---------------------------------------------------------
@then('the choices screen is displayed with title "Complementos de tu Pedido"')
def choices_screen_is_displayed(page: Page):
    choices_page = ChoicesScreenPage(page)
    choices_page.verify_page_loaded()


@then(parsers.parse('the product "{prod_name}" shows {count:d} choice options'))
def product_shows_choice_options(page: Page, shared_data: dict, prod_name: str, count: int):
    choices_page = ChoicesScreenPage(page)
    actual_count = choices_page.count_choices_for_product()
    assert actual_count == count, f"Esperaba {count} opciones de complementos, encontradas {actual_count}"


@then(parsers.parse('the selection counter shows "{expected_text}"'))
def selection_counter_shows(page: Page, expected_text: str):
    choices_page = ChoicesScreenPage(page)
    counter_text = choices_page.get_selection_counter_text()
    assert expected_text in counter_text, f"Esperaba '{expected_text}' en el contador, obtuvo '{counter_text}'"


@then(parsers.parse('the checkout screen displays "{choice1}" and "{choice2}" in the order summary'))
def checkout_displays_choices(page: Page, choice1: str, choice2: str):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_page_loaded()
    checkout_page.verify_choices_displayed(choice1, choice2)


@then('the checkout screen shows no choices in the order summary')
def checkout_shows_no_choices(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_page_loaded()
    checkout_page.verify_no_choices_displayed()


@then('the buyer is navigated directly to the checkout screen')
def navigated_directly_to_checkout(page: Page):
    checkout_page = CheckoutPage(page)
    checkout_page.verify_page_loaded()
    import re
    expect(page).to_have_url(re.compile(r"/orden$"))



@then('the order is created successfully')
def order_is_created_successfully(page: Page, shared_data: dict):
    # La navegación redirige a /perfil/:slug/orden/:order_id
    page.wait_for_url(lambda u: "/orden/" in u, timeout=15000)
    current_url = page.url
    order_id = current_url.split("/orden/")[-1].split("?")[0].strip()
    shared_data["order_id"] = order_id
    assert order_id, "No se pudo extraer el order_id de la URL"


@then('the order item has no selected choices')
def order_item_has_no_choices(backend_api: APIUtils, shared_data: dict):
    real_slug = shared_data["slug"]
    seller_token = shared_data["seller_token"]
    order_id = shared_data["order_id"]
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    res = requests.get(
        f"{base_url}/businesses/{real_slug}/orders",
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok

    orders = res.json()
    matched_order = next((o for o in orders if o["id"] == order_id), None)
    if matched_order:
        for item in matched_order.get("items", []):
            assert item.get("selected_choices") is None or item.get("selected_choices") == "" or item.get("selected_choices") == "[]", (
                f"Expected no selected_choices, got {item.get('selected_choices')}"
            )


@then(parsers.parse('the order item shows "{choice1}" and "{choice2}" as selected choices'))
def seller_sees_order_choices(page: Page, shared_data: dict, choice1: str, choice2: str):
    order_id = shared_data["order_id"]
    orders_page = BusinessOrdersPage(page)
    orders_page.verify_order_choices(order_id, choice1, choice2)
