import os
import uuid
import requests
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage

scenarios("../../features/product_visibility.feature")

@pytest.fixture
def visibility_state():
    return {}

@pytest.fixture
def backend_api():
    return APIUtils()


@given(parsers.parse('an owner user is logged in with a business "{biz_name}" and slug "{slug}" having product "{prod_name}"'))
def owner_logged_in_with_business_and_product(page: Page, backend_api: APIUtils, visibility_state: dict, biz_name: str, slug: str, prod_name: str):
    assert biz_name.endswith("Test"), f"Nombre de negocio '{biz_name}' debe terminar con 'Test'"
    assert prod_name.endswith("Test"), f"Nombre de producto '{prod_name}' debe terminar con 'Test'"

    api_context = page.context.request
    rand_suffix = uuid.uuid4().hex[:6]
    unique_biz_name = f"Visib {rand_suffix} Test"
    unique_slug = f"{slug}-{rand_suffix}"

    # 1. Crear usuario vendedor
    seller_name = f"D {rand_suffix} Test"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]
    backend_api.inject_session_to_browser(page, seller_data)

    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    # 2. Crear negocio
    biz_payload = {
        "name": unique_biz_name,
        "description": "Negocio para prueba E2E de alternador de visibilidad de productos",
        "slug": unique_slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "La Paz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "orders_enabled": "true"
    }
    res_biz = requests.post(
        f"{base_url}/businesses/",
        data=biz_payload,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res_biz.ok, f"Error creando negocio: {res_biz.text}"
    biz_data = res_biz.json()
    biz_id = biz_data["id"]
    real_slug = biz_data["slug"]

    # 3. Crear producto de prueba visible
    unique_prod_name = f"{prod_name} {rand_suffix}"
    prod_payload = {
        "name": unique_prod_name,
        "price": "50.00",
        "description": "Descripción del producto de prueba de visibilidad",
        "carousel_name": "Catálogo",
        "is_visible": True
    }
    res_prod = requests.post(
        f"{base_url}/businesses/{real_slug}/products",
        data=prod_payload,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res_prod.ok, f"Error creando producto: {res_prod.text}"
    prod_data = res_prod.json()
    prod_id = prod_data["id"]

    visibility_state["base_url"] = base_url
    visibility_state["biz_id"] = biz_id
    visibility_state["slug"] = real_slug
    visibility_state["prod_id"] = prod_id
    visibility_state["prod_name"] = unique_prod_name
    visibility_state["seller_token"] = seller_token


@when(parsers.parse('the owner visits their business profile "{slug}"'))
def owner_visits_profile(page: Page, visibility_state: dict, slug: str):
    real_slug = visibility_state.get("slug", slug)
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)
    visibility_state["profile_page"] = profile_page


@then("the product card is displayed in the catalog with a visible toggle icon")
def verify_product_displayed_with_toggle(visibility_state: dict):
    profile_page: ProfilePage = visibility_state["profile_page"]
    prod_id = visibility_state["prod_id"]

    toggle_btn = profile_page.get_product_visibility_toggle(prod_id)
    expect(toggle_btn).to_be_visible(timeout=10000)

    hidden_badge = profile_page.get_hidden_badge(prod_id)
    expect(hidden_badge).not_to_be_visible(timeout=3000)


@when(parsers.parse('the owner clicks the visibility toggle on product "{prod_name}"'))
def owner_clicks_visibility_toggle(visibility_state: dict, prod_name: str):
    profile_page: ProfilePage = visibility_state["profile_page"]
    prod_id = visibility_state["prod_id"]
    profile_page.toggle_product_visibility(prod_id)


@then("the product card displays the hidden badge and dimmed status for the owner")
def verify_hidden_badge_displayed_for_owner(visibility_state: dict):
    profile_page: ProfilePage = visibility_state["profile_page"]
    prod_id = visibility_state["prod_id"]

    hidden_badge = profile_page.get_hidden_badge(prod_id)
    expect(hidden_badge).to_be_visible(timeout=10000)


@then("the owner API endpoint confirms the product has is_visible false")
def verify_owner_api_returns_product_hidden(visibility_state: dict):
    base_url = visibility_state["base_url"]
    slug = visibility_state["slug"]
    prod_id = visibility_state["prod_id"]
    seller_token = visibility_state["seller_token"]

    res = requests.get(
        f"{base_url}/businesses/{slug}/products",
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok, f"Error en GET de productos del dueño: {res.text}"
    products = res.json()
    assert len(products) == 1, f"Se esperaba 1 producto para el dueño, se recibieron {len(products)}"
    assert products[0]["id"] == prod_id
    assert products[0]["is_visible"] is False, "El producto debería tener is_visible: False"


@then("the public API endpoint returns 0 products for visitors")
def verify_public_api_returns_no_products(visibility_state: dict):
    base_url = visibility_state["base_url"]
    slug = visibility_state["slug"]

    res = requests.get(f"{base_url}/businesses/{slug}/products")
    assert res.ok, f"Error en GET anónimo de productos: {res.text}"
    products = res.json()
    assert len(products) == 0, f"Visitante público no debería ver productos ocultos, recibió {len(products)}"


@then(parsers.parse('an anonymous visitor viewing profile "{slug}" does not see the product in the catalog'))
def verify_anonymous_visitor_does_not_see_product(page: Page, visibility_state: dict, slug: str):
    real_slug = visibility_state.get("slug", slug)
    prod_name = visibility_state["prod_name"]

    anon_context = page.context.browser.new_context()
    anon_page = anon_context.new_page()
    try:
        anon_profile = ProfilePage(anon_page)
        anon_profile.go_to(real_slug)
        assert not anon_profile.is_product_visible_in_catalog(prod_name), f"El producto '{prod_name}' no debería ser visible para visitantes"
    finally:
        anon_context.close()


@when(parsers.parse('the owner clicks the visibility toggle again on product "{prod_name}"'))
def owner_clicks_toggle_again(visibility_state: dict, prod_name: str):
    profile_page: ProfilePage = visibility_state["profile_page"]
    prod_id = visibility_state["prod_id"]
    profile_page.toggle_product_visibility(prod_id)


@then("the product card removes the hidden badge and restores active status")
def verify_hidden_badge_removed(visibility_state: dict):
    profile_page: ProfilePage = visibility_state["profile_page"]
    prod_id = visibility_state["prod_id"]

    hidden_badge = profile_page.get_hidden_badge(prod_id)
    expect(hidden_badge).not_to_be_visible(timeout=10000)


@then("the owner API endpoint confirms the product has is_visible true")
def verify_owner_api_returns_product_visible(visibility_state: dict):
    base_url = visibility_state["base_url"]
    slug = visibility_state["slug"]
    prod_id = visibility_state["prod_id"]
    seller_token = visibility_state["seller_token"]

    res = requests.get(
        f"{base_url}/businesses/{slug}/products",
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok, f"Error en GET de productos del dueño: {res.text}"
    products = res.json()
    assert len(products) == 1
    assert products[0]["id"] == prod_id
    assert products[0]["is_visible"] is True, "El producto debería tener is_visible: True"


@then("the public API endpoint returns 1 product for visitors")
def verify_public_api_returns_one_product(visibility_state: dict):
    base_url = visibility_state["base_url"]
    slug = visibility_state["slug"]
    prod_id = visibility_state["prod_id"]

    res = requests.get(f"{base_url}/businesses/{slug}/products")
    assert res.ok, f"Error en GET anónimo de productos: {res.text}"
    products = res.json()
    assert len(products) == 1, f"Visitante público debería ver 1 producto restaurado, recibió {len(products)}"
    assert products[0]["id"] == prod_id


@then(parsers.parse('an anonymous visitor viewing profile "{slug}" sees the product in the catalog'))
def verify_anonymous_visitor_sees_product(page: Page, visibility_state: dict, slug: str):
    real_slug = visibility_state.get("slug", slug)
    prod_name = visibility_state["prod_name"]

    anon_context = page.context.browser.new_context()
    anon_page = anon_context.new_page()
    try:
        anon_profile = ProfilePage(anon_page)
        anon_profile.go_to(real_slug)
        expect(anon_page.locator(f".snap-center h4:has-text('{prod_name}')").first).to_be_visible(timeout=10000)
    finally:
        anon_context.close()
