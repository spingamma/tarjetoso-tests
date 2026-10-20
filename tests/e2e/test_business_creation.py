import os
import json
import pytest
from pytest_bdd import scenario, scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect

from poms.create_business_page import CreateBusinessPage
from utils.api_testing import APIUtils

scenarios('../../features/business_creation.feature')


@pytest.fixture
def shared_data():
    return {}

@pytest.fixture
def backend_api(page: Page):
    return APIUtils()



@given(parsers.parse('a new user registered and logged in with "{user_name}"'))
def logged_in_user(page: Page, shared_data, user_name, backend_api: APIUtils):
    # Rule 7: Enforce Test Data Naming Convention
    assert user_name.endswith("Test"), f"Nombre '{user_name}' debe terminar con 'Test'"
    
    api_request_context = page.context.request
    
    # Crear y loguear usuario
    user_data = backend_api.create_e2e_user(api_request_context, name=user_name, is_seller=False)
    
    # Inyectar sesión
    backend_api.inject_session_to_browser(page, user_data)
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))
    
    shared_data['user_token'] = user_data["access_token"]

@given(parsers.parse('a seller user registered and logged in with "{user_name}"'))
def logged_in_seller_user(page: Page, shared_data, user_name, backend_api: APIUtils):
    assert user_name.endswith("Test"), f"Nombre '{user_name}' debe terminar con 'Test'"
    
    api_request_context = page.context.request
    
    # Crear y loguear usuario vendedor
    user_data = backend_api.create_e2e_user(api_request_context, name=user_name, is_seller=True)
    
    # Inyectar sesión
    backend_api.inject_session_to_browser(page, user_data)
    page.goto(os.getenv("BASE_URL", "http://localhost:5173/"))
    
    shared_data['user_token'] = user_data["access_token"]
    shared_data['seller_id'] = user_data["id"]


@given(parsers.parse('a seller user exists in the backend with name "{seller_name}" and code generated from their email and phone'))
def create_seller_user(page: Page, shared_data, seller_name, backend_api: APIUtils):
    assert seller_name.endswith("Test"), f"Nombre '{seller_name}' debe terminar con 'Test'"
    
    api_request_context = page.context.request
    
    user_data = backend_api.create_e2e_user(api_request_context, name=seller_name, is_seller=True)
    
    actual_phone = user_data.get("celular") or user_data.get("phone")
    
    # El código del vendedor es primeros 2 chars del email (lowercase) + ultimos 3 del teléfono real en BD
    prefix = user_data["email"][:2].lower()
    suffix = actual_phone[-3:]
    seller_code = f"{prefix}{suffix}"
    
    shared_data['seller_code'] = seller_code
    shared_data['seller_id'] = user_data["id"]


@given('the user is on the create business page')
def go_to_create_page(page: Page, shared_data):
    create_business_page = CreateBusinessPage(page)
    create_business_page.navigate()
    create_business_page.verify_page_loaded()
    shared_data['create_page'] = create_business_page


@when(parsers.parse('the user fills the business form with "{business_name}"'))
def fill_business_form(shared_data, business_name):
    assert business_name.endswith("Test"), f"Nombre '{business_name}' debe terminar con 'Test'"
    page: CreateBusinessPage = shared_data['create_page']
    
    # Provide required fields
    page.fill_business_info(
        name=business_name,
        description="Descripción genérica de prueba"
    )
    
    # We must provide subcategories per Rule 8 (Required Fields)
    # The categories might be loaded from DB, but typical is "Salud" or similar.
    # We will just click the select and select the first valid option.
    # In spinjob-fronted, categories are fetched. Since we can't guarantee what's in DB without creating it,
    # Let's create a specialty in DB or just use an API call to get one.
    
    # We'll just fetch specialties from the API to pick one dynamically
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/")
    api = page.page.context.request
    # Usar el endpoint /specialties/ (flat list) que retorna [{category, subcategory, ...}]
    res = api.get(f"{base_url}specialties/")
    assert res.ok, f"No se pudo obtener especialidades: {res.status}"
    specialties = res.json()
    assert len(specialties) > 0, "No hay especialidades en la DB para probar"

    cat = specialties[0]["category"]
    sub = specialties[0]["subcategory"]

    page.select_category_and_subcategory(cat, sub)
    shared_data['business_name'] = business_name


@when('leaves the seller code field empty')
def leave_seller_code_empty(shared_data):
    page: CreateBusinessPage = shared_data['create_page']
    page.fill_seller_code("")


@when('provides the valid seller code in the form')
def fill_valid_seller_code(shared_data):
    page: CreateBusinessPage = shared_data['create_page']
    code = shared_data['seller_code']
    page.fill_seller_code(code)


@when('submits the form')
def submit_business_form(shared_data):
    page: CreateBusinessPage = shared_data['create_page']
    page.submit_form()
    page.verify_redirect_to_my_businesses()



@then('the business is created with pending status')
def verify_business_pending(shared_data, page: Page):
    business_name = shared_data['business_name']
    
    # Validate via API to ensure truth
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/")
    api = page.context.request
    
    token = shared_data['user_token']
    res = api.get(
        f"{base_url}usuarios/mis-negocios",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.ok
    businesses = res.json()
    
    created = next((b for b in businesses if b["name"] == business_name), None)
    assert created is not None, "El negocio no fue creado"
    assert created["status"] == "pendiente", f"Estado incorrecto: {created['status']}"
    
    shared_data['created_business'] = created


@then('the business is created with active status')
def verify_business_active(shared_data, page: Page):
    business_name = shared_data['business_name']
    
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/")
    api = page.context.request
    
    token = shared_data['user_token']
    res = api.get(
        f"{base_url}usuarios/mis-negocios",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.ok
    businesses = res.json()
    
    created = next((b for b in businesses if b["name"] == business_name), None)
    assert created is not None, "El negocio no fue creado"
    assert created["status"] == "aprobado", f"Estado incorrecto: {created['status']}"
    
    shared_data['created_business'] = created



@then('the business is not visible in the public directory')
def verify_not_in_directory(shared_data, page: Page):
    business_name = shared_data['business_name']
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/")
    api = page.context.request
    # Usar search= para evitar falsos negativos por paginación (limit=10 por defecto).
    # Si el negocio no aparece incluso filtrando por nombre exacto → correcto, está pendiente.
    res = api.get(f"{base_url}businesses/", params={"search": business_name, "limit": 50})
    assert res.ok, f"Error al consultar el directorio: {res.status}"

    directory = res.json()
    found = any(b["name"] == business_name for b in directory)
    assert not found, "Negocio pendiente apareció en el directorio público"



@then('the business is assigned the premium plan')
def verify_business_plan(shared_data):
    created = shared_data['created_business']
    assert created["premium"] is True, f"Al negocio auto-aprobado se esperaba premium=True pero fue: {created.get('premium')}"


@then('the business is linked to the seller')
def verify_business_linked(shared_data, page: Page):
    created = shared_data['created_business']
    seller_id = shared_data['seller_id']
    
    # We must check the business referred_by. 
    # The directory endpoint might not return referred_by.
    # Let's check my-businesses
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/")
    api = page.context.request
    token = shared_data['user_token']
    
    res = api.get(
        f"{base_url}usuarios/mis-negocios",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.ok
    businesses = res.json()
    my_biz = next((b for b in businesses if b["name"] == shared_data['business_name']), None)
    
    assert my_biz is not None
    assert my_biz.get("referred_by") == seller_id, "El negocio no está vinculado al vendedor correcto"
