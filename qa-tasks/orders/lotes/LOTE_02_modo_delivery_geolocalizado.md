# Lote 02 — Modo Delivery Geolocalizado y Cotización Dinámica

| Campo | Valor |
| :--- | :--- |
| Módulo | `orders` |
| Flujos | 1. Cotización y Pedido Delivery con Mapa Leaflet (Happy Path)<br>2. Bloqueo de Checkout ante Negocio sin Coordenadas de Despacho (Negative Path 1)<br>3. Cancelación del Modal de Mapa y Persistencia de Estado Padre (Vector de Descarte)<br>4. Configuración de Métodos de Entrega en Catálogo e Invariante de Mínimo 1 |
| Pytest | `pytest tests/e2e/orders/test_orders_delivery_mode.py -v` |
| Bug Reports | Ninguno activo |

---

## Journeys del Lote

### 1. Cotización y Pedido Delivery con Mapa Leaflet [Prioridad: 🔴 Crítica]

> **Precondición:** Negocio Premium con `orders_enabled = True`, coordenadas de despacho configuradas (ej. `-17.7833, -63.1821`), y métodos de entrega `["Entrega en el local", "Delivery"]`. Cliente comprador autenticado con productos en carrito.  
> **Actor:** Cliente Comprador y Dueño de Negocio (`owner`).

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Cliente avanza a checkout (`/perfil/:slug/orden`) con productos en carrito | Vista de checkout carga con nombre de cliente y métodos de entrega disponibles. | [UI] |
| 2 | Cliente selecciona "Delivery" en el selector `[data-testid='delivery-method-select']` | Se despliega sección modular `DeliveryLocationSection` solicitando ubicación de destino con botón `[data-testid='open-delivery-map-btn']`. Botón de confirmar pedido permanece deshabilitado. | [UI] |
| 3 | Cliente hace clic en `[data-testid='open-delivery-map-btn']` | Se abre modal interactivo `MapSelectorModal` con mapa Leaflet centrado en la zona. | [UI] |
| 4 | Cliente fija ubicación en mapa (~2.0 km de distancia) y presiona `[data-testid='map-confirm-button']` | Modal se cierra. Aparece tarjeta `[data-testid='delivery-location-confirmed-card']` indicando distancia calculada (`2 km`) y costo de envío (`Bs 13.50` por tarifa base 4.50 + 4.50 Bs/km). Total a pagar se actualiza a `Subtotal + Bs 13.50`. Botón de confirmar se habilita. | [UI] |
| 5 | Cliente hace clic en `[data-testid='confirm-order-btn']` | `POST /businesses/:slug/orders` despacha payload con `delivery_method: "Delivery"`, `delivery_cost: 13.5`, `distance_km: 2.0` y `delivery_location_url: "https://www.google.com/maps?q=..."`. Retorna 201 Created. | [API] |
| 6 | Cliente es redirigido a seguimiento `/perfil/:slug/orden/:id` | En cabecera de orden se visualiza Total con envío incluido, badge `Delivery` y desglose `(+Bs. 13.50 - 2 km)`. | [UI] |
| 7 | Dueño del negocio consulta `/mis-pedidos/:slug` | Tarjeta del pedido muestra badge `Delivery (+Bs. 13.50 - 2 km)` y botón de enlace `[data-testid='delivery-map-btn-{id}']` apuntando a Google Maps con la ubicación de entrega. | [UI] |

- **Feature:** `features/orders/orders_delivery_mode.feature`
- **Steps:** `tests/e2e/orders/test_orders_delivery_mode.py`
- **POMs:** `poms/checkout_page.py`, `poms/order_tracking_page.py`, `poms/business_orders_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-DELIV-01`
- **Cobertura implícita:** Cálculo Haversine en `deliveryCalculator.js`, persistencia de columnas `delivery_cost`, `delivery_location_url`, `distance_km` en tabla `orders`.

---

### 2. Bloqueo de Checkout ante Negocio sin Coordenadas de Despacho [Prioridad: 🟡 Alta]

> **Precondición:** Negocio Premium con `orders_enabled = True`, pero sin coordenadas configuradas (`location_url = null`).  
> **Actor:** Cliente Comprador.

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Cliente avanza a checkout con productos en carrito | Vista de checkout carga con métodos de entrega. | [UI] |
| 2 | Cliente selecciona "Delivery" en `[data-testid='delivery-method-select']` | Hook detecta ausencia de coordenadas del negocio. Se despliega alerta `[data-testid='business-no-location-alert']` indicando que el comercio no tiene coordenadas registradas. | [UI] |
| 3 | Verificación de bloqueo de checkout | Botón `[data-testid='confirm-order-btn']` permanece deshabilitado (`disabled`). Se muestra hint `[data-testid='delivery-blocked-hint']` indicando seleccionar 'Entrega en el local'. | [UI] |
| 4 | Cliente conmuta método a "Entrega en el local" | Alerta desaparece inmediatamente, costo de envío vuelve a Bs 0.00 y botón `[data-testid='confirm-order-btn']` se habilita para pago presencial/retiro. | [UI] |

