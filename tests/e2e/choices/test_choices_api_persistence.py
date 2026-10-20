import os
import json
import pytest
import requests
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils

# Vincular escenarios de choices_api_persistence.feature
scenarios("../../../features/choices/choices_api_persistence.feature")


@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


# ---------------------------------------------------------
# GIVEN STEPS
# ---------------------------------------------------------
@given(parsers.parse('a premium business "{biz_name}" with slug "{slug}" is created via API'))
def premium_business_created_api(page: Page, shared_data: dict, backend_api: APIUtils, biz_name: str, slug: str):
    assert biz_name.endswith("Test"), f"Nombre '{biz_name}' debe terminar en 'Test'"
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    # 1. Crear usuario vendedor
    seller_name = f"Vendedor {biz_name}"
    seller_data = backend_api.create_e2e_user(api_context, name=seller_name, is_seller=True)
    seller_token = seller_data["access_token"]

    # 2. Crear negocio
    biz_payload = {
        "name": biz_name,
        "title": "Pizzería de Prueba",
        "description": "Negocio para pruebas de API de choices",
        "slug": slug,
        "category": "Pizzas & Pastas",
        "subcategories": '["Pizzas artesanales"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": seller_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "payment_methods": '["efectivo"]',
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

    # 3. Activar premium en DB
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE business_subscriptions SET premium = TRUE WHERE business_id = :bid"),
            {"bid": biz_id}
        )

    shared_data["seller_token"] = seller_token
    shared_data["biz_id"] = biz_id
    shared_data["slug"] = real_slug

    # 4. Crear usuario comprador para los pedidos
    buyer_name = f"Comprador {biz_name}"
    buyer_data = backend_api.create_e2e_user(api_context, name=buyer_name, is_seller=False)
    shared_data["buyer_token"] = buyer_data["access_token"]
    shared_data["buyer_data"] = buyer_data


# ---------------------------------------------------------
# WHEN STEPS
# ---------------------------------------------------------
@when(parsers.parse('a product "{prod_name}" is created with choices \'{choices_str}\' via API'))
def product_created_with_choices_api(page: Page, shared_data: dict, backend_api: APIUtils, prod_name: str, choices_str: str):
    assert prod_name.endswith("Test"), f"Nombre '{prod_name}' debe terminar en 'Test'"
    api_context = page.context.request
    real_slug = shared_data["slug"]
    seller_token = shared_data["seller_token"]

    response = backend_api.create_product_with_choices(
        api_context=api_context,
        slug=real_slug,
        name=prod_name,
        token=seller_token,
        price="60.00",
        stock=20,
        choices=choices_str,
        expected_status=200,
    )
    prod_data = response.json()
    shared_data["last_product"] = prod_data
    shared_data["product_id"] = prod_data["id"]
    shared_data["product_name"] = prod_name


@when(parsers.parse('a product "{prod_name}" is created without choices via API'))
def product_created_without_choices_api(page: Page, shared_data: dict, backend_api: APIUtils, prod_name: str):
    assert prod_name.endswith("Test"), f"Nombre '{prod_name}' debe terminar en 'Test'"
    api_context = page.context.request
    real_slug = shared_data["slug"]
    seller_token = shared_data["seller_token"]

    response = backend_api.create_product_with_choices(
        api_context=api_context,
        slug=real_slug,
        name=prod_name,
        token=seller_token,
        price="40.00",
        stock=20,
        choices=None,
        expected_status=200,
    )
    prod_data = response.json()
    shared_data["last_product"] = prod_data
    shared_data["product_id"] = prod_data["id"]
    shared_data["product_name"] = prod_name


@when('a product listing is fetched for the business')
def product_listing_fetched(shared_data: dict, backend_api: APIUtils):
    real_slug = shared_data["slug"]
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    res = requests.get(f"{base_url}/businesses/{real_slug}/products")
    assert res.ok
    shared_data["listed_products"] = res.json()


