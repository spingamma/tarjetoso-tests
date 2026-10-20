# Plan de Pruebas de API — Ciclo de Vida y Seguridad de Refresh Tokens (Auth)

> **Módulo:** Autenticación & Sesiones (`/auth/refresh`, `/auth/logout`, `/auth/e2e-login`)  
> **Nivel:** Pruebas de API / Backend (Zero Mocking, Playwright API Request Context / Requests)  
> **Estándar:** BDD (pytest-bdd + Gherkin en Inglés)  
> **Fecha de Creación:** 2026-09-27  

---

## 1. Contexto y Objetivos de Calidad

El backend de Tarjetoso implementa un esquema de **tokens duales** con rotación y control en base de datos:
1. **Access Token:** JWT de vida corta (30 minutos) con claim `type: "access"`, utilizado para invocar endpoints protegidos.
2. **Refresh Token:** JWT de vida larga (15 días) con claim `type: "refresh"`, persistido en la tabla relacional `user_refresh_tokens` con control de revocación (`revoked = False/True`) y fecha de expiración (`expires_at`).
3. **Rotación Automática (`POST /auth/refresh`):** Al refrescar sesión, el token utilizado se revoca inmediatamente (`revoked = True`) y se emite un nuevo par de tokens (Sliding Window), impidiendo ataques de repetición (*Replay Attacks*).
4. **Cierre de Sesión (`POST /auth/logout`):** Invalida el refresh token en la base de datos de manera definitiva.

El objetivo de esta suite de pruebas de API es garantizar la integridad criptográfica, la persistencia de estado, la prevención de reuso de tokens revocados y la resistencia frente a payloads malformados o vectores de inyección.

---

## 2. Flujos de Prueba BDD

### Flujo 1: Rotación Exitosa de Refresh Token y Validación de Nuevo Acceso 🔴 Crítica

> **Precondición:** Usuario de prueba registrado y autenticado mediante `/auth/e2e-login` con credenciales válidas y par de tokens generado.  
> **Actor:** Usuario Autenticado (`User`)  

| Paso | Acción de API | Validación esperada |
|------|---------------|---------------------|
| 1    | `POST /auth/e2e-login` con payload de usuario terminando en `"Test"` | HTTP 200 OK, recibe `access_token`, `refresh_token` y `token_type: "bearer"`. |
| 2    | `POST /auth/refresh` enviando el `refresh_token` obtenido | HTTP 200 OK, recibe `new_access_token` y `new_refresh_token` distintos a los originales. |
| 3    | `GET /usuarios/status` con header `Authorization: Bearer <new_access_token>` | HTTP 200 OK, status del usuario accesible con el nuevo token. |
| 4    | `POST /auth/refresh` con `new_refresh_token` (segundo ciclo sliding window) | HTTP 200 OK, confirmando que la cadena de rotación continúa activa. |

```gherkin
Feature: Refresh Token Lifecycle and Session Rotation
  As an authenticated application user
  I want to refresh my expired access token using a valid refresh token
  So that I can maintain my active session securely without re-entering credentials

  Scenario: Successful refresh token rotation and protected endpoint consumption
    Given a test user "RefreshToken User Test" is authenticated via API
    And the user receives a valid access token and refresh token
    When the user requests a new token pair using the valid refresh token
    Then the server should return HTTP 200 with a new access token and a new refresh token
    And both new tokens should be different from the previous tokens
    And the user should be able to access "/usuarios/status" using the new access token
    And the user can successfully perform a second token rotation with the latest refresh token
```

**Cobertura implícita:** Generación inicial de tokens, emisión de JWT con claim `type: "refresh"`, persistencia en tabla `user_refresh_tokens` con `revoked = False`, verificación de firma y clave secreta `SECRET_KEY`, generación de claims `jti` únicos.

---

### Flujo 2: Protección contra Replay Attack — Invalidez de Refresh Token Reutilizado 🔴 Crítica

> **Precondición:** Un usuario ha completado exitosamente una rotación de tokens (el token original ahora está revocado en base de datos).  
> **Actor:** Atacante o Cliente Desincronizado  

| Paso | Acción de API | Validación esperada |
|------|---------------|---------------------|
| 1    | `POST /auth/e2e-login` para generar sesión inicial | HTTP 200 OK, almacena `original_refresh_token`. |
| 2    | `POST /auth/refresh` con `original_refresh_token` | HTTP 200 OK, el token rota y el original queda revocado en DB (`revoked = True`). |
| 3    | `POST /auth/refresh` intentando reutilizar `original_refresh_token` | HTTP 401 Unauthorized, mensaje `"Refresh token inválido, expirado o revocado"`, header `WWW-Authenticate: Bearer`. |