- **Feature:** `features/orders/orders_delivery_mode.feature`
- **Steps:** `tests/e2e/orders/test_orders_delivery_mode.py`
- **POMs:** `poms/checkout_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-DELIV-02`
- **Cobertura implícita:** Manejo de estado `businessHasLocation` en `useDeliveryCalculation.js`.

---

### 3. Cancelación del Modal de Mapa y Persistencia de Estado Padre [Prioridad: 🟡 Alta]

> **Precondición:** Negocio con coordenadas válidas. Cliente en checkout con "Delivery" seleccionado.  
> **Actor:** Cliente Comprador.

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Cliente hace clic en `[data-testid='open-delivery-map-btn']` | Se abre modal interactivo `MapSelectorModal`. | [UI] |
| 2 | Cliente hace clic en botón de cierre `[data-testid='map-close-button']` (o botón Cancelar) | Modal se cierra: `expect(modal).not_to_be_visible()`. | [UI] |
| 3 | Verificación de integridad del contenedor padre | La vista de checkout permanece intacta, visible y con los campos completados (nombre de cliente y carrito sin alteraciones). | [UI] |
| 4 | Verificación de estado de bloqueo | Tarjeta de ubicación confirmada NO aparece y botón `[data-testid='confirm-order-btn']` continúa deshabilitado (`isDeliveryBlocked = True`). | [UI] |

- **Feature:** `features/orders/orders_delivery_mode.feature`
- **Steps:** `tests/e2e/orders/test_orders_delivery_mode.py`
- **POMs:** `poms/checkout_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-DELIV-03`
- **Cobertura implícita:** Vector de descarte y aislamiento de submodal Leaflet sin bubbling destructivo.

---

### 4. Configuración de Métodos de Entrega en Catálogo e Invariante de Mínimo 1 [Prioridad: 🟡 Alta]

> **Precondición:** Negocio con pedidos activos (`orders_enabled = True`). Ambos checkboxes ("Entrega en local" y "Delivery") inicialmente seleccionados.  
> **Actor:** Dueño de negocio (`owner`).

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Dueño abre modal de edición de catálogo -> Configuración (`CatalogSettings.jsx`) | Se muestran checkboxes `delivery-method-pickup-checkbox` y `delivery-method-delivery-checkbox` ambos activos. | [UI] |
| 2 | Dueño desmarca "Entrega en local" | Checkbox pickup se desmarca; solo Delivery queda seleccionado. | [UI] |
| 3 | Dueño intenta desmarcar "Delivery" (quedando 0 métodos) | Hook `useCatalogSettings` intercepta y bloquea la acción, manteniendo al menos una opción activa y mostrando alerta contextual. | [UI] |
| 4 | Dueño guarda cambios con solo "Delivery" | `PATCH /businesses/:slug` persiste `delivery_methods = ["Delivery"]`. | [API] |
| 5 | Cliente navega a checkout del negocio | El selector `[data-testid='delivery-method-select']` contiene exclusivamente la opción "Delivery", sin listar "Entrega en el local". | [UI] |

- **Feature:** `features/orders/orders_delivery_mode.feature`
- **Steps:** `tests/e2e/orders/test_orders_delivery_mode.py`
- **POMs:** `poms/profile_page.py`, `poms/checkout_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-DELIV-04`
- **Cobertura implícita:** Invariante de catálogo en frontend y consistencia del array JSON en backend.

---

### 5. Búsqueda por Enlace de Google Maps en el Modal Leaflet [Prioridad: 🟡 Alta]

> **Precondición:** Negocio Premium con delivery y órdenes activas. Cliente en checkout con "Delivery" seleccionado y modal de mapa abierto.  
> **Actor:** Cliente Comprador.

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Cliente abre modal de mapa de delivery | Modal interactivo `MapSelectorModal` se abre con buscador y mapa Leaflet. | [UI] |
| 2 | Cliente pega enlace corto `https://maps.app.goo.gl/...` o coordenadas en `[data-testid='map-search-input']` y presiona buscar | Input procesa la URL mediante `/businesses/resolve-url` (o regex directo), ubica el marcador en las coordenadas exactas y habilita `[data-testid='map-confirm-button']`. | [UI/API] |
| 3 | Cliente confirma la ubicación | Modal se cierra y la tarjeta de delivery confirmada muestra la distancia y el costo correspondiente. | [UI] |

