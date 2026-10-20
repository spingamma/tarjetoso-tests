# TEST_PLAN_BUSINESS_OPEN_CLOSE.md

## Plan de Pruebas E2E: Switch Abierto/Cerrado y WhatsApp en Trayecto de Pedidos

> **Alcance:** Cubre las 3 funcionalidades nuevas desplegadas:
> 1. **Toggle Abierto/Cerrado** (`PATCH /businesses/{slug}/toggle-open`)
> 2. **Letrero "Cerrado" de madera** (`WoodenClosedSign.jsx`) + grayscale en tarjetas
> 3. **Visibilidad condicional del botón WhatsApp** en `OrderCard.jsx`
>
> **Paradigma:** BDD (Gherkin + pytest-bdd) · Modo `internal` (caja blanca)

---

## Análisis de Cobertura Actual

| Funcionalidad | ¿Cubierta actualmente? | Archivos existentes |
|---|---|---|
| Toggle Abierto/Cerrado (API) | ❌ No | — |
| Toggle Abierto/Cerrado (UI perfil) | ❌ No | — |
| Toggle Abierto/Cerrado (UI MyBusinesses) | ❌ No | — |
| Grayscale + WoodenClosedSign (visitante) | ❌ No | — |
| Bloqueo de pedidos con negocio cerrado | ❌ No | — |
| Botón WhatsApp visible durante preparación | ❌ No | — |
| Botón WhatsApp oculto tras entrega/completado | ❌ No | — |
| Botón WhatsApp oculto tras cancelación | ❌ No | — |

> **Conclusión:** Ninguna de las funcionalidades nuevas tiene cobertura. Se necesita un nuevo módulo de pruebas.

---

## Decisión de Integración vs Flujos Nuevos

| Opción | Veredicto |
|---|---|
| Integrar en `premium_orders.feature` | ❌ Ya tiene 2 scenarios completos y 360 líneas de steps. Añadir más lo haría superar los 15 pasos por scenario. |
| Crear feature propia `business_open_close.feature` | ✅ El toggle es un journey **nuevo** del dueño que no existía antes. |
| Integrar WhatsApp en `premium_orders.feature` | ⚠️ Posible, pero la validación del WhatsApp post-entrega añade un actor extra (el vendedor revisando después de entregar). Mejor como scenario adicional en un feature dedicado a la **gestión del ciclo de pedidos por el vendedor**. |

**Decisión final:** Crear **1 feature file** con **3 scenarios** que cubren los 3 flujos como journeys completos.

---

## FLUJO 1: Dueño abre y cierra su negocio — Cliente ve grayscale y bloqueo 🔴

> **Precondición:** Negocio premium aprobado con al menos 1 producto y pedidos habilitados.
> **Actor:** Dueño del negocio + Cliente visitante.

| Paso | Acción del usuario | Validación esperada |
|------|-------------------|---------------------|
| 1 | Dueño navega a su perfil | El switch de Abierto/Cerrado (`business-toggle-open-btn`) es visible en la esquina superior derecha del banner |
| 2 | Dueño desactiva el switch (cierra el negocio) | La API `PATCH /businesses/{slug}/toggle-open` retorna `is_open: false`. El letrero de madera `"Cerrado"` (`hero-closed-badge`) aparece en el banner. La imagen del banner se muestra en escala de grises |
| 3 | Un visitante anónimo navega al perfil del mismo negocio | La foto del banner se muestra en escala de grises. El letrero de madera `"Cerrado"` es visible. El botón de checkout/carrito NO está disponible (el pedido queda bloqueado) |
| 4 | El visitante navega al directorio y busca el negocio | La tarjeta del negocio (`ProfessionalCard`) aparece en grayscale con el badge compacto "Cerrado" |
| 5 | Dueño reactiva el switch (abre el negocio) | `is_open: true`. El letrero "Cerrado" desaparece. La imagen vuelve a color. El carrito vuelve a estar habilitado |

```gherkin
Feature: Business Open Close Toggle
  As a business owner
  I want to toggle my business open or closed
  So that customers see it greyed out and cannot place orders when I am closed

  Scenario: Owner closes business and visitor sees grayscale profile with orders blocked
    Given a premium business exists with name "Toggle Biz Test" and slug "toggle-biz-test"
    And a product "Producto Toggle Test" exists for "toggle-biz-test"
    When the seller of "toggle-biz-test" logs in
    And the seller enables orders in catalog settings
    And the seller goes to "toggle-biz-test" profile
    Then the open close toggle switch is visible on the hero banner
    When the seller toggles the business to closed
    Then the hero banner shows the wooden "Cerrado" sign
    And the hero banner image has grayscale filter
    When a public visitor navigates to the public profile of "toggle-biz-test"
    Then the hero banner image has grayscale filter
    And the wooden "Cerrado" sign is visible
    And the checkout button is not available
    When the seller of "toggle-biz-test" logs in
    And the seller goes to "toggle-biz-test" profile
    And the seller toggles the business to open
    Then the wooden "Cerrado" sign is not visible
    And the hero banner image does not have grayscale filter
```

