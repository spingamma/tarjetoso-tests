# Lote 03 — Permisos RBAC y Operativa de Pedidos por Colaboradores

| Campo | Valor |
| :--- | :--- |
| Módulo | `business_management` |
| Flujos | 1. Visualización de negocios asignados en `/mis-negocios` y toggle de apertura condicional<br>2. Venta directa y verificación de pedidos con trazabilidad `handled_by`<br>3. Despacho multi-destinatario de notificaciones push de pago al equipo autorizado |
| Pytest | `pytest tests/e2e/business_management/test_staff_operational_rbac.py -v` |
| Bug Reports | Ninguno activo |

---

## Journeys del Lote

### 1. Visualización en `/mis-negocios` y toggle de apertura condicional [Prioridad: 🟡 Alta]

> **Precondición:** Usuario registrado ("Colaborador Operativo Test") ha sido añadido como colaborador en un Negocio Premium ("Restaurante Staff Test") con permisos iniciales por defecto.  
> **Actor:** Colaborador autorizado (`staff`).

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Colaborador inicia sesión y navega a `/mis-negocios` **[UI]** | El negocio "Restaurante Staff Test" aparece en la lista con el badge púrpura `👥 Colaborador` (`data-testid="colaborador-badge"`) **[UI]**. |
| 2 | Colaborador inspecciona las acciones disponibles en la tarjeta **[UI]** | El botón "Ver Tarjeta Pública" y el switch "Abierto/Cerrado" son visibles **[UI]**. Los botones "Métricas" y "Eliminar Solicitud" NO están visibles en la interfaz para el colaborador (`isStaff = true`) **[UI]**. |
| 3 | Colaborador hace clic en el switch de Abierto/Cerrado (`data-testid="toggle-open-{slug}"`) **[UI]** | Petición `PATCH /businesses/{slug}/toggle-open` retorna 200 con `is_open: false` autorizada por `can_toggle_open=True` **[API]**. El switch cambia visualmente al estado "Cerrado" **[UI]**. |
| 4 | Dueño del negocio revoca el permiso `can_toggle_open` mediante `PATCH /businesses/{slug}/staff/{id}` **[API]** | Permiso actualizado en base de datos a `can_toggle_open = false` **[API + DB]**. |
| 5 | Colaborador intenta modificar nuevamente el switch de apertura **[UI]** | Backend rechaza la operación con código 403 Forbidden: `"No tienes permisos para modificar el estado abierto/cerrado de este negocio"` **[API]**. |

- **Feature:** `features/business_management/staff_operational_rbac.feature`
- **Steps:** `tests/e2e/business_management/test_staff_operational_rbac.py`
- **POMs:** `poms/my_businesses_page.py`, `poms/profile_page.py`
- **Requerimientos cubiertos:** `REQ-STAFF-06`, `REQ-STAFF-07`, `REQ-STAFF-10`
- **Cobertura implícita:** Validación de que `get_mis_negocios_service` une negocios propios y aquellos donde el usuario participa como `BusinessStaff`.

---

### 2. Venta directa y verificación de pedidos con trazabilidad `handled_by` [Prioridad: 🔴 Crítica]

> **Precondición:** Colaborador con permisos `can_direct_sale=True` y `can_manage_orders=True`.  
> **Actor:** Colaborador (`staff`), Dueño (`owner`) y Cliente comprador.

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Colaborador navega al perfil del negocio y realiza un pedido en modalidad Venta Directa **[UI]** | Petición `POST /orders` procesa la compra con `is_direct_sale=True` **[API]**. La orden almacena `handled_by = colaborador.id` en la tabla `orders` **[DB]**. |
| 2 | Colaborador ingresa a `/mis-pedidos/{slug}` **[UI]** | La orden registrada muestra el badge de trazabilidad: `Atendido por: Colaborador Operativo Test` **[UI]**. |
| 3 | Cliente comprador anónimo realiza un pedido estándar vía transferencia QR y sube su comprobante **[API + UI]** | El pedido queda registrado en estado `pago_enviado` con `handled_by = null` **[API + DB]**. |
| 4 | Colaborador inspecciona el comprobante en `/mis-pedidos/{slug}` y hace clic en "Aceptar Pago" **[UI]** | Petición `PATCH /orders/{id}/verify-payment` retorna 200 con estado `pagado` **[API]**. El campo `handled_by` del pedido se actualiza con el ID del colaborador que validó el pago **[DB]**. |
| 5 | Dueño del negocio entra a `/mis-pedidos/{slug}` **[UI]** | La tarjeta del pedido exhibe el badge de auditoría indicando qué colaborador atendió la orden **[UI]**. |

