import os
import requests
from datetime import datetime, timedelta
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage

scenarios("../../features/independent_catalog.feature")

@pytest.fixture
def catalog_state():
    return {}

@pytest.fixture
def backend_api():
    return APIUtils()


@given(parsers.parse('an owner user is logged in with a premium business "{biz_name}" and slug "{slug}"'))
def owner_logged_in_with_business(page: Page, backend_api: APIUtils, catalog_state: dict, biz_name: str, slug: str):
    assert biz_name.endswith("Test"), f"Nombre '{biz_name}' debe terminar con 'Test'"
    api_context = page.context.request

    # 1. Crear usuario vendedor
    seller_name = f"Dueño {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]
    backend_api.inject_session_to_browser(page, seller_data)

    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")

    # 2. Crear negocio
    biz_payload = {
        "name": biz_name,
        "title": "Especialidad Hamburguesas",
        "description": "Negocio para pruebas de catálogo independiente",
        "slug": slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "payment_methods": '["efectivo"]',
        "orders_enabled": "true"
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

    # 3. Crear producto de prueba
    prod_payload = {
        "name": f"Producto {biz_name}",
        "price": 25.00,
        "stock": 50,
        "catalog_name": "General",
        "is_visible": True
    }
    res_prod = requests.post(
        f"{base_url}/businesses/{real_slug}/products",
        data=prod_payload,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res_prod.ok, f"Error creando producto: {res_prod.text}"

    # 4. Activar plan premium en DB
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET is_admin = TRUE WHERE id = :id"), {"id": seller_data["id"]})
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {
            "bid": biz_id,
            "exp": (datetime.now() + timedelta(days=365)).isoformat()
        })

    catalog_state["biz_id"] = biz_id
    catalog_state["slug"] = real_slug
    catalog_state["seller_token"] = seller_token


@when(parsers.parse('the owner visits their business profile "{slug}"'))
def owner_visits_profile(page: Page, catalog_state: dict, slug: str):
    real_slug = catalog_state.get("slug", slug)
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)
    catalog_state["profile_page"] = profile_page


@when('clicks the "Edita tu menú aquí" button')
@when('clicks the "Edita tu catálogo" button')
def click_open_catalog(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    profile_page.open_catalog_editor()


@then("the catalog edit modal is displayed with independent save action")
def verify_catalog_modal_displayed(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    expect(profile_page.catalog_modal).to_be_visible(timeout=5000)
    expect(profile_page.save_catalog_btn).to_be_visible(timeout=5000)


@when("the owner updates catalog settings and clicks save catalog")
def update_catalog_and_save(page: Page, catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]

    # Adjuntar dummy QR para cumplir la validación de guardado si pedidos está activo
    dummy_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    page.evaluate(f"""
        const dt = new DataTransfer();
        fetch('{dummy_base64}')
          .then(res => res.blob())
          .then(blob => {{
              const file = new File([blob], 'dummy_qr.png', {{ type: 'image/png' }});
              dt.items.add(file);
              const input = document.querySelector("[data-testid='payment-qr-file-input']");
              if (input) {{
                  input.files = dt.files;
                  input.dispatchEvent(new Event('change', {{ bubbles: true }}));
              }}
          }});
    """)
    page.wait_for_timeout(500)

    # Click en guardar catálogo
    profile_page.save_catalog()


@then("the catalog modal closes and the public catalog reflects the updated state")
def verify_catalog_modal_closed(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    expect(profile_page.catalog_modal).not_to_be_visible(timeout=10000)
    expect(profile_page.open_inventory_btn).to_be_visible(timeout=5000)


@when('the owner clicks the add product button')
def click_add_product(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    profile_page.click_add_product()


@then('the product form modal is displayed')
def verify_product_modal_displayed(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    expect(profile_page.product_modal).to_be_visible(timeout=5000)


@when('the owner clicks cancel on the product form')
def cancel_product_form(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    profile_page.cancel_product_form()


@then('the product form modal is closed')
def verify_product_modal_closed(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    expect(profile_page.product_modal).not_to_be_visible(timeout=5000)


@then('the catalog edit modal remains open and functional')
def verify_catalog_modal_remains_open(catalog_state: dict):
    profile_page: ProfilePage = catalog_state["profile_page"]
    expect(profile_page.catalog_modal).to_be_visible(timeout=5000)
    expect(profile_page.add_product_btn).to_be_visible(timeout=5000)

