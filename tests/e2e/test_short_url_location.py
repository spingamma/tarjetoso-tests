# Archivo: tests/e2e/test_short_url_location.py
"""
Step definitions for short_url_location.feature.

Tests the resolution of short Google Maps URLs (maps.app.goo.gl/...)
in both the backend API and the frontend UI.

Bug under test: The frontend reads `data.resolved_url` from the API response,
but the backend returns the URL under `data.url` (Pydantic field name mismatch).
"""
import os
import re
import json
import pytest
from uuid import uuid4
from pytest_bdd import scenario, given, when, then, parsers
from playwright.sync_api import Page, expect

from poms.edit_business_location_page import EditBusinessLocationPage
from utils.api_testing import APIUtils

FEATURE_FILE = "../../features/short_url_location.feature"

# --- Constants ---
SHORT_GOOGLE_MAPS_URL = "https://maps.app.goo.gl/jyS4XdTsSY88LmAh7"
INVALID_URL = "https://example.com/not-a-map"
COORD_PATTERN = re.compile(r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)")


# --- Scenario Bindings ---

@scenario(FEATURE_FILE, "Backend resolves a short Google Maps URL and returns parseable coordinates")
def test_backend_resolves_short_url():
    """API-level test: backend can resolve short Google Maps URLs."""


@scenario(FEATURE_FILE, "UI detects coordinates after pasting a short Google Maps URL")
def test_ui_detects_short_url_coordinates():
    """E2E test: UI should show success indicator after resolving short URL."""


@scenario(FEATURE_FILE, "UI shows warning when pasting an invalid URL in location field")
def test_ui_shows_warning_for_invalid_url():
    """E2E test: UI shows warning for non-Google Maps URLs."""


# --- Fixtures ---

@pytest.fixture
def shared_data():
    return {}


@pytest.fixture
def backend_api():
    return APIUtils()


# =============================================================================
# Scenario 1: Backend resolves a short Google Maps URL
# =============================================================================

@given("the backend API is available")
def verify_backend_available(page: Page, shared_data, backend_api: APIUtils):
    """Verify the backend API is reachable."""
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000/").rstrip("/")
    api_context = page.context.request

    response = api_context.get(f"{api_base}/businesses/", params={"limit": 1})
    assert response.ok, (
        f"Backend API is not reachable at {api_base}. Status: {response.status}"
    )
    shared_data["api_context"] = api_context
    shared_data["api_base"] = api_base


@when("a resolve-url request is sent with a short Google Maps URL")
def send_resolve_url_request(shared_data):
    """Call the backend resolve-url endpoint with a short Google Maps URL."""
    api_context = shared_data["api_context"]
    api_base = shared_data["api_base"]

    response = api_context.get(
        f"{api_base}/businesses/resolve-url",
        params={"url": SHORT_GOOGLE_MAPS_URL}
    )

    shared_data["resolve_response_status"] = response.status
    shared_data["resolve_response_text"] = response.text()

    # Only parse JSON if the response is valid JSON
    if response.ok:
        try:
            shared_data["resolve_response_body"] = response.json()
        except Exception:
            shared_data["resolve_response_body"] = None
    else:
        shared_data["resolve_response_body"] = None


@then("the response contains a valid URL with coordinates")
def verify_response_has_coordinates(shared_data):
    """Verify the API response contains a parseable Google Maps URL with lat/lng.
    
    This test validates that the resolve-url endpoint returns a 200 response
    with a clean, parseable URL containing coordinates. If the endpoint returns
    500 (Internal Server Error), it means the backend has a serialization bug
    where a dict is being passed to a Pydantic str field.
    """
    status = shared_data["resolve_response_status"]
    body = shared_data["resolve_response_body"]
    raw_text = shared_data["resolve_response_text"]

    assert status == 200, (
        f"Expected 200, got {status}. "
        f"Response text: '{raw_text}'. "
        f"If 500, this confirms the backend serialization bug: "
        f"resolve_url() returns a dict but ResolveUrlResponse.url expects str."
    )

    assert body is not None, "Response body could not be parsed as JSON"

    # The backend returns {"url": ...} — extract the resolved URL
    resolved_value = body["url"]

    # Verify it's a clean URL string (not a stringified dict)
    assert not str(resolved_value).startswith("{"), (
        f"The 'url' field contains a stringified dict instead of a clean URL: "
        f"{resolved_value}"
    )

    # Try to find coordinates in the resolved value
    coord_match = COORD_PATTERN.search(str(resolved_value))

    assert coord_match is not None, (
        f"No coordinates found in resolved URL. "
        f"Response body: {body}. "
        f"This suggests the backend is not returning a clean, parseable URL."
    )

    lat, lng = float(coord_match.group(1)), float(coord_match.group(2))
    assert -90 <= lat <= 90, f"Latitude {lat} is out of range"
    assert -180 <= lng <= 180, f"Longitude {lng} is out of range"



