# Lote 01 — Notificaciones Push Centradas en el Pago y Ciclo CX

| Campo | Valor |
| :--- | :--- |
| Módulo | `orders` |
| Flujos | 1. Silenciado de push en la creación de pedido (Actionable Push)<br>2. Ciclo completo de notificaciones de pago (Alerta Dólar y Confirmación al Cliente)<br>3. Observación/Rechazo de comprobante con motivo y reintento de subida |
| Pytest | `pytest tests/e2e/test_order_push.py tests/e2e/test_payment_notifications.py -v` |
| Bug Reports | Ninguno activo |

---

## Journeys del Lote

### 1. Silenciado de push en la creación de pedido (Actionable Push) [Prioridad: 🔴 Crítica]

> **Precondición:** Dueño de negocio con suscripción push activa. Cliente comprador navegando en el perfil.  
> **Actor:** Cliente comprador y Dueño del negocio (`owner`).

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Cliente selecciona productos del catálogo y confirma el checkout **[UI]** | Petición `POST /orders` retorna 200 con la orden en estado `pendiente_de_pago` **[API]**. |
| 2 | Verificación de silencio en el dispositivo del dueño **[API]** | El backend NO envía ninguna notificación push al dueño mientras no exista pago (`mock_push.assert_not_called()`) **[API]**. |
| 3 | Dueño consulta `/mis-pedidos/{slug}` **[UI]** | El pedido existe en el listado y reserva stock, pero no generó alertas invasivas prematuras **[UI]**. |

- **Feature:** `features/order_push_notifications.feature`
- **Steps:** `tests/e2e/test_order_push.py`
- **POMs:** `poms/checkout_page.py`, `poms/business_orders_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-PUSH-01`, `REQ-ORD-PUSH-02`, `REQ-ORD-PUSH-03`
- **Cobertura implícita:** Supresión del webhook/push de creación en `crear_pedido_service`.

---

### 2. Ciclo completo de notificaciones de pago [Prioridad: 🔴 Crítica]

> **Precondición:** Negocio Premium con pagos QR configurados. Cliente comprador con suscripción push activa.  
> **Actor:** Cliente comprador y Comerciante (`owner`).

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Cliente realiza pedido con modalidad Transferencia / QR y sube imagen de comprobante bancario **[UI]** | Petición `POST /orders/{id}/receipt` cambia el estado de la orden a `pago_enviado` **[API]**. |
| 2 | Verificación de despacho al comerciante **[API]** | El comerciante recibe la notificación push con título `"💲 ¡Pago Enviado!"`, detalle del monto e icono distintivo de dólar `/dollar-notification.png` **[API]**. La URL de clic redirige a `/mis-pedidos/{slug}` **[API]**. |
| 3 | Comerciante valida el pago en su banca y hace clic en "Marcar como Pagado" **[UI]** | Petición `PATCH /orders/{id}/verify-payment` retorna 200 con estado `pagado` **[API]**. |
| 4 | Verificación de despacho al cliente **[API]** | El cliente comprador recibe notificación push: `"✅ ¡Tu pago ha sido aceptado!"`, avisando que su pedido entró en preparación **[API]**. La URL redirige al seguimiento `/perfil/{slug}/orden/{order_id}` **[API]**. |

- **Feature:** `features/payment_notifications.feature`
- **Steps:** `tests/e2e/test_payment_notifications.py`
- **POMs:** `poms/order_tracking_page.py`, `poms/business_orders_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-PAY-01`, `REQ-ORD-PAY-02`
- **Cobertura implícita:** Verificación de payloads Push con claves `title`, `body`, `icon` y `url`.

---

### 3. Observación/Rechazo de comprobante con motivo y reintento [Prioridad: 🟡 Alta]

> **Precondición:** Pedido en estado `pago_enviado` con comprobante ilegible.  
> **Actor:** Comerciante (`owner`) y Cliente comprador.

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Comerciante rechaza el comprobante ingresando el motivo: `"Comprobante ilegible"` **[UI]** | Petición `PATCH /orders/{id}/reject-payment` retorna 200. El pedido regresa al estado `pendiente_de_pago` y el URL del recibo se limpia **[API + DB]**. |
| 2 | Verificación de notificación de observación al cliente **[API]** | El cliente recibe alerta push: `"❌ Comprobante observado: Comprobante ilegible"` invitándolo a subir un nuevo comprobante **[API]**. |
| 3 | Cliente abre `/perfil/{slug}/orden/{order_id}` y sube una foto nítida del comprobante **[UI]** | El pedido pasa nuevamente a `pago_enviado` **[API]**. Se despacha una nueva alerta de pago al comerciante **[API]**. |
| 4 | Comerciante aprueba el nuevo comprobante **[UI]** | El pedido pasa a `pagado` y el cliente recibe su confirmación exitosa **[API]**. |

- **Feature:** `features/payment_notifications.feature`
- **Steps:** `tests/e2e/test_payment_notifications.py`
- **POMs:** `poms/order_tracking_page.py`, `poms/business_orders_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-PAY-03`
- **Cobertura implícita:** Resiliencia y feedback loop ante pagos observados sin perder la orden original.

---

## Mapeo a Tríada BDD (Feature + Steps + POM/Cliente) y Fixtures

| Flujo | Feature | Test / Steps | POMs / Clientes Requeridos | Fixtures Requeridos |
| :--- | :--- | :--- | :--- | :--- |
| 1. Creación Silenciosa | `features/order_push_notifications.feature` | `tests/e2e/test_order_push.py` | `checkout_page.py`, `business_orders_page.py` | `backend_api`, `shared_data` |
| 2. Ciclo Notificaciones Pago | `features/payment_notifications.feature` | `tests/e2e/test_payment_notifications.py` | `order_tracking_page.py`, `business_orders_page.py` | `backend_api`, `shared_data` |
| 3. Rechazo y Reintento | `features/payment_notifications.feature` | `tests/e2e/test_payment_notifications.py` | `order_tracking_page.py`, `business_orders_page.py` | `backend_api`, `shared_data` |

---

## Checklist de Ejecución

- [x] Tríada creada en disco (`order_push_notifications.feature`, `payment_notifications.feature`, `test_order_push.py`, `test_payment_notifications.py`)
- [x] Suite del lote ejecutada (Fecha: 2026-10-03, Ambiente: local)
- [x] Resultado: 6 passed / 0 failed / 0 xfail / 0 skipped
- [x] Teardown verificado (entidades generadas terminan en `*Test` y se limpian)
- [x] Bugs pendientes del lote: ninguno activo
