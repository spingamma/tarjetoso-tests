# TEST_PLAN_ORDERS

| Campo | Valor |
| :--- | :--- |
| Dominio | `orders` |
| Fuente de Verdad | `ops/docs/03-backend.md`, `ops/docs/04-frontend.md`, `spinjob-backend/services/order_service.py`, `spinjob-fronted/src/utils/deliveryCalculator.js` |
| Cobertura API | `/businesses/{slug}/orders`, `/orders/{id}/receipt`, `/orders/{id}/verify-payment`, `/orders/{id}/reject-payment`, `/delivery/orders/available`, `/delivery/orders/{id}/claim`, `/delivery/orders/{id}/deliver`, `/delivery/orders/{id}/location`, `/delivery/my-orders`, `/delivery/my-summary` |
| Comando de Suite | `pytest tests/e2e/test_order_push.py tests/e2e/test_payment_notifications.py tests/e2e/orders/test_orders_delivery_mode.py tests/e2e/orders/test_delivery_dispatch_board.py tests/e2e/orders/test_delivery_dashboard_ui.py -v` |

---

## Resumen de Cobertura Esperada

| Métrica | Cantidad |
| :--- | ---: |
| Requerimientos / Criterios totales | 18 |
| Con lote (tríada en disco o en diseño) | 18 |
| Con journey, sin lote | 0 |
| Pendiente de automatización | 0 |
| No testeable E2E (Unitario / Infra pura) | 0 |

---

## Lotes de Automatización

| Lote | Journeys Cubiertos | Ejecución |
| :--- | :--- | :--- |
| [01 Notificaciones Push de Pago y Ciclo CX](lotes/LOTE_01_notificaciones_push_pago.md) | Silenciado de creación, Alerta dólar comprobante, Aceptación y Rechazo con motivo | Ejecutado (2026-10-03, 6 passed) |
| [02 Modo Delivery Geolocalizado](lotes/LOTE_02_modo_delivery_geolocalizado.md) | Cotización Leaflet, Sinuosidad 1.8x/OSRM, Búsqueda Maps en modal, Bloqueo sin coordenadas, Vector de descarte, Invariante catálogo | Ejecutado (6 passed) |
| [03 Tablero de Despachos y Ciclo de Reparto Multi-Negocio](lotes/LOTE_03_tablero_despacho_delivery.md) | Reemplazo Navegación y Semáforo Distancias (0-3km Verde, 3-8km Amarillo, >8km Rojo Bloqueado), Toma Atómica y Descarte Modal Entrega, Liquidación con Filtro de Fechas | Ejecutado (4 passed: 1 API + 3 BDD UI) |

---

## Matriz de Trazabilidad (Requerimientos → Journeys)

