# Lote 03 — Tablero de Despachos y Ciclo de Reparto Multi-Negocio

| Campo | Valor |
| :--- | :--- |
| Módulo | `orders` |
| Flujos | 1. Reemplazo de Navegación por Rol y Semáforo de Distancias (0-3km Verde, 3-8km Amarillo, >8km Rojo Bloqueado)<br>2. Reclamación Atómica de Orden y Vector de Descarte de Confirmación de Entrega<br>3. Reporte de Liquidación de Repartidor con Filtro de Rango de Fechas (Hoy, Semana, Mes) |
| Pytest | `pytest tests/e2e/orders/test_delivery_dispatch_board.py tests/e2e/orders/test_delivery_dashboard_ui.py -v` |
| Bug Reports | Ninguno activo |

---

## Journeys del Lote

### 1. Reemplazo de Navegación y Semáforo de Distancias [Prioridad: 🔴 Crítica]

> **Precondición:** Repartidor autenticado (`is_delivery = True`, `state = 'La Paz'`) con geolocalización activa en La Paz. Órdenes pagadas disponibles en restaurantes cercanos (<3km) y lejanos (>8km).  
> **Actor:** Repartidor Motorizado (`delivery`).

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Repartidor visita la barra de navegación en `/` | El menú despliega el botón de delivery con icono de moto (`/tablero-delivery`) y se oculta el botón 'Mis negocios'. | [UI] |
| 2 | Repartidor navega a `/tablero-delivery` | Carga el Tablero de Despachos en tiempo real con pestañas 'Disponibles' y 'Mis Entregas'. | [UI] |
| 3 | Verificación de orden cercana (<3 km) | La tarjeta de orden muestra badge verde `🟢` con distancia calculada y botón activo `[data-testid='accept-delivery-btn-{id}']`. | [UI] |
| 4 | Verificación de orden lejana (>8 km) | La tarjeta de orden muestra badge rojo `🔴`, botón deshabilitado `[data-testid='blocked-delivery-btn-{id}']` y advertencia informativa: *"Debes estar más cerca para aceptar el pedido"*. | [UI] |

- **Feature:** `features/orders/delivery_dispatch_board.feature` (Scenario: `Delivery role navigation replacement and distance tiering`)
- **Steps:** `tests/e2e/orders/test_delivery_dashboard_ui.py`
- **POMs:** `poms/delivery_dashboard_page.py`
- **Requerimientos cubiertos:** `REQ-DELIV-BOARD-01`, `REQ-DELIV-TIER-01`
- **Cobertura implícita:** Clasificación de semáforo (0-3km verde, 3-8km amarillo, >8km rojo) y cálculo dinámico de distancia restaurante-motorizado.

---

### 2. Reclamación Atómica y Vector de Descarte de Confirmación [Prioridad: 🔴 Crítica]

> **Precondición:** Repartidor autenticado con geolocalización en zona. Orden pagada en estado disponible (`en_preparacion`/`pagado`).  
> **Actor:** Repartidor Motorizado (`delivery`).

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Repartidor presiona botón `[data-testid='accept-delivery-btn-{id}']` | Petición atómica `POST /delivery/orders/{id}/claim`. Retorna 200 OK y asigna `delivery_user_id`. | [API/UI] |
| 2 | Verificación de desaparición en disponibles | El pedido desaparece del listado de órdenes disponibles para todos los repartidores. | [UI] |
| 3 | Conmutación a entregas activas | La vista conmuta a 'Mis Entregas' (subpestaña 'Activas') mostrando la tarjeta con badge `🟢 GPS activo` y estado `En camino al cliente`. | [UI] |
| 4 | Repartidor presiona `[data-testid='deliver-btn-{id}']` | Se despliega modal de confirmación `¿Confirmar Entrega?`. | [UI] |
| 5 | Repartidor presiona `[data-testid='deliver-cancel-btn']` (Vector de Descarte) | Modal se cierra (`expect(modal).not_to_be_visible()`), el contenedor padre permanece intacto y la orden sigue en tránsito. | [UI] |
| 6 | Repartidor presiona de nuevo `[data-testid='deliver-btn-{id}']` y confirma con `[data-testid='deliver-confirm-btn']` | Petición `POST /delivery/orders/{id}/deliver`. La orden pasa a `entregado`, se muestra toast exitoso y se traslada a la subpestaña 'Historial'. | [API/UI] |

- **Feature:** `features/orders/delivery_dispatch_board.feature` (Scenario: `Atomic order claiming and delivery modal dismissal vector`)
- **Steps:** `tests/e2e/orders/test_delivery_dashboard_ui.py`
- **POMs:** `poms/delivery_dashboard_page.py`
- **Requerimientos cubiertos:** `REQ-DELIV-CLAIM-01`, `REQ-DELIV-DISMISS-01`, `REQ-DELIV-CONFIRM-01`
- **Cobertura implícita:** Concurrencia segura de toma de pedidos (409 Conflict si ya fue reclamado) y descarte de submodal sin side-effects.

---

### 3. Reporte de Liquidación con Filtro de Fechas [Prioridad: 🟡 Alta]

> **Precondición:** Repartidor con al menos una carrera completada en el día de hoy.  
> **Actor:** Repartidor Motorizado (`delivery`).

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Repartidor accede a subpestaña 'Historial' | Carga la tarjeta de control de liquidación `DeliveryHistoryControlCard`. | [UI] |
| 2 | Repartidor presiona botón rápido `[data-testid='delivery-filter-today-btn']` | Los inputs de fecha Desde y Hasta se sincronizan con la fecha de hoy (`YYYY-MM-DD`). | [UI] |
| 3 | Verificación de métricas en tarjeta de resumen | La tarjeta `[data-testid='delivery-earnings-summary-card']` exhibe el conteo de carreras completadas (`1 carrera`), ganancia total acumulada en `Bs.` y promedio por carrera. | [UI] |

- **Feature:** `features/orders/delivery_dispatch_board.feature` (Scenario: `Delivery earnings settlement report with date range filtering`)
- **Steps:** `tests/e2e/orders/test_delivery_dashboard_ui.py`
- **POMs:** `poms/delivery_dashboard_page.py`
- **Requerimientos cubiertos:** `REQ-DELIV-REPORT-01`
- **Cobertura implícita:** Endpoints `GET /delivery/my-orders` y `GET /delivery/my-summary` con filtrado por `start_date` y `end_date`.