---

## FLUJO 2: Toggle desde panel Mis Negocios + Tarjeta del directorio en grayscale 🟡

> **Precondición:** Negocio premium aprobado.
> **Actor:** Dueño del negocio + Cliente visitante.

| Paso | Acción del usuario | Validación esperada |
|------|-------------------|---------------------|
| 1 | Dueño navega a `/mis-negocios` | El switch (`toggle-open-{slug}`) está visible junto al negocio aprobado |
| 2 | Dueño desactiva el toggle desde Mis Negocios | El switch cambia visualmente a "cerrado". La API responde con `is_open: false` |
| 3 | Visitante busca el negocio en el directorio | La tarjeta aparece en grayscale con badge compacto "Cerrado". El botón de acción dice "Cerrado" en vez de "Ver Tarjeta" |
| 4 | Dueño reactiva desde Mis Negocios | El switch vuelve a "abierto". La tarjeta vuelve a color |

```gherkin
  Scenario: Owner toggles open close from My Businesses panel and directory reflects grayscale
    Given a premium business exists with name "Panel Toggle Test" and slug "panel-toggle-test"
    When the seller of "panel-toggle-test" logs in
    And the seller navigates to "Mis Negocios"
    Then the open close toggle for "panel-toggle-test" is visible in the list
    When the seller toggles "panel-toggle-test" to closed from the panel
    Then the toggle shows closed state for "panel-toggle-test"
    When a public visitor searches for "Panel Toggle Test" in the directory
    Then the business card for "panel-toggle-test" appears in grayscale with "Cerrado" badge
    When the seller of "panel-toggle-test" logs in
    And the seller navigates to "Mis Negocios"
    And the seller toggles "panel-toggle-test" to open from the panel
    Then the toggle shows open state for "panel-toggle-test"
```

---

## FLUJO 3: Botón WhatsApp del cliente desaparece tras entrega del pedido 🔴

> **Precondición:** Negocio premium con pedidos habilitados y al menos 1 producto. Un pedido ya creado vía API en estado `pagado`.
> **Actor:** Vendedor del negocio (revisa la tarjeta del pedido).

| Paso | Acción del usuario | Validación esperada |
|------|-------------------|---------------------|
| 1 | Se crea un pedido con `customer_phone` vía API | El pedido tiene `customer_phone` registrado |
| 2 | Vendedor navega a `/mis-pedidos/{slug}` | El pedido aparece como "PAGADO" |
| 3 | Vendedor verifica la tarjeta del pedido | El botón WhatsApp (`whatsapp-customer-btn-{order_id}`) ES visible junto al nombre del cliente |
| 4 | Vendedor marca el pedido como "Entregado" | El estado cambia a "ENTREGADO" |
| 5 | Vendedor verifica la tarjeta del pedido | El botón WhatsApp (`whatsapp-customer-btn-{order_id}`) YA NO es visible |

```gherkin
  Scenario: WhatsApp button disappears from order card after delivery
    Given a premium business exists with name "WA Button Test" and slug "wa-button-test"
    And a product "Producto WA Test" exists for "wa-button-test"
    When the seller of "wa-button-test" logs in
    And the seller enables orders in catalog settings
    And an order with customer phone is created for "wa-button-test" via API
    And the seller navigates to their business orders
    Then the seller sees the order as "Pagado"
    And the WhatsApp button is visible on the order card
    When the seller marks the order as delivered
    Then the seller sees the order as "Entregado"
    And the WhatsApp button is not visible on the order card
```

---

## Mapeo Flujo → Archivos BDD

| Flujo | Feature | Test / Steps | POMs requeridos | Fixtures |
|---|---|---|---|---|
| Flujo 1: Cerrar negocio desde perfil | `features/business_management/business_open_close.feature` | `tests/e2e/business_management/test_business_open_close.py` | `profile_page.py`, `business_orders_page.py` | `shared_data`, `backend_api` |
| Flujo 2: Cerrar desde Mis Negocios | (mismo feature, Scenario 2) | (mismo test file) | `my_businesses_page.py` (**NUEVO**), `directory_page.py` | `shared_data`, `backend_api` |
| Flujo 3: WhatsApp en trayecto | (mismo feature, Scenario 3) | (mismo test file) | `business_orders_page.py` | `shared_data`, `backend_api` |
