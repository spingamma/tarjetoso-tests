# TEST_PLAN_BUSINESS_MANAGEMENT

| Campo | Valor |
| :--- | :--- |
| Dominio | `business_management` |
| Fuente de Verdad | `ops/docs/03-backend.md`, `ops/flows/flows.json`, `spinjob-backend/routers/business_staff.py`, `spinjob-fronted/src/plantillas/components/TeamManagementModal.jsx` |
| Cobertura API | `/businesses/{slug}/toggle-open`, `/businesses/{slug}/staff`, `/businesses/{slug}/staff/search-user`, `/businesses/{slug}/staff/{id}`, `/user/mis-negocios`, `/orders/direct-sale` |
| Comando de Suite | `pytest tests/e2e/business_management/ -v` |

---

## Resumen de Cobertura Esperada

| Métrica | Cantidad |
| :--- | ---: |
| Requerimientos / Criterios totales | 13 |
| Con lote (tríada en disco o en diseño) | 13 |
| Con journey, sin lote | 0 |
| Pendiente de automatización | 0 |
| No testeable E2E (Unitario / Infra pura) | 0 |

---

## Lotes de Automatización

| Lote | Journeys Cubiertos | Ejecución |
| :--- | :--- | :--- |
| [01 Negocio Apertura y Cierre](lotes/LOTE_01_apertura_cierre.md) | Toggle perfil, Grayscale visitante, WhatsApp en pedidos | Ejecutado (2026-10-01, 3 passed) |
| [02 Gestión de Equipo de Vendedores](lotes/LOTE_02_gestion_equipo_vendedores.md) | Alta de colaboradores, límite de 2, candidate preview, vector descarte modal, baja, búsqueda contains 2 más cercanos | Ejecutado (2026-10-03, 4 passed) |
| [03 Permisos RBAC y Operativa Staff](lotes/LOTE_03_operativa_rbac_staff_pedidos.md) | Vista `/mis-negocios`, toggle staff, atención de órdenes `handled_by`, push multi-equipo | Ejecutado (2026-10-03, 3 passed) |

---

## Matriz de Trazabilidad (Requerimientos → Journeys)

| ID / Requerimiento | Prioridad | Journey Esperado | Feature Esperado | Lote Asignado |
| :--- | :--- | :--- | :--- | :--- |
| `REQ-BIZ-01` (Toggle Abierto/Cerrado) | 🔴 Crítica | Dueño abre/cierra negocio desde perfil y `/mis-negocios` | `features/business_management/business_open_close.feature` | [LOTE 01](lotes/LOTE_01_apertura_cierre.md) |
| `REQ-BIZ-02` (Grayscale y Bloqueo Pedidos) | 🟡 Alta | Visitante ve letrero "Cerrado", banner en gris y checkout bloqueado | `features/business_management/business_open_close.feature` | [LOTE 01](lotes/LOTE_01_apertura_cierre.md) |
| `REQ-BIZ-03` (WhatsApp en Ciclo de Pedido) | 🟡 Alta | Botón WhatsApp visible en preparación y oculto tras entrega/cancelación | `features/business_management/business_open_close.feature` | [LOTE 01](lotes/LOTE_01_apertura_cierre.md) |
| `REQ-STAFF-01` (Exclusividad Premium Team) | 🔴 Crítica | Acceso a "Gestionar equipo" condicionado a Plan Premium activo | `features/business_management/team_management.feature` | [LOTE 02](lotes/LOTE_02_gestion_equipo_vendedores.md) |
| `REQ-STAFF-02` (Búsqueda y Confirmación de Candidatos) | 🔴 Crítica | Búsqueda por contains (nombre, usuario/email, teléfono), hasta 2 candidatos más cercanos y confirmación | `features/business_management/team_management.feature` | [LOTE 02](lotes/LOTE_02_gestion_equipo_vendedores.md) |
| `REQ-STAFF-03` (Cupo Máximo 2 Colaboradores) | 🔴 Crítica | Contador dinámico (0/2, 1/2, 2/2) y bloqueo estricto al alcanzar el límite | `features/business_management/team_management.feature` | [LOTE 02](lotes/LOTE_02_gestion_equipo_vendedores.md) |
| `REQ-STAFF-04` (Descarte de Submodal sin Colisiones) | 🟡 Alta | Cierre intencional (botón 'X' o backdrop) preservando el contenedor padre | `features/business_management/team_management.feature` | [LOTE 02](lotes/LOTE_02_gestion_equipo_vendedores.md) |
| `REQ-STAFF-05` (Baja de Colaborador y Liberación) | 🟡 Alta | Eliminación de miembro del equipo y reapertura del cupo para nuevas altas | `features/business_management/team_management.feature` | [LOTE 02](lotes/LOTE_02_gestion_equipo_vendedores.md) |
| `REQ-STAFF-06` (Visibilidad en `/mis-negocios`) | 🟡 Alta | Colaborador ve negocio con badge `👥 Colaborador` y restricciones de dueño | `features/business_management/staff_operational_rbac.feature` | [LOTE 03](lotes/LOTE_03_operativa_rbac_staff_pedidos.md) |
| `REQ-STAFF-07` (Toggle Abierto por Colaborador) | 🟡 Alta | Colaborador opera switch de apertura según permiso `can_toggle_open` | `features/business_management/staff_operational_rbac.feature` | [LOTE 03](lotes/LOTE_03_operativa_rbac_staff_pedidos.md) |
| `REQ-STAFF-08` (Trazabilidad `handled_by` en Pedidos) | 🔴 Crítica | Venta directa y verificación de orden registran `handled_by` y badge visual | `features/business_management/staff_operational_rbac.feature` | [LOTE 03](lotes/LOTE_03_operativa_rbac_staff_pedidos.md) |
| `REQ-STAFF-09` (Push Multi-Equipo en Pagos) | 🔴 Crítica | Despacho push con icono dólar a Dueño y colaboradores con permiso activo | `features/business_management/staff_operational_rbac.feature` | [LOTE 03](lotes/LOTE_03_operativa_rbac_staff_pedidos.md) |
| `REQ-STAFF-10` (Aislamiento Métricas / Eliminación) | ⚪ Media | Colaborador sin permiso recibe 403 en métricas y no puede eliminar negocio | `features/business_management/staff_operational_rbac.feature` | [LOTE 03](lotes/LOTE_03_operativa_rbac_staff_pedidos.md) |
