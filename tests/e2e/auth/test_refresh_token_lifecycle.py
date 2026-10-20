import os
import json
import base64
import hmac
import hashlib
import time
import uuid
import pytest
from pytest_bdd import scenario, given, when, then, parsers
from playwright.sync_api import Playwright, APIRequestContext, Error as PlaywrightError
from utils.api_testing import APIUtils

FEATURE_FILE = "../../../features/auth/refresh_token_lifecycle.feature"


def generate_custom_jwt(payload: dict, secret: str) -> str:
    """Genera un token JWT HMAC-SHA256 utilizando únicamente la biblioteca estándar."""
    header = {"alg": "HS256", "typ": "JWT"}
    b64url = lambda b: base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")
    h_b64 = b64url(json.dumps(header).encode("utf-8"))
    p_b64 = b64url(json.dumps(payload).encode("utf-8"))
    msg = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = b64url(hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest())
    return f"{h_b64}.{p_b64}.{sig}"


# =============================================================================
# Scenarios
# =============================================================================

@scenario(FEATURE_FILE, "Successful refresh token rotation and protected endpoint consumption")
def test_successful_refresh_token_rotation():
    """Valida la rotación exitosa de tokens y acceso a endpoints protegidos."""


@scenario(FEATURE_FILE, "Replay attack prevention on already rotated refresh token")
def test_replay_attack_prevention():
    """Valida que un token previo rotado no pueda ser reutilizado."""


@scenario(FEATURE_FILE, "User logout revokes the refresh token permanently")
def test_user_logout_revocation():
    """Valida que el cierre de sesión revoque el token en base de datos."""


@scenario(FEATURE_FILE, "Enforcement of strict token type segregation")
def test_strict_token_type_segregation():
    """Valida el rechazo por confusión de tipos de token (access vs refresh)."""


@scenario(FEATURE_FILE, "Rejection of empty payload on refresh endpoint")
def test_rejection_empty_payload():
    """Valida el rechazo de un payload vacío con HTTP 422."""


@scenario(FEATURE_FILE, "Rejection of empty string refresh token")
def test_rejection_empty_string_token():
    """Valida el rechazo de un refresh token con string vacío."""


@scenario(FEATURE_FILE, "Rejection of malformed refresh token string")
def test_rejection_malformed_token():
    """Valida el rechazo de tokens con estructura inválida o corrupta."""


@scenario(FEATURE_FILE, "Rejection of forged token with invalid signature")
def test_rejection_forged_signature():
    """Valida el rechazo de tokens firmados con una clave secreta incorrecta."""


