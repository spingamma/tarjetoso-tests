# Lote 02 — Gestión de Equipo de Vendedores (Staff Management)

| Campo | Valor |
| :--- | :--- |
| Módulo | `business_management` |
| Flujos | 1. Búsqueda de candidato, confirmación y alta de colaboradores hasta cupo máximo (2/2)<br>2. Vector de descarte del submodal y eliminación de colaborador con liberación de cupo<br>3. Restricciones RBAC: Negocio estándar/gratuito y usuarios no propietarios<br>4. Búsqueda por coincidencia parcial (contains) y selección de hasta 2 resultados más cercanos |
| Pytest | `pytest tests/e2e/business_management/test_team_management.py -v` |
| Bug Reports | Ninguno activo |

---

## Journeys del Lote

### 1. Búsqueda de candidato, confirmación y alta de colaboradores hasta cupo máximo [Prioridad: 🔴 Crítica]

> **Precondición:** Negocio con Plan Premium activo. Existen en el sistema un usuario comprador registrado ("Colaborador Uno Test") y un segundo usuario registrado ("Colaborador Dos Test").  
> **Actor:** Dueño del negocio (`owner`).

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Dueño inicia sesión y navega a su perfil `/perfil/{slug}` **[UI]** | El botón "Gestionar equipo" (`data-testid="open-team-modal-btn"`) es visible en el banner/hero de la plantilla **[UI]**. |
| 2 | Dueño hace clic en "Gestionar equipo" **[UI]** | Se abre el modal `TeamManagementModal` (`data-testid="team-management-modal"`) con el contador en `0 / 2` **[UI]**. |
| 3 | Dueño escribe un teléfono o email inexistente en el buscador y hace clic en Buscar **[UI]** | La API `GET /businesses/{slug}/staff/search-user` retorna 404 Not Found **[API]**. El modal renderiza el mensaje de error: `"Usuario no encontrado. El colaborador debe estar registrado..."` **[UI]**. |
| 4 | Dueño escribe su propio correo/teléfono y busca **[UI]** | Al intentar agregarse, el backend rechaza con 400 Bad Request: `"El dueño del negocio ya cuenta con todos los accesos."` **[API]**. |
| 5 | Dueño escribe el correo de "Colaborador Uno Test" y busca **[UI]** | La API retorna 200 con `UserCandidateResponse` **[API]**. La UI despliega la tarjeta de vista previa con nombre y datos del candidato **[UI]**. |
| 6 | Dueño hace clic en "Agregar al Equipo" (`data-testid="confirm-add-staff-btn"`) **[UI]** | Petición `POST /businesses/{slug}/staff` retorna 200 con `BusinessStaffResponse` **[API]**. El nuevo colaborador aparece en la lista visual con sus permisos por defecto **[UI]**. El contador superior se actualiza a `1 / 2` **[UI]**. |
| 7 | Dueño busca y agrega a "Colaborador Dos Test" **[UI]** | Petición `POST` retorna 200 **[API]**. El contador se actualiza a `2 / 2` **[UI]**. El formulario de búsqueda se oculta y se muestra el banner de advertencia: `"Has alcanzado el límite máximo de 2 colaboradores..."` **[UI]**. |
| 8 | Intento forzado vía API de agregar un tercer colaborador **[API]** | Endpoint retorna 400 Bad Request con mensaje de límite alcanzado (`MAX_STAFF_LIMIT = 2`) **[API]**. |

- **Feature:** `features/business_management/team_management.feature`
- **Steps:** `tests/e2e/business_management/test_team_management.py`
- **POMs:** `poms/profile_page.py`, `poms/team_management_modal_page.py`
- **Requerimientos cubiertos:** `REQ-STAFF-01`, `REQ-STAFF-02`, `REQ-STAFF-03`
- **Cobertura implícita:** Asignación inicial de permisos por defecto (`can_manage_orders=True`, `can_direct_sale=True`, `can_toggle_open=True`, `can_view_metrics=False`).

---

### 2. Vector de descarte del submodal y eliminación de colaborador con liberación de cupo [Prioridad: 🟡 Alta]

> **Precondición:** Negocio Premium con 2 colaboradores vinculados (cupo al 100%).  
> **Actor:** Dueño del negocio (`owner`).

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Dueño abre el modal de gestión de equipo en `/perfil/{slug}` **[UI]** | Modal visible con 2 colaboradores listados y banner de cupo lleno **[UI]**. |
| 2 | Dueño hace clic en el botón de cierre "X" (`data-testid="close-team-modal-btn"`) o presiona la tecla Escape **[UI]** | El submodal de gestión de equipo se cierra completamente (`expect(modal).not_to_be_visible()`) **[UI]**. El contenedor padre (perfil / hero del negocio) permanece visible, interactivo y con su estado intacto **[UI]**. |
| 3 | Dueño vuelve a abrir el modal y expande el acordeón de permisos de "Colaborador Uno Test" (`data-testid="toggle-permissions-{id}"`) **[UI]** | Se despliegan los 7 toggles de permisos granulares (`can_manage_orders`, `can_receive_payment_notifications`, `can_direct_sale`, etc.) **[UI]**. |
| 4 | Dueño hace clic en el botón de eliminar colaborador (`data-testid="remove-staff-{id}"`) **[UI]** | Petición `DELETE /businesses/{slug}/staff/{id}` retorna 200 OK **[API]**. El registro se elimina de la tabla `business_staff` en la base de datos **[DB]**. |
| 5 | Dueño observa la reactivación del flujo en el modal **[UI]** | El colaborador eliminado desaparece de la lista **[UI]**. El contador desciende a `1 / 2` **[UI]**. El formulario de búsqueda de candidatos vuelve a estar habilitado y visible para admitir un nuevo reemplazo **[UI]**. |