| ID / Requerimiento | Prioridad | Journey Esperado | Feature Esperado | Lote Asignado |
| :--- | :--- | :--- | :--- | :--- |
| `REQ-ORD-PUSH-01` (Creación Silenciosa de Pedido) | 🔴 Crítica | Al crear pedido `pendiente_de_pago`, no se envía push al dueño | `features/order_push_notifications.feature` | [LOTE 01](lotes/LOTE_01_notificaciones_push_pago.md) |
| `REQ-ORD-PUSH-02` (Opt-out Notificaciones) | 🟡 Alta | Dueño desactiva toggle de push y deja de recibir alertas | `features/order_push_notifications.feature` | [LOTE 01](lotes/LOTE_01_notificaciones_push_pago.md) |
| `REQ-ORD-PUSH-03` (Resiliencia sin Suscripción) | ⚪ Media | Pedido exitoso cuando el dueño no tiene suscripción push activa | `features/order_push_notifications.feature` | [LOTE 01](lotes/LOTE_01_notificaciones_push_pago.md) |
| `REQ-ORD-PAY-01` (Alerta Dólar Comprobante) | 🔴 Crítica | Push con icono dólar y monto al comerciante al subir comprobante | `features/payment_notifications.feature` | [LOTE 01](lotes/LOTE_01_notificaciones_push_pago.md) |
| `REQ-ORD-PAY-02` (Confirmación Pago al Cliente) | 🔴 Crítica | Push de aceptación al cliente indicando pedido en preparación | `features/payment_notifications.feature` | [LOTE 01](lotes/LOTE_01_notificaciones_push_pago.md) |
| `REQ-ORD-PAY-03` (Rechazo de Comprobante con Motivo) | 🟡 Alta | Push de rechazo al cliente con motivo y reintento con nueva foto | `features/payment_notifications.feature` | [LOTE 01](lotes/LOTE_01_notificaciones_push_pago.md) |
| `REQ-ORD-DELIV-01` (Cotización Dinámica y Persistencia) | 🔴 Crítica | Cotización Leaflet en checkout (4.50 Bs/km), guardado en orden y vista dueño con mapa | `features/orders/orders_delivery_mode.feature` | [LOTE 02](lotes/LOTE_02_modo_delivery_geolocalizado.md) |
| `REQ-ORD-DELIV-02` (Bloqueo Checkout sin Coordenadas) | 🟡 Alta | Alerta informativa y deshabilitación de checkout si negocio no tiene coordenadas | `features/orders/orders_delivery_mode.feature` | [LOTE 02](lotes/LOTE_02_modo_delivery_geolocalizado.md) |
| `REQ-ORD-DELIV-03` (Vector Descarte Mapa Leaflet) | 🟡 Alta | Cierre de submodal de mapa sin confirmar preservando intacto el formulario padre | `features/orders/orders_delivery_mode.feature` | [LOTE 02](lotes/LOTE_02_modo_delivery_geolocalizado.md) |
| `REQ-ORD-DELIV-04` (Invariante Catálogo Mínimo 1) | 🟡 Alta | Bloqueo al intentar desmarcar ambos métodos y sincronización select checkout | `features/orders/orders_delivery_mode.feature` | [LOTE 02](lotes/LOTE_02_modo_delivery_geolocalizado.md) |
| `REQ-ORD-DELIV-05` (Búsqueda por Enlace Maps en Modal) | 🟡 Alta | Resolución automática de coordenadas al pegar enlaces `maps.app.goo.gl` o formato web en el modal de mapa | `features/orders/orders_delivery_mode.feature` | [LOTE 02](lotes/LOTE_02_modo_delivery_geolocalizado.md) |
| `REQ-ORD-DELIV-06` (Factor de Sinuosidad Urbana 1.8x / OSRM) | 🔴 Crítica | Cálculo vial con estimación de topografía de montaña (1.8x) y ruta OSRM superando la distancia recta euclidiana | `features/orders/orders_delivery_mode.feature` | [LOTE 02](lotes/LOTE_02_modo_delivery_geolocalizado.md) |
| `REQ-DELIV-BOARD-01` (Navegación Exclusiva Delivery) | 🔴 Crítica | Enlace moto `/tablero-delivery` reemplaza botón 'Mis Negocios' para usuarios repartidores | `features/orders/delivery_dispatch_board.feature` | [LOTE 03](lotes/LOTE_03_tablero_despacho_delivery.md) |
| `REQ-DELIV-TIER-01` (Semáforo de Distancias 3 Zonas) | 🔴 Crítica | 0-3km Verde (habilitado), 3-8km Amarillo (habilitado), >8km Rojo con botón bloqueado y advertencia | `features/orders/delivery_dispatch_board.feature` | [LOTE 03](lotes/LOTE_03_tablero_despacho_delivery.md) |
| `REQ-DELIV-CLAIM-01` (Toma Atómica de Pedido) | 🔴 Crítica | Asignación atómica en backend (`en_camino`), desaparición del listado disponible y 409 amigable ante colisión | `features/orders/delivery_dispatch_board.feature` | [LOTE 03](lotes/LOTE_03_tablero_despacho_delivery.md) |
| `REQ-DELIV-DISMISS-01` (Vector Descarte Modal Entrega) | 🟡 Alta | Botón 'Aún no' descarta modal sin side-effects conservando pedido activo en tránsito | `features/orders/delivery_dispatch_board.feature` | [LOTE 03](lotes/LOTE_03_tablero_despacho_delivery.md) |
| `REQ-DELIV-CONFIRM-01` (Confirmación de Entrega Sin Fricción) | 🔴 Crítica | Entrega directa sin PIN mediante confirmación visual, transición a `entregado` y toast de éxito | `features/orders/delivery_dispatch_board.feature` | [LOTE 03](lotes/LOTE_03_tablero_despacho_delivery.md) |
| `REQ-DELIV-REPORT-01` (Liquidación con Rango de Fechas) | 🟡 Alta | Resumen de carreras completadas y ganancias acumuladas con botones de filtro rápido (Hoy, Semana, Mes) | `features/orders/delivery_dispatch_board.feature` | [LOTE 03](lotes/LOTE_03_tablero_despacho_delivery.md) |