@scenario(FEATURE_FILE, "Rejection of valid JWT not registered in the database")
def test_rejection_unregistered_jwt():
    """Valida el rechazo de un JWT con firma válida pero no persistido en la base de datos."""


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def api_context(playwright: Playwright) -> APIRequestContext:
    """Provee un contexto HTTP de Playwright para llamadas de API puras."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/").rstrip("/")
    try:
        context = playwright.request.new_context(base_url=base_url)
    except PlaywrightError as e:
        pytest.skip(f"Service not available: {e}")
    yield context
    context.dispose()


@pytest.fixture
def backend_api() -> APIUtils:
    """Instancia del cliente auxiliar APIUtils."""
    return APIUtils()


@pytest.fixture
def shared_data() -> dict:
    """Contenedor de estado compartido entre pasos BDD."""
    return {}


# =============================================================================
# Step Definitions — Given
# =============================================================================

@given(parsers.parse('a test user "{name}" is authenticated via API'))
def step_auth_user(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, name: str):
    try:
        user_info = backend_api.create_e2e_user(api_context, name)
        shared_data["user"] = user_info
        shared_data["access_token"] = user_info["access_token"]
        shared_data["refresh_token"] = user_info["refresh_token"]
    except PlaywrightError as e:
        pytest.skip(f"Service not available: {e}")


@given("the user receives a valid access token and refresh token")
def step_verify_initial_tokens(shared_data: dict):
    assert shared_data["access_token"], "Initial access_token must not be empty"
    assert shared_data["refresh_token"], "Initial refresh_token must not be empty"


@given(parsers.parse('a test user "{name}" has already rotated their initial refresh token'))
def step_user_with_rotated_token(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, name: str):
    try:
        user_info = backend_api.create_e2e_user(api_context, name)
        initial_refresh_token = user_info["refresh_token"]
        shared_data["rotated_token"] = initial_refresh_token
        
        # Realizamos la primera rotación legítima
        rotation_resp = backend_api.refresh_token(
            api_context,
            refresh_token=initial_refresh_token,
            expected_status=[200]
        )
        assert rotation_resp.status == 200, f"Expected initial rotation to succeed, got {rotation_resp.status}"
    except PlaywrightError as e:
        pytest.skip(f"Service not available: {e}")


@given(parsers.parse('a test user "{name}" has an active session with a refresh token'))
def step_user_with_active_session(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, name: str):
    try:
        user_info = backend_api.create_e2e_user(api_context, name)
        shared_data["user"] = user_info
        shared_data["refresh_token"] = user_info["refresh_token"]
    except PlaywrightError as e:
        pytest.skip(f"Service not available: {e}")


@given(parsers.parse('a test user "{name}" possesses both access and refresh tokens'))
def step_user_with_both_tokens(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, name: str):
    try:
        user_info = backend_api.create_e2e_user(api_context, name)
        shared_data["access_token"] = user_info["access_token"]
        shared_data["refresh_token"] = user_info["refresh_token"]
    except PlaywrightError as e:
        pytest.skip(f"Service not available: {e}")


# =============================================================================
# Step Definitions — When
# =============================================================================

@when("the user requests a new token pair using the valid refresh token")
def step_request_token_rotation(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    response = backend_api.refresh_token(
        api_context,
        refresh_token=shared_data["refresh_token"],
        expected_status=[200]
    )
    shared_data["refresh_response"] = response
    shared_data["last_response"] = response


@when("the client attempts to reuse the previous rotated refresh token")
def step_reuse_rotated_token(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    response = backend_api.refresh_token(
        api_context,
        refresh_token=shared_data["rotated_token"]
    )
    shared_data["last_response"] = response


@when(parsers.parse('the user sends a logout request to "{endpoint}" with their refresh token'))
def step_send_logout(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, endpoint: str):
    response = backend_api.logout(
        api_context,
        refresh_token=shared_data["refresh_token"],
        expected_status=[200]
    )
    shared_data["logout_response"] = response
    shared_data["last_response"] = response


@when(parsers.parse('the client sends an access token to the "{endpoint}" endpoint'))
def step_send_access_token_to_refresh(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, endpoint: str):
    response = backend_api.refresh_token(
        api_context,
        refresh_token=shared_data["access_token"]
    )
    shared_data["last_response"] = response


@when(parsers.parse('the client uses the refresh token as a Bearer authorization token on "{endpoint}"'))
def step_use_refresh_token_as_bearer(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, endpoint: str):
    response = backend_api.get_user_status(
        api_context,
        access_token=shared_data["refresh_token"]
    )
    shared_data["last_response"] = response


@when('a request is sent to "/auth/refresh" with an empty json payload')
def step_empty_payload(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    response = backend_api.refresh_token(
        api_context,
        payload={}
    )
    shared_data["last_response"] = response


@when('a request is sent to "/auth/refresh" with an empty string refresh token')
def step_empty_string_token(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    response = backend_api.refresh_token(
        api_context,
        refresh_token=""
    )
    shared_data["last_response"] = response


@when('a request is sent to "/auth/refresh" with a malformed token string')
def step_malformed_token(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    response = backend_api.refresh_token(
        api_context,
        refresh_token="not.a.valid.jwt.string.at.all"
    )
    shared_data["last_response"] = response


@when('a request is sent to "/auth/refresh" with a forged token signed with wrong secret')
def step_forged_token_wrong_secret(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    payload = {
        "sub": str(uuid.uuid4()),
        "type": "refresh",
        "exp": int(time.time()) + 86400,
        "jti": str(uuid.uuid4())
    }
    forged_token = generate_custom_jwt(payload, secret="invalid_unauthorized_secret_key_999")
    response = backend_api.refresh_token(
        api_context,
        refresh_token=forged_token
    )
    shared_data["last_response"] = response


@when('a request is sent to "/auth/refresh" with an unregistered valid JWT')
def step_unregistered_valid_jwt(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    secret = os.getenv("SECRET_KEY", "test_secret_key_not_for_production")
    payload = {
        "sub": str(uuid.uuid4()),
        "type": "refresh",
        "exp": int(time.time()) + 86400,
        "jti": str(uuid.uuid4())
    }
    valid_unregistered_token = generate_custom_jwt(payload, secret=secret)
    response = backend_api.refresh_token(
        api_context,
        refresh_token=valid_unregistered_token
    )
    shared_data["last_response"] = response


# =============================================================================
# Step Definitions — Then
# =============================================================================

@then("the server should return HTTP 200 with a new access token and a new refresh token")
def step_verify_refresh_success(shared_data: dict):
    response = shared_data["refresh_response"]
    assert response.status == 200, f"Expected 200 OK, got {response.status}: {response.text()}"
    data = response.json()
    assert "access_token" in data, "Response must include access_token"
    assert "refresh_token" in data, "Response must include refresh_token"
    shared_data["new_access_token"] = data["access_token"]
    shared_data["new_refresh_token"] = data["refresh_token"]


@then("both new tokens should be different from the previous tokens")
def step_verify_tokens_rotated(shared_data: dict):
    assert shared_data["new_access_token"] != shared_data["access_token"], (
        "New access token must be different from previous access token"
    )
    assert shared_data["new_refresh_token"] != shared_data["refresh_token"], (
        "New refresh token must be different from previous refresh token (rotation)"
    )


@then(parsers.parse('the user should be able to access "{endpoint}" using the new access token'))
def step_verify_new_token_access(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict, endpoint: str):
    response = backend_api.get_user_status(
        api_context,
        access_token=shared_data["new_access_token"],
        expected_status=[200]
    )
    assert response.status == 200, f"Expected 200 from {endpoint}, got {response.status}"


@then("the user can successfully perform a second token rotation with the latest refresh token")
def step_verify_second_rotation(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    second_response = backend_api.refresh_token(
        api_context,
        refresh_token=shared_data["new_refresh_token"],
        expected_status=[200]
    )
    assert second_response.status == 200, "Second consecutive token rotation failed"
    second_data = second_response.json()
    assert second_data["refresh_token"] != shared_data["new_refresh_token"], (
        "Consecutive rotation must produce yet another distinct refresh token"
    )


@then(parsers.parse("the server should reject the request with HTTP {status_code:d} {status_name}"))
def step_verify_rejected_status(shared_data: dict, status_code: int, status_name: str):
    response = shared_data["last_response"]
    assert response.status == status_code, (
        f"Expected status {status_code} ({status_name}), got {response.status}: {response.text()}"
    )


@then(parsers.parse('the error detail should indicate "{expected_detail}"'))
def step_verify_error_detail(shared_data: dict, expected_detail: str):
    response = shared_data["last_response"]
    detail = response.json().get("detail", "")
    assert expected_detail in detail, f"Expected '{expected_detail}' in response detail, got '{detail}'"


@then(parsers.parse('the server should return HTTP 200 with "{expected_message}"'))
def step_verify_logout_message(shared_data: dict, expected_message: str):
    response = shared_data["logout_response"]
    assert response.status == 200, f"Expected 200 OK, got {response.status}"
    message = response.json().get("message", "")
    assert message == expected_message, f"Expected message '{expected_message}', got '{message}'"


@then("attempting to refresh session with the logged-out token should return HTTP 401 Unauthorized")
def step_verify_refresh_after_logout(api_context: APIRequestContext, backend_api: APIUtils, shared_data: dict):
    response = backend_api.refresh_token(
        api_context,
        refresh_token=shared_data["refresh_token"],
        expected_status=[401]
    )
    assert response.status == 401, f"Expected 401 Unauthorized after logout, got {response.status}"