@when(parsers.parse('an order is created with selected_choices \'{selected_choices_str}\' for that product'))
def order_created_with_choices(page: Page, shared_data: dict, backend_api: APIUtils, selected_choices_str: str):
    api_context = page.context.request
    real_slug = shared_data["slug"]
    buyer_token = shared_data["buyer_token"]
    product_id = shared_data["product_id"]
    product_name = shared_data["product_name"]

    items = [
        {
            "product_id": product_id,
            "product_name": product_name,
            "quantity": 1,
            "price_at_time": 60.0,
            "subtotal": 60.0,
            "selected_choices": selected_choices_str,
        }
    ]

    response = backend_api.create_order(
        api_context=api_context,
        slug=real_slug,
        token=buyer_token,
        customer_name="Comprador API Choices Test",
        items=items,
        total_price=60.0,
        expected_status=200,
    )
    order_data = response.json()
    shared_data["last_order"] = order_data
    shared_data["order_id"] = order_data["id"]


@when('an order is created without selected_choices for that product')
def order_created_without_choices(page: Page, shared_data: dict, backend_api: APIUtils):
    api_context = page.context.request
    real_slug = shared_data["slug"]
    buyer_token = shared_data["buyer_token"]
    product_id = shared_data["product_id"]
    product_name = shared_data["product_name"]

    items = [
        {
            "product_id": product_id,
            "product_name": product_name,
            "quantity": 1,
            "price_at_time": 40.0,
            "subtotal": 40.0,
            "selected_choices": None,
        }
    ]

    response = backend_api.create_order(
        api_context=api_context,
        slug=real_slug,
        token=buyer_token,
        customer_name="Comprador Simple Test",
        items=items,
        total_price=40.0,
        expected_status=200,
    )
    order_data = response.json()
    shared_data["last_order"] = order_data
    shared_data["order_id"] = order_data["id"]


@when('the business orders are listed')
def business_orders_listed(shared_data: dict, backend_api: APIUtils):
    real_slug = shared_data["slug"]
    seller_token = shared_data["seller_token"]
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    res = requests.get(
        f"{base_url}/businesses/{real_slug}/orders",
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    assert res.ok
    shared_data["listed_orders"] = res.json()


# ---------------------------------------------------------
# THEN STEPS
# ---------------------------------------------------------
@then(parsers.parse('the product response contains choices \'{expected_choices}\''))
def product_response_contains_choices(shared_data: dict, expected_choices: str):
    product = shared_data["last_product"]
    assert product.get("choices") == expected_choices, (
        f"Esperaba choices '{expected_choices}', obtuvo '{product.get('choices')}'"
    )


@then('the product appears with non-null choices')
def product_appears_with_choices(shared_data: dict):
    product_id = shared_data["product_id"]
    products = shared_data["listed_products"]
    matched = next((p for p in products if p["id"] == product_id), None)
    assert matched is not None, f"Producto {product_id} no encontrado en listado"
    assert matched.get("choices") is not None, "El campo choices no debería ser None"


@then(parsers.parse('the order response item contains selected_choices \'{expected_selected}\''))
def order_response_item_contains_selected_choices(shared_data: dict, expected_selected: str):
    order = shared_data["last_order"]
    items = order.get("items", [])
    assert len(items) > 0, "La orden no contiene items"
    first_item = items[0]
    assert first_item.get("selected_choices") == expected_selected, (
        f"Esperaba selected_choices '{expected_selected}', obtuvo '{first_item.get('selected_choices')}'"
    )


@then(parsers.parse('the order item still contains selected_choices \'{expected_selected}\''))
def listed_order_item_contains_selected_choices(shared_data: dict, expected_selected: str):
    order_id = shared_data["order_id"]
    orders = shared_data["listed_orders"]
    matched = next((o for o in orders if o["id"] == order_id), None)
    assert matched is not None, f"Orden {order_id} no encontrada en listado del vendedor"
    items = matched.get("items", [])
    assert len(items) > 0
    first_item = items[0]
    assert first_item.get("selected_choices") == expected_selected, (
        f"Esperaba selected_choices '{expected_selected}', obtuvo '{first_item.get('selected_choices')}'"
    )


@then('the product response has null choices')
def product_response_has_null_choices(shared_data: dict):
    product = shared_data["last_product"]
    assert product.get("choices") is None or product.get("choices") == "", (
        f"Esperaba choices nulo, obtuvo '{product.get('choices')}'"
    )


@then('the order response item has null selected_choices')
def order_response_has_null_selected_choices(shared_data: dict):
    order = shared_data["last_order"]
    items = order.get("items", [])
    assert len(items) > 0
    first_item = items[0]
    assert first_item.get("selected_choices") is None or first_item.get("selected_choices") == "", (
        f"Esperaba selected_choices nulo, obtuvo '{first_item.get('selected_choices')}'"
    )