- **Feature:** `features/orders/orders_delivery_mode.feature`
- **Steps:** `tests/e2e/orders/test_orders_delivery_mode.py`
- **POMs:** `poms/checkout_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-DELIV-05`
- **Cobertura implícita:** Resolución de enlaces acortados y detección de coordenadas `ll=` o `q=` en `useLeafletMap.js`.

---

### 6. Factor de Sinuosidad Vial Urbana (1.8x) y Enrutamiento OSRM [Prioridad: 🔴 Crítica]

> **Precondición:** Negocio en La Paz (Obrajes: `-16.5349061, -68.1050929`). Cliente fija destino en Sopocachi (`-16.5108315, -68.1277939`). Distancia recta euclidiana base: 3.64 km.  
> **Actor:** Cliente Comprador.

| Paso | Acción del Usuario | Validación Esperada | Capa |
| :--- | :--- | :--- | :--- |
| 1 | Cliente avanza a checkout y abre modal de mapa | Mapa Leaflet se inicializa. | [UI] |
| 2 | Cliente introduce destino en Sopocachi y confirma ubicación | `useDeliveryCalculation` aplica factor de sinuosidad urbana (1.8x) o ruta vial OSRM. | [UI] |
| 3 | Verificación de distancia y tarifa vial | La distancia mostrada es `>= 6.0 km` (marcadamente superior a los 3.64 km en línea recta) y la tarifa calculada a 4.50 Bs/km resulta en `>= Bs. 27.00` (frente a los 16.38 Bs euclidianos). | [UI] |

- **Feature:** `features/orders/orders_delivery_mode.feature`
- **Steps:** `tests/e2e/orders/test_orders_delivery_mode.py`
- **POMs:** `poms/checkout_page.py`
- **Requerimientos cubiertos:** `REQ-ORD-DELIV-06`
- **Cobertura implícita:** `URBAN_CIRCUITY_FACTOR = 1.8` y `calculateRoadDistanceKm` con OSRM en `deliveryCalculator.js`.

---

## Mapeo a Tríada BDD (Feature + Steps + POM/Cliente) y Fixtures

| Flujo | Feature | Test / Steps | POMs / Clientes Requeridos | Fixtures Requeridos |
| :--- | :--- | :--- | :--- | :--- |
| 1. Pedido Delivery Cotizado | `features/orders/orders_delivery_mode.feature` | `tests/e2e/orders/test_orders_delivery_mode.py` | `checkout_page.py`, `order_tracking_page.py`, `business_orders_page.py` | `backend_api`, `shared_data` |
| 2. Bloqueo sin Coordenadas | `features/orders/orders_delivery_mode.feature` | `tests/e2e/orders/test_orders_delivery_mode.py` | `checkout_page.py` | `backend_api`, `shared_data` |
| 3. Cancelación Modal Mapa | `features/orders/orders_delivery_mode.feature` | `tests/e2e/orders/test_orders_delivery_mode.py` | `checkout_page.py` | `backend_api`, `shared_data` |
| 4. Invariante Catálogo | `features/orders/orders_delivery_mode.feature` | `tests/e2e/orders/test_orders_delivery_mode.py` | `profile_page.py`, `checkout_page.py` | `backend_api`, `shared_data` |
| 5. Búsqueda Enlaces Maps | `features/orders/orders_delivery_mode.feature` | `tests/e2e/orders/test_orders_delivery_mode.py` | `checkout_page.py` | `backend_api`, `shared_data` |
| 6. Sinuosidad Urbana 1.8x | `features/orders/orders_delivery_mode.feature` | `tests/e2e/orders/test_orders_delivery_mode.py` | `checkout_page.py` | `backend_api`, `shared_data` |

---

## Checklist de Ejecución

- [x] Tríada creada y actualizada en disco (`features/orders/orders_delivery_mode.feature`, `tests/e2e/orders/test_orders_delivery_mode.py`, `checkout_page.py`)
- [x] Flujos 1 a 6 ejecutados: 6 passed (0 failed, 0 xfailed)
- [x] Corrección de nested forms en `MapSelectorModal.jsx` y propagación de eventos
- [x] Teardown verificado (entidades generadas terminan en `*Test` y se limpian limpiamente)