```gherkin
  Scenario: Replay attack prevention on already rotated refresh token
    Given a test user "Replay Attack User Test" has already rotated their initial refresh token
    When the client attempts to reuse the previous rotated refresh token
    Then the server should reject the request with HTTP 401 Unauthorized
    And the error detail should indicate "Refresh token inválido, expirado o revocado"
```

**Cobertura implícita:** Verificación del flag `token_record.revoked == True` en base de datos, bloqueo de reutilización de tokens en memoria o DB.

---

### Flujo 3: Cierre de Sesión y Revocación Inmediata de Refresh Token 🔴 Crítica

> **Precondición:** Usuario con sesión activa y refresh token emitido.  
> **Actor:** Usuario Autenticado  

| Paso | Acción de API | Validación esperada |
|------|---------------|---------------------|
| 1    | `POST /auth/e2e-login` para emitir credenciales de prueba | HTTP 200 OK con `refresh_token`. |
| 2    | `POST /auth/logout` con body `{"refresh_token": "<refresh_token>"}` | HTTP 200 OK, mensaje `"Sesión cerrada exitosamente"`. |
| 3    | `POST /auth/refresh` intentando refrescar con el token deslogueado | HTTP 401 Unauthorized, revocación efectiva. |

```gherkin
  Scenario: User logout revokes the refresh token permanently
    Given a test user "Logout Revocation User Test" has an active session with a refresh token
    When the user sends a logout request to "/auth/logout" with their refresh token
    Then the server should return HTTP 200 with "Sesión cerrada exitosamente"
    And attempting to refresh session with the logged-out token should return HTTP 401 Unauthorized
```

**Cobertura implícita:** Actualización de registro en base de datos en `/auth/logout`, manejo de peticiones de logout con o sin token.

---

### Flujo 4: Rechazo por Discrepancia de Tipo de Token (Token Type Confusion) 🟡 Alta

> **Precondición:** Usuario con par de tokens legítimos emitidos.  
> **Actor:** Atacante o Cliente con manipulación de payloads  

| Paso | Acción de API | Validación esperada |
|------|---------------|---------------------|
| 1    | `POST /auth/e2e-login` para obtener `access_token` y `refresh_token` | HTTP 200 OK. |
| 2    | `POST /auth/refresh` enviando el `access_token` en el campo `refresh_token` | HTTP 401 Unauthorized (claim `type` es `"access"`, no `"refresh"`). |
| 3    | `GET /usuarios/status` enviando `Authorization: Bearer <refresh_token>` | HTTP 401 Unauthorized (middleware `get_current_user` rechaza tokens con `type != "access"`). |

```gherkin
  Scenario: Enforcement of strict token type segregation
    Given a test user "Type Confusion User Test" possesses both access and refresh tokens
    When the client sends an access token to the "/auth/refresh" endpoint
    Then the server should reject the request with HTTP 401 Unauthorized
    When the client uses the refresh token as a Bearer authorization token on "/usuarios/status"
    Then the server should reject the request with HTTP 401 Unauthorized
```

**Cobertura implícita:** Validación de claim `type` en `jwt.decode()`, aislamiento estricto de roles de tokens.

---

### Flujo 5: Resiliencia ante Payloads Inválidos, Malformados y Falsificados (Checklist Negativo) 🟡 Alta

> **Precondición:** Servidor backend en ejecución.  
> **Actor:** Cliente anónimo / Malicioso  

| Paso | Acción de API | Validación esperada |
|------|---------------|---------------------|
| 1    | `POST /auth/refresh` con body vacío `{}` | HTTP 422 Unprocessable Entity (error de esquema Pydantic). |
| 2    | `POST /auth/refresh` con `{"refresh_token": ""}` | HTTP 401 Unauthorized (token vacío rechazado). |
| 3    | `POST /auth/refresh` con string basura `{"refresh_token": "malformed.jwt.token"}` | HTTP 401 Unauthorized (fallo en decode PyJWT). |
| 4    | `POST /auth/refresh` con token firmado con clave ajena/falsificada | HTTP 401 Unauthorized (firma criptográfica inválida). |
| 5    | `POST /auth/refresh` con JWT válido estructuralmente pero inexistente en DB | HTTP 401 Unauthorized (no existe registro en `user_refresh_tokens`). |

