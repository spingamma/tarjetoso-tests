import os
import requests
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage

# Vincular escenarios de product_choices_config.feature
scenarios("../../../features/choices/product_choices_config.feature")


@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


# ---------------------------------------------------------
# GIVEN STEPS
# ---------------------------------------------------------
@given(parsers.parse('a seller is logged in with a premium business "{biz_name}" and slug "{slug}"'))
def seller_logged_in_with_premium_business(page: Page, shared_data: dict, backend_api: APIUtils, biz_name: str, slug: str):
    assert biz_name.endswith("Test"), f"Nombre '{biz_name}' debe terminar en 'Test'"
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    # 1. Crear vendedor
    seller_name = f"Dueño {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]
    backend_api.inject_session_to_browser(page, seller_data)

    # 2. Crear negocio
    biz_payload = {
        "name": biz_name,
        "title": "Negocio Config Complementos",
        "description": "Negocio de pruebas para configuración de choices",
        "slug": slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "payment_methods": '["efectivo"]',
        "orders_enabled": "false"
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

    # 3. Activar premium en DB
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE business_subscriptions SET premium = TRUE WHERE business_id = :bid"),
            {"bid": biz_id}
        )

    # 4. Crear un producto base para que el catálogo renderice sin esperar timeout
    backend_api.create_product_with_choices(
        api_context=api_context,
        slug=real_slug,
        name=f"Producto Inicial {biz_name}",
        token=seller_token,
        price="20.00",
        stock=10,
        expected_status=200,
    )

    shared_data["seller_token"] = seller_token
    shared_data["seller_data"] = seller_data
    shared_data["biz_id"] = biz_id
    shared_data["slug"] = real_slug

    # Navegar al perfil como dueño
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


# ---------------------------------------------------------
# WHEN STEPS
# ---------------------------------------------------------
@when('the seller opens the catalog editor and clicks add product')
def seller_opens_catalog_and_clicks_add(page: Page):
    profile_page = ProfilePage(page)
    profile_page.open_catalog_editor()
    profile_page.click_add_product()


@when('the seller clicks the add choice button')
def seller_clicks_add_choice(page: Page):
    profile_page = ProfilePage(page)
    profile_page.click_add_choice()


@when(parsers.parse('the seller types "{text}" in choice input {idx:d}'))
def seller_types_in_choice_input(page: Page, text: str, idx: int):
    profile_page = ProfilePage(page)
    profile_page.fill_choice_input(idx, text)


@when('the seller clicks the add choice button again')
def seller_clicks_add_choice_again(page: Page):
    profile_page = ProfilePage(page)
    profile_page.click_add_choice()


@when(parsers.parse('the seller removes choice {idx:d}'))
def seller_removes_choice(page: Page, idx: int):
    profile_page = ProfilePage(page)
    profile_page.remove_choice(idx)



@when(parsers.parse('the seller fills product name "{name}" and submits'))
def seller_fills_name_and_submits(page: Page, shared_data: dict, name: str):
    assert name.endswith("Test"), f"Nombre '{name}' debe terminar en 'Test'"
    profile_page = ProfilePage(page)
    profile_page.fill_product_name(name)
    profile_page.submit_product_form()
    shared_data["created_product_name"] = name


@when('the seller saves the catalog')
def seller_saves_catalog(page: Page):
    profile_page = ProfilePage(page)
    profile_page.save_catalog()



# ---------------------------------------------------------
# THEN STEPS
# ---------------------------------------------------------
@then('the product form modal is displayed with the "A elección" section')
def product_form_displayed_with_choices_section(page: Page):
    profile_page = ProfilePage(page)
    expect(profile_page.product_modal).to_be_visible(timeout=5000)
    expect(page.locator("text=/A elección/i").first).to_be_visible(timeout=5000)


@then('a choice input field appears')
def choice_input_field_appears(page: Page):
    input_first = page.locator("[data-testid='choice-input-0']")
    expect(input_first).to_be_visible(timeout=5000)


@then(parsers.parse('only 1 choice input remains with value "{expected_val}"'))
def only_one_choice_remains(page: Page, expected_val: str):
    inputs = page.locator("[data-testid^='choice-input-']")
    expect(inputs).to_have_count(1, timeout=5000)
    input_first = page.locator("[data-testid='choice-input-0']")
    expect(input_first).to_have_value(expected_val, timeout=5000)



@then(parsers.parse('the product is created with choices containing "{expected_choice}"'))
def product_created_with_choices(backend_api: APIUtils, shared_data: dict, expected_choice: str):
    real_slug = shared_data["slug"]
    seller_token = shared_data["seller_token"]
    prod_name = shared_data["created_product_name"]
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    res = requests.get(
        f"{base_url}/businesses/{real_slug}/products",
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok, f"Error listando productos: {res.text}"
    products = res.json()
    matched = next((p for p in products if p["name"] == prod_name), None)
    assert matched is not None, f"Producto '{prod_name}' no encontrado en el catálogo"
    assert matched.get("choices") is not None, f"El campo choices es None en el producto creado"
    assert expected_choice in matched["choices"], f"'{expected_choice}' no encontrado en choices: {matched['choices']}"
