import os
import uuid
import pytest
import requests
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

from utils.api_testing import APIUtils
from poms.profile_page import ProfilePage
from poms.my_businesses_page import MyBusinessesPage
from poms.team_management_modal_page import TeamManagementModalPage

# Load scenarios from feature file
scenarios('../../../features/business_management/team_management.feature')


@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


def _get_db_engine():
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


# ---------------------------------------------------------------------------
# GIVEN STEPS
# ---------------------------------------------------------------------------

@given(parsers.parse('a registered owner "{owner_name}" with a premium business "{biz_name}" and slug "{slug}"'), target_fixture="owner_biz_setup")
def setup_premium_business(page: Page, shared_data, backend_api: APIUtils, owner_name, biz_name, slug):
    assert biz_name.endswith("Test"), f"Nombre del negocio '{biz_name}' debe terminar con 'Test'"
    api_context = page.context.request
    unique_suffix = uuid.uuid4().hex[:4]

    # 1. Crear Dueño
    owner_data = backend_api.create_e2e_user(api_context, name=f"{owner_name} {unique_suffix}", is_seller=True)
    owner_token = owner_data["access_token"]
    owner_id = owner_data["user"]["id"] if "user" in owner_data else owner_data.get("id")

    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    # 2. Crear Negocio (Nombre <= 30 caracteres)
    final_biz_name = f"{biz_name} {unique_suffix}"[:30]
    biz_payload = {
        "name": final_biz_name,
        "title": "Tienda Premium",
        "description": "Negocio de pruebas E2E Staff Management",
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": owner_data["email"],
        "delivery_methods": '["Entrega en el local"]',
        "payment_methods": '["efectivo", "qr_simple"]',
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
    real_slug = biz_data["slug"]

    # 3. Crear Producto de prueba para carga rápida de la página de perfil
    requests.post(
        f"{base_url}/businesses/{real_slug}/products",
        data={"name": f"Prod {unique_suffix} Test", "price": 25.0, "stock": 50, "catalog_name": "General", "is_visible": True},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    # 4. Activar status aprobado y plan premium en DB
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET is_admin = TRUE WHERE id = :id"), {"id": owner_id})
        conn.execute(text("UPDATE businesses SET status = 'aprobado' WHERE id = :bid"), {"bid": biz_id})
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {
            "bid": biz_id,
            "exp": (datetime.now() + timedelta(days=365)).isoformat()
        })

    shared_data['owner_name'] = owner_name
    shared_data['owner_data'] = owner_data
    shared_data['owner_token'] = owner_token
    shared_data['owner_id'] = owner_id
    shared_data['biz_id'] = biz_id
    shared_data['slug'] = real_slug
    shared_data['biz_name'] = final_biz_name

    return {"biz_id": biz_id, "slug": real_slug, "owner_token": owner_token}


@given(parsers.parse('registered users "{user1}" and "{user2}" exist in the system'))
def create_candidate_users(page: Page, shared_data, backend_api: APIUtils, user1, user2):
    api_context = page.context.request
    unique_suffix = uuid.uuid4().hex[:4]

    u1_data = backend_api.create_e2e_user(api_context, name=f"{user1} {unique_suffix}")
    u2_data = backend_api.create_e2e_user(api_context, name=f"{user2} {unique_suffix}")

    shared_data[user1] = {
        "display_name": f"{user1} {unique_suffix}",
        "data": u1_data,
        "email": u1_data["email"],
        "id": u1_data["user"]["id"] if "user" in u1_data else u1_data.get("id"),
        "token": u1_data["access_token"]
    }
    shared_data[user2] = {
        "display_name": f"{user2} {unique_suffix}",
        "data": u2_data,
        "email": u2_data["email"],
        "id": u2_data["user"]["id"] if "user" in u2_data else u2_data.get("id"),
        "token": u2_data["access_token"]
    }


@given(parsers.parse('the business already has two staff members "{staff1}" and "{staff2}"'))
def setup_two_existing_staff(page: Page, shared_data, backend_api: APIUtils, staff1, staff2):
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    owner_token = shared_data['owner_token']
    unique_suffix = uuid.uuid4().hex[:4]

    s1_data = backend_api.create_e2e_user(api_context, name=f"{staff1} {unique_suffix}")
    s2_data = backend_api.create_e2e_user(api_context, name=f"{staff2} {unique_suffix}")

    # Add staff 1
    res1 = requests.post(
        f"{base_url}/businesses/{slug}/staff",
        json={"query": s1_data["email"]},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res1.ok, f"Error adding staff 1: {res1.text}"
    staff1_record = res1.json()

    # Add staff 2
    res2 = requests.post(
        f"{base_url}/businesses/{slug}/staff",
        json={"query": s2_data["email"]},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res2.ok, f"Error adding staff 2: {res2.text}"
    staff2_record = res2.json()

    shared_data[staff1] = {
        "display_name": f"{staff1} {unique_suffix}",
        "data": s1_data,
        "email": s1_data["email"],
        "id": s1_data["user"]["id"] if "user" in s1_data else s1_data.get("id"),
        "staff_id": staff1_record["id"],
        "token": s1_data["access_token"]
    }
    shared_data[staff2] = {
        "display_name": f"{staff2} {unique_suffix}",
        "data": s2_data,
        "email": s2_data["email"],
        "id": s2_data["user"]["id"] if "user" in s2_data else s2_data.get("id"),
        "staff_id": staff2_record["id"],
        "token": s2_data["access_token"]
    }


@given(parsers.parse('a registered owner "{owner_name}" with a standard free business "{biz_name}" and slug "{slug}"'))
def setup_free_business(page: Page, shared_data, backend_api: APIUtils, owner_name, biz_name, slug):
    assert biz_name.endswith("Test"), f"Nombre del negocio '{biz_name}' debe terminar con 'Test'"
    api_context = page.context.request
    unique_suffix = uuid.uuid4().hex[:4]

    owner_data = backend_api.create_e2e_user(api_context, name=f"{owner_name} {unique_suffix}", is_seller=True)
    owner_token = owner_data["access_token"]
    owner_id = owner_data["user"]["id"] if "user" in owner_data else owner_data.get("id")

    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    final_biz_name = f"{biz_name} {unique_suffix}"[:30]
    biz_payload = {
        "name": final_biz_name,
        "title": "Tienda Gratuita",
        "description": "Negocio Estándar sin Plan Premium",
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "phone": "59170000000",
        "email": owner_data["email"],
        "delivery_methods": '["Entrega en el local"]',
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
    real_slug = biz_data["slug"]

    # Crear producto de prueba
    requests.post(
        f"{base_url}/businesses/{real_slug}/products",
        data={"name": f"Free Prod {unique_suffix} Test", "price": 10.0, "stock": 10, "catalog_name": "General", "is_visible": True},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    # Dejar en Plan Gratuito (premium = False) y status aprobado
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("UPDATE businesses SET status = 'aprobado' WHERE id = :bid"), {"bid": biz_id})
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = FALSE
            WHERE business_id = :bid
        """), {"bid": biz_id})

    shared_data['free_owner_data'] = owner_data
    shared_data['free_owner_token'] = owner_token
    shared_data['free_slug'] = real_slug
    shared_data['free_biz_id'] = biz_id


@given(parsers.parse('a non-owner user "{user_name}" exists'))
def setup_non_owner_user(page: Page, shared_data, backend_api: APIUtils, user_name):
    api_context = page.context.request
    unique_suffix = uuid.uuid4().hex[:4]
    non_owner_data = backend_api.create_e2e_user(api_context, name=f"{user_name} {unique_suffix}")
    shared_data['non_owner_data'] = non_owner_data
    shared_data['non_owner_token'] = non_owner_data["access_token"]


# ---------------------------------------------------------------------------
# WHEN & THEN STEPS: SCENARIO 1 (SEARCH & ADD UP TO LIMIT)
# ---------------------------------------------------------------------------

@when('the owner logs in and navigates to "Mis Negocios"')
def owner_logs_in_and_visits_my_businesses(page: Page, shared_data, backend_api: APIUtils):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/").rstrip("/")
    owner_data = shared_data['owner_data']

    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")

    backend_api.inject_session_to_browser(page, owner_data)
    my_biz_page = MyBusinessesPage(page)
    my_biz_page.go_to()


@then(parsers.parse('the "Gestionar equipo" button is visible for "{slug}" in "Mis Negocios"'))
def verify_manage_team_button_visible_in_my_biz(page: Page, shared_data, slug):
    my_biz_page = MyBusinessesPage(page)
    real_slug = shared_data.get('slug', slug)
    my_biz_page.verify_team_management_btn_visible(real_slug)


@when(parsers.parse('the owner clicks "Gestionar equipo" button for "{slug}"'))
def click_manage_team_button_for_slug(page: Page, shared_data, slug):
    my_biz_page = MyBusinessesPage(page)
    real_slug = shared_data.get('slug', slug)
    my_biz_page.open_team_management(real_slug)


@when(parsers.parse('the owner logs in and navigates to "{slug}" profile'))
def owner_logs_in_and_visits_profile(page: Page, shared_data, backend_api: APIUtils, slug):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/").rstrip("/")
    real_slug = shared_data['slug']
    owner_data = shared_data['owner_data']

    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")

    backend_api.inject_session_to_browser(page, owner_data)
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


@then('the "Gestionar equipo" button is visible in the profile banner')
def verify_manage_team_button_visible(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_team_management_btn_visible()


@when('the owner clicks "Gestionar equipo" button')
def click_manage_team_button(page: Page, shared_data):
    if "/mis-negocios" in page.url:
        my_biz_page = MyBusinessesPage(page)
        real_slug = shared_data.get('slug')
        my_biz_page.open_team_management(real_slug)
    else:
        profile_page = ProfilePage(page)
        profile_page.open_team_management()


@then(parsers.parse('the team management modal opens with counter "{counter_text}"'))
def verify_team_modal_opened(page: Page, counter_text):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_page_loaded()
    modal_page.verify_counter(counter_text)


@when(parsers.parse('the owner searches for a non-existent candidate "{email}"'))
def search_non_existent_candidate(page: Page, email):
    modal_page = TeamManagementModalPage(page)
    modal_page.search_candidate(email)


@then(parsers.parse('an error message "{err_msg}" is displayed in the modal'))
def verify_error_message_displayed(page: Page, err_msg):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_error_message(err_msg)


@when('the owner searches for their own email')
def search_owner_own_email(page: Page, shared_data):
    modal_page = TeamManagementModalPage(page)
    owner_email = shared_data['owner_data']['email']
    modal_page.search_candidate(owner_email)


@when(parsers.parse('the owner searches for "{candidate_name}"'))
def search_for_candidate(page: Page, shared_data, candidate_name):
    modal_page = TeamManagementModalPage(page)
    candidate_email = shared_data[candidate_name]['email']
    modal_page.search_candidate(candidate_email)


@then(parsers.parse('the candidate preview card displays "{candidate_name}"'))
def verify_candidate_card(page: Page, shared_data, candidate_name):
    modal_page = TeamManagementModalPage(page)
    display_name = shared_data[candidate_name]['display_name']
    modal_page.verify_candidate_preview(display_name)


@when('the owner confirms adding the candidate to the team')
def confirm_add_candidate(page: Page):
    modal_page = TeamManagementModalPage(page)
    modal_page.confirm_add_staff()


@then(parsers.parse('"{candidate_name}" appears in the active staff list'))
def verify_candidate_in_staff_list(page: Page, shared_data, candidate_name):
    modal_page = TeamManagementModalPage(page)
    display_name = shared_data[candidate_name]['display_name']
    modal_page.verify_staff_in_list(display_name)


@then(parsers.parse('the team counter updates to "{counter_text}"'))
def verify_counter_updated(page: Page, counter_text):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_counter(counter_text)


@when(parsers.parse('the owner searches and adds "{candidate_name}" to the team'))
def search_and_add_second_candidate(page: Page, shared_data, candidate_name):
    modal_page = TeamManagementModalPage(page)
    candidate_email = shared_data[candidate_name]['email']
    display_name = shared_data[candidate_name]['display_name']

    modal_page.search_candidate(candidate_email)
    modal_page.verify_candidate_preview(display_name)
    modal_page.confirm_add_staff()


@then('the limit reached warning banner is visible')
def verify_limit_reached_banner(page: Page):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_limit_warning_visible()


@then('the search input is not visible')
def verify_search_input_hidden(page: Page):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_search_input_not_visible()


@when('an unauthorized attempt via API is made to add a third collaborator')
def attempt_add_third_staff_via_api(page: Page, shared_data, backend_api: APIUtils):
    api_context = page.context.request
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    owner_token = shared_data['owner_token']

    # Crear 3er usuario
    u3 = backend_api.create_e2e_user(api_context, name="Tercer Candidato Test")

    res = requests.post(
        f"{base_url}/businesses/{slug}/staff",
        json={"query": u3["email"]},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    shared_data['third_staff_response'] = res


@then('the API rejects the addition with status 400 and limit reached message')
def verify_api_rejects_third_collaborator(shared_data):
    res = shared_data['third_staff_response']
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
    assert "Límite alcanzado" in res.text or "máximo permitido" in res.text


# ---------------------------------------------------------------------------
# WHEN & THEN STEPS: SCENARIO 2 (DISMISSAL VECTOR & REMOVAL)
# ---------------------------------------------------------------------------

@when('the owner clicks the modal close button')
def click_modal_close_button(page: Page):
    modal_page = TeamManagementModalPage(page)
    modal_page.close_modal()


@then('the team management modal is closed')
def verify_modal_is_closed(page: Page):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_modal_closed()


@then('the "Mis Negocios" panel remains visible and interactive')
def verify_my_biz_panel_remains_interactive(page: Page, shared_data):
    my_biz_page = MyBusinessesPage(page)
    real_slug = shared_data.get('slug')
    my_biz_page.verify_team_management_btn_visible(real_slug)


@then('the profile banner remains visible and interactive')
def verify_profile_remains_interactive(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_team_management_btn_visible()


@when(parsers.parse('the owner expands permissions for "{staff_name}"'))
def expand_staff_permissions(page: Page, shared_data, staff_name):
    modal_page = TeamManagementModalPage(page)
    staff_id = shared_data[staff_name]['staff_id']
    modal_page.expand_permissions(staff_id)


@then(parsers.parse('granular permission toggles are visible for "{staff_name}"'))
def verify_permission_toggles(page: Page, shared_data, staff_name):
    modal_page = TeamManagementModalPage(page)
    staff_id = shared_data[staff_name]['staff_id']
    modal_page.verify_permission_checkbox_visible(staff_id, "can_manage_orders")
    modal_page.verify_permission_checkbox_visible(staff_id, "can_direct_sale")
    modal_page.verify_permission_checkbox_visible(staff_id, "can_toggle_open")


@when(parsers.parse('the owner removes "{staff_name}" from the team'))
def remove_staff_member(page: Page, shared_data, staff_name):
    modal_page = TeamManagementModalPage(page)
    staff_id = shared_data[staff_name]['staff_id']
    modal_page.remove_staff(staff_id)


@then(parsers.parse('"{staff_name}" is no longer in the active staff list'))
def verify_staff_removed_from_ui(page: Page, shared_data, staff_name):
    modal_page = TeamManagementModalPage(page)
    display_name = shared_data[staff_name]['display_name']
    modal_page.verify_staff_not_in_list(display_name)


@then('the search input is visible again')
def verify_search_input_visible_again(page: Page):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_search_input_visible()


@then('the staff member is deleted from the database')
def verify_staff_deleted_from_db(shared_data):
    engine = _get_db_engine()
    biz_id = shared_data['biz_id']
    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM business_staff WHERE business_id = :bid"),
            {"bid": biz_id}
        ).scalar()
        assert count == 1, f"Expected 1 remaining staff in DB, found {count}"


# ---------------------------------------------------------------------------
# WHEN & THEN STEPS: SCENARIO 3 (RBAC RESTRICTIONS)
# ---------------------------------------------------------------------------

@when(parsers.parse('the free business owner logs in and navigates to "{slug}" profile'))
def free_owner_logs_in(page: Page, shared_data, backend_api: APIUtils, slug):
    base_url = os.getenv("BASE_URL", "http://localhost:5173/").rstrip("/")
    real_slug = shared_data['free_slug']
    owner_data = shared_data['free_owner_data']

    page.goto(base_url)
    page.context.clear_cookies()
    page.evaluate("localStorage.clear()")

    backend_api.inject_session_to_browser(page, owner_data)
    profile_page = ProfilePage(page)
    profile_page.go_to(real_slug)


@then('the "Gestionar equipo" button is not visible')
def verify_team_btn_not_visible(page: Page):
    profile_page = ProfilePage(page)
    profile_page.verify_team_management_btn_not_visible()


@when('the free business owner attempts to add staff via API')
def free_owner_attempts_add_staff_api(page: Page, shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['free_slug']
    token = shared_data['free_owner_token']

    res = requests.post(
        f"{base_url}/businesses/{slug}/staff",
        json={"query": "random_candidate@test.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    shared_data['free_add_staff_res'] = res


@then('the API rejects with status 403 and premium required message')
def verify_free_business_403(shared_data):
    res = shared_data['free_add_staff_res']
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    assert "Plan Premium" in res.text or "exclusiva" in res.text


@when('the non-owner user attempts to list staff via API')
def non_owner_attempts_list_staff(page: Page, shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['free_slug']
    token = shared_data['non_owner_token']

    res = requests.get(
        f"{base_url}/businesses/{slug}/staff",
        headers={"Authorization": f"Bearer {token}"}
    )
    shared_data['non_owner_list_res'] = res


@then('the API rejects with status 403 and owner required message')
def verify_non_owner_403(shared_data):
    res = shared_data['non_owner_list_res']
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    assert "Solo el dueño" in res.text


@when('a staff member attempts to delete another collaborator via API')
def staff_member_attempts_delete_other_staff(page: Page, shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    # Create business and 2 staff members
    api_context = page.context.request
    owner = backend_api.create_e2e_user(api_context, name="Owner Temp Test", is_seller=True)
    res_biz = requests.post(
        f"{base_url}/businesses/",
        data={
            "name": f"Biz RBAC {uuid.uuid4().hex[:4]} Test"[:30],
            "title": "RBAC",
            "description": "Negocio RBAC Staff Test",
            "state": "Santa Cruz",
            "country": "Bolivia",
            "category": "Comida Rápida & Burgers",
            "subcategories": '["Hamburguesas"]',
            "phone": "59170000000",
            "email": owner["email"],
        },
        headers={"Authorization": f"Bearer {owner['access_token']}"}
    )
    assert res_biz.ok, f"Error creating rbac biz: {res_biz.text}"
    slug = res_biz.json()["slug"]

    # Make premium in DB
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("UPDATE businesses SET status = 'aprobado' WHERE slug = :s"), {"s": slug})
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE 
            WHERE business_id = (SELECT id FROM businesses WHERE slug = :s)
        """), {"s": slug})

    # Add staff 1 and staff 2
    u1 = backend_api.create_e2e_user(api_context, name="Staff Uno Test")
    u2 = backend_api.create_e2e_user(api_context, name="Staff Dos Test")

    r1 = requests.post(f"{base_url}/businesses/{slug}/staff", json={"query": u1["email"]}, headers={"Authorization": f"Bearer {owner['access_token']}"})
    assert r1.ok, f"Error adding u1: {r1.text}"
    r2 = requests.post(f"{base_url}/businesses/{slug}/staff", json={"query": u2["email"]}, headers={"Authorization": f"Bearer {owner['access_token']}"})
    assert r2.ok, f"Error adding u2: {r2.text}"
    staff2_id = r2.json()["id"]

    # Staff 1 attempts to delete Staff 2
    res = requests.delete(
        f"{base_url}/businesses/{slug}/staff/{staff2_id}",
        headers={"Authorization": f"Bearer {u1['access_token']}"}
    )
    shared_data['staff_delete_other_res'] = res


@then('the API rejects with status 403 forbidden')
def verify_staff_delete_other_forbidden(shared_data):
    res = shared_data['staff_delete_other_res']
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"


# ---------------------------------------------------------------------------
# STEPS FOR SCENARIO 4: CONTAINS SEARCH & UP TO 2 CLOSEST RESULTS
# ---------------------------------------------------------------------------

@given('three registered candidates with unique search token exist in the system')
def create_three_candidate_users_with_token(page: Page, shared_data, backend_api: APIUtils):
    api_context = page.context.request
    token = uuid.uuid4().hex[:6]
    shared_data['search_token'] = token
    shared_data['third_token'] = f"tri_{token}"

    u1_name = f"Staff{token} Uno Test"
    u2_name = f"Staff{token} Dos Test"
    u3_name = f"Staff{shared_data['third_token']} Tres Test"

    u1_data = backend_api.create_e2e_user(api_context, name=u1_name)
    u2_data = backend_api.create_e2e_user(api_context, name=u2_name)
    u3_data = backend_api.create_e2e_user(api_context, name=u3_name)

    shared_data['candidate_1'] = {"name": u1_name, "email": u1_data["email"], "data": u1_data}
    shared_data['candidate_2'] = {"name": u2_name, "email": u2_data["email"], "data": u2_data}
    shared_data['candidate_3'] = {"name": u3_name, "email": u3_data["email"], "data": u3_data}


@when('the owner searches for candidate unique token')
def search_candidate_unique_token(page: Page, shared_data):
    modal_page = TeamManagementModalPage(page)
    modal_page.search_candidate(shared_data['search_token'])


@then('both candidate preview cards match the unique token')
def verify_both_candidates_match(page: Page, shared_data):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_candidate_preview(shared_data['candidate_1']['name'])
    modal_page.verify_candidate_preview(shared_data['candidate_2']['name'])


@when('the owner searches for third candidate unique token')
def search_third_candidate_token(page: Page, shared_data):
    modal_page = TeamManagementModalPage(page)
    modal_page.search_candidate(shared_data['third_token'])


@when('the owner confirms adding the third candidate to the team')
def confirm_add_third_candidate(page: Page, shared_data):
    modal_page = TeamManagementModalPage(page)
    modal_page.confirm_add_staff_by_name(shared_data['candidate_3']['name'])


@then('the third candidate appears in the active staff list')
def verify_third_candidate_in_staff_list(page: Page, shared_data):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_staff_in_list(shared_data['candidate_3']['name'])


@then(parsers.parse('exactly {count:d} candidate preview cards are displayed'))
def verify_candidate_cards_count(page: Page, count):
    modal_page = TeamManagementModalPage(page)
    modal_page.verify_candidate_count(count)


@when('the owner searches candidate via API for candidate unique token')
def api_search_candidate_token(shared_data, backend_api: APIUtils):
    base_url = (backend_api.base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    slug = shared_data['slug']
    owner_token = shared_data['owner_token']
    token = shared_data['search_token']
    res = requests.get(
        f"{base_url}/businesses/{slug}/staff/search-user?query={token}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    shared_data['api_search_res'] = res


@then(parsers.parse('the API search returns at most {max_results:d} results ordered by closeness'))
def verify_api_search_results(shared_data, max_results):
    res = shared_data['api_search_res']
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert isinstance(data, list), f"Expected list response, got {type(data)}"
    assert 1 <= len(data) <= max_results, f"Expected between 1 and {max_results} results, got {len(data)}"
