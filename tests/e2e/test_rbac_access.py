import os
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from utils.api_testing import APIUtils

# Vincular el archivo feature
scenarios("../../features/rbac_access.feature")

@pytest.fixture
def rbac_state():
    """Estado compartido para almacenar info del usuario actual."""
    return {}

@pytest.fixture
def backend_api():
    """Fixture para interactuar con la API del backend."""
    return APIUtils()

@given(parsers.parse('a normal client user "{name}" is logged in'))
def login_normal_user(page: Page, backend_api: APIUtils, name: str, rbac_state: dict):
    user_data = backend_api.create_e2e_user(page.context.request, name, is_seller=False, is_admin=False)
    backend_api.inject_session_to_browser(page, user_data)
    rbac_state["user_type"] = "client"
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(base_url)
    page.wait_for_load_state("networkidle")

@given(parsers.parse('a seller user "{name}" is logged in'))
def login_seller_user(page: Page, backend_api: APIUtils, name: str, rbac_state: dict):
    user_data = backend_api.create_e2e_user(page.context.request, name, is_seller=True, is_admin=False)
    backend_api.inject_session_to_browser(page, user_data)
    rbac_state["user_type"] = "seller"
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(base_url)
    page.wait_for_load_state("networkidle")

@given(parsers.parse('an admin user "{name}" is logged in'))
def login_admin_user(page: Page, backend_api: APIUtils, name: str, rbac_state: dict):
    user_data = backend_api.create_e2e_user(page.context.request, name, is_seller=True, is_admin=True)
    backend_api.inject_session_to_browser(page, user_data)
    rbac_state["user_type"] = "admin"
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(base_url)
    page.wait_for_load_state("networkidle")

@when("the user opens the user menu")
def open_user_menu(page: Page):
    try:
        # Buscamos el botón del usuario en el Header. 
        # Sabemos que tiene el texto "Hola,"
        menu_btn = page.locator("button:has-text('Hola,')").first
        menu_btn.click()
    except Exception as e:
        print(f"Error al abrir menú: {e}")

@then("the user should not see the admin or seller panel buttons")
def no_admin_or_seller_panels(page: Page):
    expect(page.locator("text=Panel Admin").first).not_to_be_visible(timeout=2000)
    expect(page.locator("text=Panel Ventas").first).not_to_be_visible(timeout=2000)

@then("the user should see the \"Panel Ventas\" button")
def see_panel_ventas(page: Page):
    expect(page.locator("text=Panel Ventas").first).to_be_visible(timeout=5000)

@when("the user clicks the \"Panel Ventas\" button")
def click_panel_ventas(page: Page):
    page.locator("text=Panel Ventas").first.click()
    page.wait_for_load_state("networkidle")
    
import re

@then("the user should see seller specific tabs")
def see_seller_tabs(page: Page):
    expect(page).to_have_url(re.compile(r".*/admin.*"))
    # Validamos que vea "Negocios"
    expect(page.locator("button, a").filter(has_text="Negocios").first).to_be_visible()

@then("the user should not see full admin tabs")
def no_full_admin_tabs(page: Page):
    # Validamos que tabs exclusivos de Admin no existan
    expect(page.locator("button, a").filter(has_text="Usuarios").first).not_to_be_visible(timeout=2000)

@then("the user should see the \"Panel Admin\" button")
def see_panel_admin(page: Page):
    expect(page.locator("text=Panel Admin").first).to_be_visible(timeout=5000)

@when("the user clicks the \"Panel Admin\" button")
def click_panel_admin(page: Page):
    page.locator("text=Panel Admin").first.click()
    page.wait_for_load_state("networkidle")

@then("the user should see full admin tabs")
def see_full_admin_tabs(page: Page):
    expect(page).to_have_url(re.compile(r".*/admin.*"))
    # Validamos que vea "Usuarios"
    expect(page.locator("button, a").filter(has_text="Usuarios").first).to_be_visible()


import requests
from poms.profile_page import ProfilePage

@given(parsers.parse('a premium business exists with name "{biz_name}" and slug "{slug}"'))
def create_profile_rbac_business(page: Page, rbac_state: dict, backend_api: APIUtils, biz_name: str, slug: str):
    assert biz_name.endswith("Test"), f"Nombre del negocio '{biz_name}' debe terminar con 'Test'"
    api_context = page.context.request
    
    seller_name = f"Dueño {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]
    
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    
    biz_payload = {
        "name": biz_name,
        "title": "Restaurante RBAC",
        "description": "Negocio para pruebas RBAC de perfil",
        "slug": slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"]
    }
    res = requests.post(
        f"{base_url}/businesses/",
        data=biz_payload,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok, f"Error creando negocio: {res.text}"
    biz_data = res.json()
    rbac_state["biz_id"] = biz_data["id"]
    rbac_state["slug"] = biz_data["slug"]


@when(parsers.parse('an anonymous visitor goes to "{slug}" profile'))
def anonymous_visits_profile(page: Page, rbac_state: dict, slug: str):
    # Asegurar sesión anónima (limpiar localStorage y cookies)
    page.context.clear_cookies()
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    
    real_slug = rbac_state.get("slug", slug)
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)
    rbac_state["profile_page"] = profile_page


@then("the visitor should not see the edit profile button or edit catalog button")
def verify_no_owner_controls(page: Page, rbac_state: dict):
    profile_page: ProfilePage = rbac_state.get("profile_page") or ProfilePage(page)
    expect(profile_page.edit_profile_btn).not_to_be_visible(timeout=3000)
    expect(profile_page.open_inventory_btn).not_to_be_visible(timeout=3000)

