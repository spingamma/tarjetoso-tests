Feature: Refresh Token Lifecycle and Session Rotation
  As an authenticated application user
  I want to refresh my expired access token using a valid refresh token
  So that I can maintain my active session securely without re-entering credentials

  Scenario: Successful refresh token rotation and protected endpoint consumption
    Given a test user "RefreshToken Success User Test" is authenticated via API
    And the user receives a valid access token and refresh token
    When the user requests a new token pair using the valid refresh token
    Then the server should return HTTP 200 with a new access token and a new refresh token
    And both new tokens should be different from the previous tokens
    And the user should be able to access "/usuarios/status" using the new access token
    And the user can successfully perform a second token rotation with the latest refresh token

  Scenario: Replay attack prevention on already rotated refresh token
    Given a test user "Replay Attack User Test" has already rotated their initial refresh token
    When the client attempts to reuse the previous rotated refresh token
    Then the server should reject the request with HTTP 401 Unauthorized
    And the error detail should indicate "Refresh token inválido, expirado o revocado"

  Scenario: User logout revokes the refresh token permanently
    Given a test user "Logout Revocation User Test" has an active session with a refresh token
    When the user sends a logout request to "/auth/logout" with their refresh token
    Then the server should return HTTP 200 with "Sesión cerrada exitosamente"
    And attempting to refresh session with the logged-out token should return HTTP 401 Unauthorized

  Scenario: Enforcement of strict token type segregation
    Given a test user "Type Confusion User Test" possesses both access and refresh tokens
    When the client sends an access token to the "/auth/refresh" endpoint
    Then the server should reject the request with HTTP 401 Unauthorized
    When the client uses the refresh token as a Bearer authorization token on "/usuarios/status"
    Then the server should reject the request with HTTP 401 Unauthorized

  Scenario: Rejection of empty payload on refresh endpoint
    When a request is sent to "/auth/refresh" with an empty json payload
    Then the server should reject the request with HTTP 422 Unprocessable Entity

  Scenario: Rejection of empty string refresh token
    When a request is sent to "/auth/refresh" with an empty string refresh token
    Then the server should reject the request with HTTP 401 Unauthorized

  Scenario: Rejection of malformed refresh token string
    When a request is sent to "/auth/refresh" with a malformed token string
    Then the server should reject the request with HTTP 401 Unauthorized

  Scenario: Rejection of forged token with invalid signature
    When a request is sent to "/auth/refresh" with a forged token signed with wrong secret
    Then the server should reject the request with HTTP 401 Unauthorized

  Scenario: Rejection of valid JWT not registered in the database
    When a request is sent to "/auth/refresh" with an unregistered valid JWT
    Then the server should reject the request with HTTP 401 Unauthorized