```gherkin
  Scenario Outline: Rejection of malformed, invalid, or forged refresh tokens
    When a request is sent to "/auth/refresh" with <scenario_condition>
    Then the response status code should be <expected_status>

    Examples:
      | scenario_condition                  | expected_status |
      | an empty json payload               | 422             |
      | an empty string refresh token       | 401             |
      | a malformed random string           | 401             |
      | a forged token with an invalid signature | 401        |
      | a valid JWT not registered in the database | 401       |
```

**Cobertura implícita:** Manejo de excepciones `PyJWTError`, validadores Pydantic en `RefreshTokenRequest`, consulta existencial en `db.query(UserRefreshToken)`.

---

## 3. Reconciliación de Cobertura API (Zero-Gap)

| Endpoint | Método | Flujos que lo cubren | Tipo de Cobertura |
|----------|--------|----------------------|-------------------|
| `/auth/e2e-login` | `POST` | Flujos 1, 2, 3, 4 | Setup y emisión inicial de credenciales |
| `/auth/refresh` | `POST` | Flujos 1, 2, 3, 4, 5 | Happy Path, Replay Attack, Revocación, Tipo inválido, Tokens malformados |
| `/auth/logout` | `POST` | Flujo 3 | Revocación en base de datos |
| `/usuarios/status` | `GET` | Flujos 1, 4 | Validación de validez de nuevo access token y rechazo de refresh token |

---

## 4. Mapeo Flujo → Archivos BDD (Estructura Modular)

> **Regla Arquitectónica:** Cumpliendo con el estándar modular, los archivos se organizan dentro del submódulo `auth/`:

| Componente | Ruta Relativa | Propósito |
|------------|---------------|-----------|
| **Feature (Gherkin)** | `features/auth/refresh_token_lifecycle.feature` | Especificación de los 5 escenarios BDD en inglés. |
| **Step Definitions** | `tests/e2e/auth/test_refresh_token_lifecycle.py` | Implementación de `@given`, `@when`, `@then` con requests reales. |
| **API Client Helper** | `utils/api_testing.py` (métodos extendidos de auth) | Encapsulamiento de llamadas `refresh_token` y `logout` (DRY). |
| **Fixtures Requeridos**| `tests/e2e/conftest.py` / `shared_data` | Fixture `shared_data` para compartir tokens y `backend_api` (APIUtils). |
| **Teardown** | `utils/db_teardown.py` | Eliminación de usuarios que terminen en `"Test"` y sus tokens asociados (`CASCADE`). |

---

## 5. Estrategia de Teardown y Cero Contaminación

- Todos los usuarios de prueba creados en los escenarios se llamarán `"... User Test"`.
- La tabla `user_refresh_tokens` tiene configurada la llave foránea con `ondelete="CASCADE"` hacia `users.id`, por lo que al purgar el usuario de prueba al finalizar la sesión de pruebas, se limpian automáticamente todos sus tokens registrados sin dejar registros huérfanos.

---

## 6. Estado de Ejecución y Cobertura Verificada

- [x] Crear directorio `features/auth/`
- [x] Crear directorio `tests/e2e/auth/`
- [x] Escribir archivo de especificación `features/auth/refresh_token_lifecycle.feature` con los 9 escenarios BDD
- [x] Incorporar métodos auxiliares `refresh_token()`, `logout()` y `get_user_status()` en `utils/api_testing.py`
- [x] Implementar step definitions en `tests/e2e/auth/test_refresh_token_lifecycle.py`
- [x] Actualizar endpoint backdoor de teardown `/e2e/cleanup-test-data` para purgar `user_refresh_tokens`
- [x] Ejecutar la suite con `venv/bin/pytest tests/e2e/auth/test_refresh_token_lifecycle.py -v`
- [x] Verificar que no haya warnings ni dependencias de mocking (9/9 PASSED en 1.32s, Global Teardown 200 OK)

### 🔍 Resumen de Resultados:
- `test_successful_refresh_token_rotation`: **PASSED** ✅
- `test_replay_attack_prevention`: **PASSED** ✅
- `test_user_logout_revocation`: **PASSED** ✅
- `test_strict_token_type_segregation`: **PASSED** ✅
- `test_rejection_empty_payload`: **PASSED** ✅
- `test_rejection_empty_string_token`: **PASSED** ✅
- `test_rejection_malformed_token`: **PASSED** ✅
- `test_rejection_forged_signature`: **PASSED** ✅
- `test_rejection_unregistered_jwt`: **PASSED** ✅
- **Global Teardown:** Cleanup exitoso (8 usuarios de test y sus refresh tokens purgados).