# =============================================================================
# Scenario 2: UI detects coordinates after pasting a short Google Maps URL
# =============================================================================

@given(parsers.parse('a seller user logged in with a business "{business_name}"'))
def setup_seller_with_business(page: Page, shared_data, business_name, backend_api: APIUtils):
    """Create a seller user, log them in, and create a business via API."""
    assert business_name.endswith("Test"), f"Name '{business_name}' must end with 'Test'"

    api_context = page.context.request
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000/").rstrip("/")

    # Create and log in seller user
    user_data = backend_api.create_e2e_user(api_context, name=f"Owner {business_name}", is_seller=True)
    token = user_data["access_token"]

    # Get a valid category/subcategory from the backend
    specialties_res = api_context.get(f"{api_base}/specialties/")
    assert specialties_res.ok, f"Cannot fetch specialties: {specialties_res.status}"
    specialties = specialties_res.json()
    assert len(specialties) > 0, "No specialties in DB for test setup"

    category = specialties[0]["category"]
    subcategory = specialties[0]["subcategory"]

    # Create business via API (multipart/form-data)
    unique_suffix = uuid4().hex[:6]
    biz_name = f"{business_name} {unique_suffix}"

    biz_response = api_context.post(
        f"{api_base}/businesses/",
        headers={"Authorization": f"Bearer {token}"},
        multipart={
            "name": biz_name,
            "title": f"Título {biz_name}",
            "category": category,
            "description": "Negocio de prueba para test de URL de ubicación",
            "state": "La Paz",
            "country": "Bolivia",
            "subcategories": json.dumps([subcategory]),
        }
    )
    assert biz_response.ok, (
        f"Failed to create business. Status: {biz_response.status}. "
        f"Body: {biz_response.text()}"
    )

    biz_data = biz_response.json()

    # Inject session to browser
    backend_api.inject_session_to_browser(page, user_data)

    shared_data["user_token"] = token
    shared_data["business_slug"] = biz_data.get("slug") or biz_data.get("name", "").lower().replace(" ", "-")
    shared_data["business_name"] = biz_name


@given("the user navigates to edit their business")
def navigate_to_edit_business(page: Page, shared_data):
    """Navigate to the business profile and enter edit mode."""
    slug = shared_data["business_slug"]

    location_page = EditBusinessLocationPage(page)
    location_page.navigate_to_business(slug)
    location_page.enter_edit_mode()

    shared_data["location_page"] = location_page


@when("the user pastes a short Google Maps URL in the location field")
def paste_short_url(shared_data):
    """Fill the location URL field with a short Google Maps URL."""
    location_page: EditBusinessLocationPage = shared_data["location_page"]
    location_page.fill_location_url(SHORT_GOOGLE_MAPS_URL)


@when("the URL resolution completes")
def wait_for_resolution(shared_data):
    """Wait for the frontend to finish resolving the short URL."""
    location_page: EditBusinessLocationPage = shared_data["location_page"]
    location_page.wait_for_resolution_complete(timeout=20000)


@then("the UI shows the success indicator for detected location")
def verify_success_indicator(shared_data):
    """Assert the green success message is visible."""
    location_page: EditBusinessLocationPage = shared_data["location_page"]
    expect(location_page.location_success_indicator).to_be_visible(timeout=5000)


@then("the warning message about undetected coordinates is not visible")
def verify_warning_not_visible(shared_data):
    """Assert the orange warning message is NOT visible."""
    location_page: EditBusinessLocationPage = shared_data["location_page"]
    expect(location_page.location_warning_indicator).not_to_be_visible()


# =============================================================================
# Scenario 3: UI shows warning when pasting an invalid URL
# =============================================================================

@when("the user pastes an invalid URL in the location field")
def paste_invalid_url(shared_data):
    """Fill the location URL field with a non-Google Maps URL."""
    location_page: EditBusinessLocationPage = shared_data["location_page"]
    location_page.fill_location_url(INVALID_URL)


@when("waits for any resolution attempt to finish")
def wait_for_invalid_resolution(shared_data, page: Page):
    """Wait enough time for the frontend to process the invalid URL.
    
    Invalid URLs won't trigger the resolve-url API call (the frontend
    only calls it for maps.app.goo.gl URLs), so we just wait for the
    debounce timer (800ms) plus a small buffer.
    """
    page.wait_for_timeout(1500)


@then("the UI shows the warning about undetected coordinates")
def verify_warning_visible(shared_data):
    """Assert the orange warning message IS visible."""
    location_page: EditBusinessLocationPage = shared_data["location_page"]
    expect(location_page.location_warning_indicator).to_be_visible(timeout=5000)