- **Feature:** `features/business_management/staff_operational_rbac.feature`
- **Steps:** `tests/e2e/business_management/test_staff_operational_rbac.py`
- **POMs:** `poms/business_orders_page.py`, `poms/order_tracking_page.py`
- **Requerimientos cubiertos:** `REQ-STAFF-08`
- **Cobertura implícita:** Exposición del campo computado `handled_by_name` en el schema `OrderResponse`.

---

### 3. Despacho multi-destinatario de notificaciones push de pago al equipo autorizado [Prioridad: 🔴 Crítica]

> **Precondición:** Negocio Premium con el Dueño y dos colaboradores suscritos a Web Push:  
> - "Staff Alerta ON": tiene `can_receive_payment_notifications = True`  
> - "Staff Alerta OFF": tiene `can_receive_payment_notifications = False`  
> **Actor:** Cliente comprador y Servicio de Notificaciones Push.

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Cliente completa checkout y sube comprobante de pago por QR **[UI]** | La orden pasa a `pago_enviado` **[API]**. |
| 2 | Backend ejecuta `send_push_notification_to_business_team` **[API]** | El servicio consulta los suscriptores elegibles del negocio en la tabla `business_staff` **[DB]**. |
| 3 | Verificación de despacho al Dueño **[API]** | El Dueño recibe la notificación push con icono de dólar y redirección a `/mis-pedidos/{slug}` **[API]**. |
| 4 | Verificación de despacho a "Staff Alerta ON" **[API]** | El colaborador con permiso activo recibe la notificación push con el detalle del pago **[API]**. |
| 5 | Verificación de exclusión a "Staff Alerta OFF" **[API]** | El colaborador con permiso revocado NO recibe ninguna alerta push, respetando la configuración granular del equipo **[API]**. |

- **Feature:** `features/business_management/staff_operational_rbac.feature`
- **Steps:** `tests/e2e/business_management/test_staff_operational_rbac.py`
- **POMs:** `poms/order_tracking_page.py`
- **Requerimientos cubiertos:** `REQ-STAFF-09`
- **Cobertura implícita:** Filtrado por `BusinessStaff.can_receive_payment_notifications.is_(True)` en `push_service.py`.

---

## Mapeo a Tríada BDD (Feature + Steps + POM/Cliente) y Fixtures

| Flujo | Feature | Test / Steps | POMs / Clientes Requeridos | Fixtures Requeridos |
| :--- | :--- | :--- | :--- | :--- |
| 1. Visibilidad `/mis-negocios` y Toggle Staff | `features/business_management/staff_operational_rbac.feature` | `tests/e2e/business_management/test_staff_operational_rbac.py` | `my_businesses_page.py`, `profile_page.py` | `backend_api`, `shared_data` |
| 2. Venta Directa y Trazabilidad `handled_by` | `features/business_management/staff_operational_rbac.feature` | `tests/e2e/business_management/test_staff_operational_rbac.py` | `business_orders_page.py` | `backend_api`, `shared_data` |
| 3. Push Multi-Equipo en Pagos | `features/business_management/staff_operational_rbac.feature` | `tests/e2e/business_management/test_staff_operational_rbac.py` | `order_tracking_page.py` | `backend_api`, `shared_data` |

---

## Checklist de Ejecución

- [x] Tríada creada en disco (`staff_operational_rbac.feature`, `test_staff_operational_rbac.py`, POMs correspondientes)
- [x] Suite del lote ejecutada (Fecha: 2026-10-03, Ambiente: local)
- [x] Resultado: 3 passed / 0 failed / 0 xfail / 0 skipped
- [x] Teardown verificado (entidades generadas terminan en `*Test` y se limpian)
- [x] Bugs pendientes del lote: ninguno activo