- **Feature:** `features/business_management/team_management.feature`
- **Steps:** `tests/e2e/business_management/test_team_management.py`
- **POMs:** `poms/profile_page.py`, `poms/team_management_modal_page.py`
- **Requerimientos cubiertos:** `REQ-STAFF-04`, `REQ-STAFF-05`
- **Cobertura implícita:** Prevención de fugas de eventos (`event bubbling`) en el backdrop del modal.

---

### 3. Restricciones RBAC: Negocio estándar/gratuito y usuarios no propietarios [Prioridad: 🔴 Crítica]

> **Precondición:** Existe un negocio con Plan Gratuito (Standard) y usuarios sin rol de dueño (visitante / comprador).  
> **Actor:** Dueño de negocio gratuito y Usuario no autorizado.

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Dueño de negocio gratuito navega a su perfil `/perfil/{slug}` **[UI]** | El botón "Gestionar equipo" NO se renderiza en la interfaz (`expect(btn).not_to_be_visible()`) **[UI]**. |
| 2 | Dueño de negocio gratuito intenta invocar directamente `POST /businesses/{slug}/staff` **[API]** | Backend rechaza la petición con código 403 Forbidden: `"La gestión de colaboradores es una función exclusiva para negocios con Plan Premium activo."` **[API]**. |
| 3 | Usuario cliente autenticado (no dueño) intenta listar colaboradores vía `GET /businesses/{slug}/staff` **[API]** | Backend rechaza con 403 Forbidden: `"Solo el dueño del negocio puede gestionar el equipo de colaboradores"` **[API]**. |
| 4 | Colaborador activo del negocio intenta invocar la eliminación de otro colaborador vía `DELETE` **[API]** | Backend rechaza con 403 Forbidden por no ser el propietario del negocio **[API]**. |

- **Feature:** `features/business_management/team_management.feature`
- **Steps:** `tests/e2e/business_management/test_team_management.py`
- **POMs:** `poms/profile_page.py`
- **Requerimientos cubiertos:** `REQ-STAFF-01`
- **Cobertura implícita:** Blindaje de seguridad en todos los métodos HTTP (`GET`, `POST`, `PATCH`, `DELETE`) del router `/businesses/{slug}/staff`.

---

### 4. Búsqueda por coincidencia parcial (contains) y selección de hasta 2 resultados más cercanos [Prioridad: 🟡 Alta]

> **Precondición:** Negocio Premium activo. Existen al menos 3 usuarios registrados en el sistema.  
> **Actor:** Dueño del negocio (`owner`).

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Dueño abre modal de gestión de equipo en `/perfil/{slug}` **[UI]** | Modal renderiza campo de búsqueda con placeholder `"Buscar por nombre, usuario o teléfono..."` **[UI]**. |
| 2 | Dueño escribe un fragmento compartido por múltiples usuarios (contains) **[UI]** | La API `GET /businesses/{slug}/staff/search-user?query=...` retorna status 200 con `List[UserCandidateResponse]` (máximo 2 resultados) **[API]**. |
| 3 | Dueño verifica resultados en el modal **[UI]** | Se despliegan exactamente hasta 2 tarjetas de previsualización individuales con nombre, email/teléfono y botón propio de confirmación **[UI]**. |
| 4 | Dueño busca término específico para un candidato y confirma adición **[UI]** | El candidato seleccionado se agrega al equipo y se refleja en la lista con contador actualizado **[UI]**. |

- **Feature:** `features/business_management/team_management.feature`
- **Steps:** `tests/e2e/business_management/test_team_management.py`
- **POMs:** `poms/profile_page.py`, `poms/team_management_modal_page.py`
- **Requerimientos cubiertos:** `REQ-STAFF-02`

---

## Mapeo a Tríada BDD (Feature + Steps + POM/Cliente) y Fixtures

| Flujo | Feature | Test / Steps | POMs / Clientes Requeridos | Fixtures Requeridos |
| :--- | :--- | :--- | :--- | :--- |
| 1. Alta de Colaboradores y Límite | `features/business_management/team_management.feature` | `tests/e2e/business_management/test_team_management.py` | `profile_page.py`, `team_management_modal_page.py` | `backend_api`, `shared_data` |
| 2. Vector Descarte y Baja de Staff | `features/business_management/team_management.feature` | `tests/e2e/business_management/test_team_management.py` | `profile_page.py`, `team_management_modal_page.py` | `backend_api`, `shared_data` |
| 3. Blindaje RBAC y Plan Gratuito | `features/business_management/team_management.feature` | `tests/e2e/business_management/test_team_management.py` | `profile_page.py` | `backend_api`, `shared_data` |
| 4. Búsqueda Contains y 2 Cercanos | `features/business_management/team_management.feature` | `tests/e2e/business_management/test_team_management.py` | `profile_page.py`, `team_management_modal_page.py` | `backend_api`, `shared_data` |

---

## Checklist de Ejecución

- [x] Tríada creada en disco (`team_management.feature`, `test_team_management.py`, `team_management_modal_page.py`)
- [x] Suite del lote ejecutada (Fecha: 2026-10-03, Ambiente: local)
- [x] Resultado: 4 passed / 0 failed / 0 xfail / 0 skipped
- [x] Teardown verificado (usuarios y negocios creados terminan en `*Test` y se limpian)
- [x] Bugs pendientes del lote: ninguno activo
