import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
import os
import re
import json
import uuid
import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage
from poms.directory_page import DirectoryPage
from poms.business_orders_page import BusinessOrdersPage

scenarios('../../features/freemium_premium_plans.feature')

@pytest.fixture
def shared_data():
    return {}

@pytest.fixture
def backend_api():
    return APIUtils()

@pytest.fixture(autouse=True)
def cleanup_freemium_test_data():
    yield
    # Clean up test data after each test
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    try:
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM interactions WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Test%')"))
            conn.execute(text("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Test%'))"))
            conn.execute(text("DELETE FROM orders WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Test%')"))
            conn.execute(text("DELETE FROM products WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Test%') OR name LIKE '%Test%'"))
            conn.execute(text("DELETE FROM business_subscriptions WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Test%')"))
            conn.execute(text("DELETE FROM business_specialties WHERE business_id IN (SELECT id FROM businesses WHERE name LIKE '%Test%')"))
            conn.execute(text("DELETE FROM businesses WHERE name LIKE '%Test%'"))
            conn.execute(text("DELETE FROM users WHERE email LIKE '%@test.com' OR name LIKE '%Test%'"))
    except Exception as e:
        print(f"Error during teardown: {e}")


def _create_test_business_with_products(page: Page, backend_api: APIUtils, biz_name: str, slug: str, product_count: int, is_premium: bool, is_expired: bool = False):
    api_context = page.context.request
    owner_data = backend_api.create_e2e_user(api_context, name=f"Dueño {biz_name}", is_seller=True)
    owner_token = owner_data["access_token"]
    
    base_url = backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    
    unique_suffix = uuid.uuid4().hex[:4]
    requested_slug = f"{slug}-{unique_suffix}"
    
    biz_payload = {
        "name": f"{biz_name} {unique_suffix}",
        "title": "Comercio",
        "description": "Comercio para pruebas Freemium vs Premium",
        "slug": requested_slug,
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": owner_data["email"],
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
    
    # Crear productos para el negocio
    for i in range(1, product_count + 1):
        prod_payload = {
            "name": f"Producto {i} {biz_name} {unique_suffix}",
            "description": f"Descripción del producto {i}",
            "price": str(10.0 + i * 5),
            "is_visible": "true",
            "stock": "100"
        }
        prod_res = requests.post(
            f"{base_url}/businesses/{final_slug}/products",
            data=prod_payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert prod_res.ok, f"Error creando producto {i}: {prod_res.text}"

    # Ajustar suscripción en BD de acuerdo al plan
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        if is_expired:
            conn.execute(text("""
                UPDATE business_subscriptions 
                SET premium = TRUE, 
                    plan_months = 1, 
                    expiration_date = NOW() - INTERVAL '10 days'
                WHERE business_id = :bid
            """), {"bid": biz_id})
        elif not is_premium:
            conn.execute(text("""
                UPDATE business_subscriptions 
                SET premium = FALSE, 
                    plan_months = NULL, 
                    expiration_date = NULL
                WHERE business_id = :bid
            """), {"bid": biz_id})
        else:
            conn.execute(text("""
                UPDATE business_subscriptions 
                SET premium = TRUE, 
                    plan_months = 3, 
                    expiration_date = NOW() + INTERVAL '90 days'
                WHERE business_id = :bid
            """), {"bid": biz_id})
            
    return {
        "id": biz_id,
        "name": biz_payload["name"],
        "slug": final_slug,
        "owner_token": owner_token,
        "owner_data": owner_data
    }


@given(parsers.parse('a free tier business exists with name "{biz_name}" and slug "{slug}" with {count:d} products'))
def given_free_business(page: Page, shared_data, backend_api: APIUtils, biz_name: str, slug: str, count: int):
    info = _create_test_business_with_products(page, backend_api, biz_name, slug, count, is_premium=False)
    shared_data["free_biz"] = info
    shared_data[slug] = info


@given(parsers.parse('a premium tier business exists with name "{biz_name}" and slug "{slug}" with {count:d} products'))
def given_premium_business(page: Page, shared_data, backend_api: APIUtils, biz_name: str, slug: str, count: int):
    info = _create_test_business_with_products(page, backend_api, biz_name, slug, count, is_premium=True)
    shared_data["premium_biz"] = info
    shared_data[slug] = info


@given(parsers.parse('an expired tier business exists with name "{biz_name}" and slug "{slug}" with {count:d} products'))
def given_expired_business(page: Page, shared_data, backend_api: APIUtils, biz_name: str, slug: str, count: int):
    info = _create_test_business_with_products(page, backend_api, biz_name, slug, count, is_premium=True, is_expired=True)
    shared_data["expired_biz"] = info
    shared_data[slug] = info


@when(parsers.parse('a public visitor navigates to the public profile of "{slug}"'))
def public_visitor_navigates_to_profile(page: Page, shared_data, slug: str):
    info = shared_data[slug]
    actual_slug = info["slug"]
    
    # Asegurar sesión limpia de visitante
    page.goto("about:blank")
    base_url_front = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(base_url_front)
    page.evaluate("localStorage.clear();")
    
    profile = ProfilePage(page)
    profile.go_to(actual_slug)
    shared_data["current_profile"] = profile


@then(parsers.parse('the public visitor sees exactly {count:d} products in the catalog'))
def public_visitor_sees_exact_product_count(page: Page, shared_data, count: int):
    profile: ProfilePage = shared_data["current_profile"]
    unique_names = profile.get_unique_product_names()
    assert len(unique_names) == count, f"Se esperaban {count} productos en el catálogo público, pero se encontraron {len(unique_names)} (Nombres: {unique_names})"


@when(parsers.parse('the owner of "{slug}" navigates to "Mis Negocios"'))
def owner_navigates_to_my_businesses(page: Page, shared_data, slug: str):
    info = shared_data[slug]
    owner_token = info["owner_token"]
    owner_data = info["owner_data"]
    
    base_url_front = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(base_url_front)
    page.evaluate(f"localStorage.setItem('spingamma_token', '{owner_token}');")
    page.evaluate(
        "([key, value]) => localStorage.setItem(key, value)",
        ["spingamma_user", json.dumps(owner_data)]
    )
    page.goto(f"{base_url_front}/mis-negocios")
    page.wait_for_load_state("networkidle")


@then('the owner sees the business listed with the "Plan Gratuito" badge')
def owner_sees_free_plan_badge(page: Page, shared_data):
    # Validar que el badge 'Plan Gratuito' esté visible en la tarjeta del negocio
    expect(page.locator("text=/Plan Gratuito/i").first).to_be_visible(timeout=10000)


@then('the owner sees the business listed with the "Plan Premium" badge and expiration info')
def owner_sees_premium_plan_badge(page: Page, shared_data):
    # Validar que el badge '⭐ Plan Premium' esté visible en la tarjeta del negocio
    expect(page.locator("text=/Plan Premium/i").first).to_be_visible(timeout=10000)


@when(parsers.parse('a public visitor searches for "{query}" in the directory'))
def public_visitor_searches_directory(page: Page, shared_data, query: str):
    base_url_front = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(base_url_front)
    page.evaluate("localStorage.clear();")
    
    directory = DirectoryPage(page)
    directory.go_to()
    
    # Buscar usando el nombre base o slug
    directory.search_by_text(query)
    shared_data["directory_page"] = directory


@then(parsers.parse('the business "{slug}" appears in the search results'))
def business_appears_in_search_results(page: Page, shared_data, slug: str):
    info = shared_data[slug]
    biz_name = info["name"]
    expect(page.locator(f"text=/{biz_name}/i").first).to_be_visible(timeout=10000)


@then('the public profile loads successfully without 403 error')
def public_profile_loads_no_403(page: Page, shared_data):
    expect(page.locator("text=/403|Acceso Denegado|No disponible/i")).not_to_be_visible()
    profile: ProfilePage = shared_data["current_profile"]
    profile.verify_page_loaded()


@when(parsers.parse('the owner of "{slug}" navigates to the orders panel of "{slug_ref}"'))
def owner_navigates_to_orders_panel(page: Page, shared_data, slug: str, slug_ref: str):
    info = shared_data[slug]
    actual_slug = info["slug"]
    owner_token = info["owner_token"]
    owner_data = info["owner_data"]
    
    base_url_front = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
    page.goto(base_url_front)
    page.evaluate(f"localStorage.setItem('spingamma_token', '{owner_token}');")
    page.evaluate(
        "([key, value]) => localStorage.setItem(key, value)",
        ["spingamma_user", json.dumps(owner_data)]
    )
    
    bo = BusinessOrdersPage(page)
    bo.go_to(actual_slug)
    shared_data["bo_page"] = bo


@then('the owner sees the premium lock screen')
def owner_sees_premium_lock_screen(page: Page, shared_data):
    expect(page.locator("text=/Gestión de Pedidos Premium/i").first).to_be_visible(timeout=10000)
    expect(page.locator("[data-testid='activate-premium-orders-btn']")).to_be_visible()
