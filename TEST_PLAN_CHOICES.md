# Plan de Pruebas E2E — Complementos de Productos (Choices / A Elección)

> **Módulo:** Catálogo & Pedidos — Sub-funcionalidad "A elección"  
> **Nivel:** E2E UI (Playwright + pytest-bdd) con setup vía API  
> **Estándar:** BDD (Gherkin en Inglés), Zero Mocking  
> **Fecha de Creación:** 2026-09-27  

---

## 1. Contexto y Objetivos de Calidad

La funcionalidad **"A elección"** permite a los dueños de negocios premium configurar opciones complementarias opcionales en sus productos (ej. Ketchup, Cebollín, Mayonesa). Cuando un comprador realiza un pedido que incluye productos con complementos, se le presenta una pantalla intermedia (`/perfil/:slug/complementos`) donde puede seleccionar sus preferencias antes de proceder al checkout.

### Flujo de Datos:
1. **Vendedor:** Configura choices en `ProductFormModal` → se almacenan como JSON string en `products.choices`.
2. **Comprador:** Selecciona complementos en `ChoicesScreen` → se enriquece el carrito con `selected_choices`.
3. **Checkout:** El payload `OrderItemCreate.selected_choices` lleva las selecciones al backend → se persisten en `order_items.selected_choices`.
4. **Visualización:** Tanto `CustomerOrderCard` (comprador) como `OrderCard` (vendedor) renderizan los complementos seleccionados.

### Endpoints Involucrados:
| Endpoint | Método | Rol |
|----------|--------|-----|
| `POST /businesses/{slug}/products` | `POST` | Crear producto con campo `choices` (Form) |
| `PUT /businesses/{slug}/products/{id}` | `PUT` | Actualizar producto incluyendo `choices` |
| `GET /businesses/{slug}/products` | `GET` | Listar productos (retorna `choices` en response) |
| `POST /businesses/{slug}/orders` | `POST` | Crear pedido con `selected_choices` en items |
| `GET /businesses/{slug}/orders` | `GET` | Listar pedidos (retorna `selected_choices` en items) |

---

## 2. Flujos de Prueba BDD

### Flujo 1: Vendedor configura complementos y comprador los selecciona en un pedido completo 🔴 Crítica

> **Precondición:** Negocio premium con pedidos habilitados y al menos un producto con choices configuradas.  
> **Actor (Tramo 1):** Dueño del negocio (Vendedor)  
> **Actor (Tramo 2):** Comprador autenticado  

| Paso | Acción del usuario | Validación esperada |
|------|--------------------|---------------------|
| 1 | (API Setup) Crear negocio premium con pedidos habilitados y producto con `choices: '["Ketchup","Cebollín","Mayonesa"]'` | Producto creado con `choices` no nulo en la response. |
| 2 | Comprador navega al perfil del negocio | El perfil carga y muestra el producto. |
| 3 | Comprador agrega el producto al carrito | El carrito muestra 1 item. |
| 4 | Comprador hace click en "Ordenar" | Se redirige a `/perfil/{slug}/complementos` (ChoicesScreen). |
| 5 | Comprador ve la pantalla de complementos | La pantalla muestra el título "Complementos de tu Pedido", el nombre del producto y las 3 opciones (Ketchup, Cebollín, Mayonesa) como checkboxes. |
| 6 | Comprador selecciona "Ketchup" y "Mayonesa" | Los checkboxes seleccionados muestran estado activo (estilo naranja), el contador muestra "2 selec." |
| 7 | Comprador hace click en "Continuar al Pedido" | Se redirige a la pantalla de checkout (`/perfil/{slug}/orden`). |
| 8 | Comprador verifica resumen del pedido en checkout | El resumen muestra el producto con los complementos "Ketchup" y "Mayonesa" listados. |
| 9 | Comprador completa el checkout (nombre + método de pago) | El pedido se crea exitosamente con `selected_choices` almacenado. |
| 10 | Vendedor navega a sus pedidos del negocio | El pedido aparece con los complementos "Ketchup" y "Mayonesa" visibles en el detalle del item. |

```gherkin
Feature: Product Choices Selection During Purchase
  As a buyer
  I want to select optional complements for products that offer them
  So that my order reflects my personalized preferences

  Scenario: Buyer selects choices for a product and they persist in the order
    Given a premium business "Burger Choices Test" with slug "burger-choices-test" exists via API
    And orders are enabled for "burger-choices-test"
    And a product "Hamburguesa Especial Test" with choices '["Ketchup","Cebollín","Mayonesa"]' exists for "burger-choices-test"
    And a buyer user is logged in
    When the buyer navigates to the "burger-choices-test" profile
    And the buyer adds "Hamburguesa Especial Test" to the cart
    And the buyer clicks the order button
    Then the choices screen is displayed with title "Complementos de tu Pedido"
    And the product "Hamburguesa Especial Test" shows 3 choice options
    When the buyer selects "Ketchup" and "Mayonesa" as choices
    Then the selection counter shows "2 selec."
    When the buyer clicks "Continuar al Pedido"
    Then the checkout screen displays "Ketchup" and "Mayonesa" in the order summary
    When the buyer completes the checkout with name "Buyer Choices Test" and payment "Transferencia / QR"
    Then the order is created successfully
    When the seller of "burger-choices-test" logs in and views their orders
    Then the order item shows "Ketchup" and "Mayonesa" as selected choices
```

**Cobertura implícita:** Navegación a ChoicesScreen, renderizado de checkboxes, enriquecimiento del carrito con `selected_choices`, serialización JSON del payload, persistencia en `order_items.selected_choices`, renderizado en `CustomerOrderCard` y `OrderCard`.

---

### Flujo 2: Producto sin complementos no muestra pantalla de choices (bypass directo a checkout) 🟡 Alta

> **Precondición:** Negocio premium con pedidos habilitados y un producto SIN choices.  
> **Actor:** Comprador autenticado  

| Paso | Acción del usuario | Validación esperada |
|------|--------------------|---------------------|
| 1 | (API Setup) Crear negocio premium con producto sin choices (`choices: null`) | Producto creado sin complementos. |
| 2 | Comprador navega al perfil y agrega el producto al carrito | Carrito con 1 item. |
| 3 | Comprador hace click en "Ordenar" | Se redirige directamente al checkout (sin pasar por ChoicesScreen) O la ChoicesScreen muestra "Listo" y "Este producto no requiere complementos". |
| 4 | Comprador completa el checkout | Pedido creado con `selected_choices: null` en el item. |

```gherkin
  Scenario: Product without choices skips or shows no-choices state on choices screen
    Given a premium business "No Choices Test" with slug "no-choices-test" exists via API
    And orders are enabled for "no-choices-test"
    And a product "Hamburguesa Simple Test" without choices exists for "no-choices-test"
    And a buyer user is logged in
    When the buyer adds "Hamburguesa Simple Test" to the cart and clicks order
    Then the choices screen shows the product with a "Listo" badge and no checkboxes
    When the buyer clicks "Continuar al Pedido"
    And completes checkout with name "No Choices Buyer Test" and payment "efectivo"
    Then the order is created without selected choices
```

**Cobertura implícita:** Renderizado condicional del badge "Listo" vs checkboxes, texto "Este producto no requiere complementos", `selected_choices: null` en payload.

---

### Flujo 3: Comprador deselecciona todos los complementos (pedido sin selecciones pese a existir opciones) 🟢 Media

> **Precondición:** Negocio premium con producto que tiene choices.  
> **Actor:** Comprador autenticado  

| Paso | Acción del usuario | Validación esperada |
|------|--------------------|---------------------|
| 1 | (API Setup) Producto con choices configuradas. | Choices disponibles. |
| 2 | Comprador agrega al carrito y llega a ChoicesScreen. | Muestra las opciones. |
| 3 | Comprador selecciona "Ketchup" | Checkbox activo, contador "1 selec." |
| 4 | Comprador deselecciona "Ketchup" | Checkbox inactivo, contador "0 selec." |
| 5 | Comprador continúa al pedido sin selecciones | Checkout NO muestra complementos para ese item. |
| 6 | Comprador completa el pedido | `selected_choices: null` en el item del pedido. |

```gherkin
  Scenario: Buyer deselects all choices and order is created without selections
    Given a premium business "Deselect Choices Test" with slug "deselect-choices-test" exists via API
    And a product "Burger Deselect Test" with choices '["Ketchup","Cebollín"]' exists for "deselect-choices-test"
    And a buyer user is logged in
    When the buyer reaches the choices screen for "Burger Deselect Test"
    And selects "Ketchup" then deselects it
    Then the selection counter shows "0 selec."
    When the buyer continues to checkout and completes the order
    Then the order item has no selected choices
```

**Cobertura implícita:** Toggle on/off de checkboxes, `JSON.stringify([])` → `null` en el carrito enriquecido, aserción de ausencia de complementos en la order response.

---

### Flujo 4: Vendedor configura choices desde el modal de producto en el editor de catálogo (E2E UI) 🟡 Alta

> **Precondición:** Negocio premium existente, vendedor autenticado.  
> **Actor:** Dueño del negocio  

| Paso | Acción del usuario | Validación esperada |
|------|--------------------|---------------------|
| 1 | Vendedor navega a su perfil y abre el editor de catálogo | Modal de catálogo visible. |
| 2 | Vendedor hace click en "Añadir producto" | Modal de producto visible con sección "A elección". |
| 3 | Vendedor hace click en el botón "Añadir" de la sección A elección | Aparece un input de texto para la opción 1. |
| 4 | Vendedor escribe "Ketchup" en el primer input | Texto visible en el input. |
| 5 | Vendedor hace click en "Añadir" de nuevo | Aparece un segundo input. |
| 6 | Vendedor escribe "Cebollín" en el segundo input | Texto visible. |
| 7 | Vendedor hace click en el botón "-" del primer choice (Ketchup) | El input de "Ketchup" desaparece, solo queda "Cebollín". |
| 8 | Vendedor completa el nombre del producto y guarda | Producto creado con `choices: '["Cebollín"]'`. |
| 9 | Vendedor verifica en la lista de productos | El producto aparece en el catálogo. |

```gherkin
Feature: Product Choices Configuration by Seller
  As a business owner
  I want to add optional choices to my products
  So that buyers can customize their orders

  Scenario: Seller adds and removes choices in the product form modal
    Given a seller is logged in with a premium business "Config Choices Test" and slug "config-choices-test"
    When the seller opens the catalog editor and clicks add product
    Then the product form modal is displayed with the "A elección" section
    When the seller clicks the add choice button
    Then a choice input field appears
    When the seller types "Ketchup" in choice input 0
    And clicks the add choice button again
    And types "Cebollín" in choice input 1
    And removes choice 0 (Ketchup)
    Then only 1 choice input remains with value "Cebollín"
    When the seller fills product name "Producto Choices Config Test" and submits
    Then the product is created with choices containing "Cebollín"
```

**Cobertura implícita:** Renderizado de `ProductFormModal` con sección A elección, botón `add-choice-btn`, inputs `choice-input-{idx}`, botones `remove-choice-btn-{idx}`, serialización del array de choices al submit, límite de 10 choices (botón oculto al llegar a 10).

---

### Flujo 5: Validación API — Crear producto con choices y crear pedido con selected_choices (Backend Puro) 🟡 Alta

> **Precondición:** Token de autenticación de un dueño de negocio premium.  
> **Actor:** API Client  

| Paso | Acción de API | Validación esperada |
|------|---------------|---------------------|
| 1 | `POST /businesses/{slug}/products` con `choices='["Extra Queso","Jalapeños"]'` en Form data | HTTP 200, response incluye `choices: '["Extra Queso","Jalapeños"]'`. |
| 2 | `GET /businesses/{slug}/products` | Lista incluye el producto con `choices` no nulo. |
| 3 | `POST /businesses/{slug}/orders` con item que incluye `selected_choices: '["Extra Queso"]'` | HTTP 200, order response incluye item con `selected_choices: '["Extra Queso"]'`. |
| 4 | `GET /businesses/{slug}/orders` | El pedido listado incluye `selected_choices` en el item correcto. |

```gherkin
Feature: Choices API Persistence and Retrieval
  As the system
  I want product choices and order selected_choices to persist correctly
  So that both buyer and seller see the correct data

  Scenario: Product choices persist via API and order carries selected_choices
    Given a premium business "API Choices Test" with slug "api-choices-test" is created via API
    When a product is created with choices '["Extra Queso","Jalapeños"]' via API
    Then the product response contains choices '["Extra Queso","Jalapeños"]'
    When a product listing is fetched for the business
    Then the product appears with non-null choices
    When an order is created with selected_choices '["Extra Queso"]' for that product
    Then the order response item contains selected_choices '["Extra Queso"]'
    When the business orders are listed
    Then the order item still contains selected_choices '["Extra Queso"]'
```

**Cobertura implícita:** Serialización/deserialización JSON en `ProductCreate.choices` y `OrderItemCreate.selected_choices`, persistencia en columnas `products.choices` y `order_items.selected_choices`.

---

### Flujo 6: Edge Case — Producto con choices vacías y pedido con selected_choices vacío 🟢 Media

> **Precondición:** Backend en ejecución.  
> **Actor:** API Client  

| Paso | Acción de API | Validación esperada |
|------|---------------|---------------------|
| 1 | `POST /businesses/{slug}/products` con `choices='[]'` | HTTP 200, `choices` es `null` o `'[]'`. |
| 2 | `POST /businesses/{slug}/products` con `choices=null` (omitido) | HTTP 200, `choices: null`. |
| 3 | `POST /businesses/{slug}/orders` con `selected_choices: '[]'` en un item | HTTP 200, `selected_choices` es `null` o `'[]'`. |
| 4 | `POST /businesses/{slug}/orders` con `selected_choices: null` en un item | HTTP 200, `selected_choices: null`. |

```gherkin
  Scenario Outline: Edge cases for empty or null choices
    Given a premium business "Edge Choices Test" exists via API
    When a product is created with choices <choices_value>
    Then the product response has choices <expected_choices>

    Examples:
      | choices_value | expected_choices |
      | '[]'          | null or '[]'     |
      | null          | null             |

  Scenario Outline: Edge cases for empty or null selected_choices in orders
    Given a product exists for "Edge Choices Test"
    When an order is created with selected_choices <selected_value>
    Then the order item has selected_choices <expected_selected>

    Examples:
      | selected_value | expected_selected |
      | '[]'           | null or '[]'      |
      | null           | null              |
```

**Cobertura implícita:** Manejo de strings vacíos, arrays vacíos, y valores nulos tanto en la capa de producto como en la de pedido.

---

## 3. Reconciliación de Cobertura API (Zero-Gap)

| Endpoint | Método | Flujos que lo cubren | Tipo de Cobertura |
|----------|--------|----------------------|-------------------|
| `POST /businesses/{slug}/products` | `POST` | Flujos 1 (setup), 4 (UI), 5, 6 | Creación con choices — Happy Path, Edge Cases |
| `PUT /businesses/{slug}/products/{id}` | `PUT` | ⚠️ No cubierto explícitamente (cubierto implícitamente por `independent_catalog.feature` existente) | Considerar añadir un paso de update con choices a Flujo 4 si se requiere |
| `GET /businesses/{slug}/products` | `GET` | Flujos 1, 2, 5 | Listado con choices visibles |
| `POST /businesses/{slug}/orders` | `POST` | Flujos 1, 2, 3, 5, 6 | Creación con selected_choices — Happy, Skip, Deselect, Edge |
| `GET /businesses/{slug}/orders` | `GET` | Flujos 1, 5 | Verificación de persistencia de selected_choices |

> **Nota:** `PUT /businesses/{slug}/products/{id}` acepta `choices` como Form field. Si se desea cobertura explícita del update, se puede añadir un escenario dentro del Flujo 4 donde el vendedor edite un producto existente para agregar/remover choices.

---

## 4. Mapeo Flujo → Archivos BDD (Estructura Modular)

> **REGLA ESTRUCTURAL:** Los archivos se agrupan en subcarpetas por módulo dentro de `features/` y `tests/e2e/`.

| Flujo | Feature | Test / Steps | POMs | Fixtures Requeridos |
|-------|---------|-------------|------|---------------------|
| Flujo 1 (Compra con choices) | `features/choices/product_choices_purchase.feature` | `tests/e2e/choices/test_product_choices_purchase.py` | `choices_screen_page.py`, `checkout_page.py`, `profile_page.py`, `business_orders_page.py` | `shared_data`, `backend_api` |
| Flujo 2 (Sin choices) | `features/choices/product_choices_purchase.feature` (mismo feature, scenario 2) | `tests/e2e/choices/test_product_choices_purchase.py` | `choices_screen_page.py`, `checkout_page.py` | `shared_data`, `backend_api` |
| Flujo 3 (Deselect) | `features/choices/product_choices_purchase.feature` (mismo feature, scenario 3) | `tests/e2e/choices/test_product_choices_purchase.py` | `choices_screen_page.py` | `shared_data`, `backend_api` |
| Flujo 4 (Config UI) | `features/choices/product_choices_config.feature` | `tests/e2e/choices/test_product_choices_config.py` | `profile_page.py` (editor de catálogo ya existente) | `shared_data`, `backend_api` |
| Flujos 5-6 (API) | `features/choices/choices_api_persistence.feature` | `tests/e2e/choices/test_choices_api_persistence.py` | Ninguno — API pura | `shared_data`, `backend_api` |

---

## 5. Estrategia de Teardown y Cero Contaminación

- Todas las entidades de prueba usan el sufijo `"Test"` (ej. `"Burger Choices Test"`, `"Buyer Choices Test"`).
- Se usa el endpoint `DELETE /e2e/cleanup-test-data` existente al finalizar la suite, que purga usuarios y negocios con sufijo `"Test"` y sus dependencias en cascada (`products`, `order_items`, `orders`).
- Los productos y pedidos creados vía API en los fixtures se limpian automáticamente junto con el negocio.

---

## 6. Estado de Ejecución y Cobertura Verificada

- [x] Crear directorio `features/choices/`
- [x] Crear directorio `tests/e2e/choices/`
- [x] Crear POM `poms/choices_screen_page.py` para la pantalla de complementos (`ChoicesScreen`)
- [x] Verificar y adaptar `poms/checkout_page.py` para asertar complementos en el resumen de compra (`verify_choices_displayed`)
- [x] Adaptar `poms/business_orders_page.py` para asertar complementos en pedidos recibidos (`verify_order_choices`)
- [x] Escribir especificación Gherkin `features/choices/product_choices_purchase.feature` (Escenarios 1, 2, 3)
- [x] Escribir especificación Gherkin `features/choices/product_choices_config.feature` (Escenario 4)
- [x] Escribir especificación Gherkin `features/choices/choices_api_persistence.feature` (Escenarios 5, 6)
- [x] Implementar step definitions en `tests/e2e/choices/test_product_choices_purchase.py`
- [x] Implementar step definitions en `tests/e2e/choices/test_product_choices_config.py`
- [x] Implementar step definitions en `tests/e2e/choices/test_choices_api_persistence.py`
- [x] Agregar métodos `create_product_with_choices()` y `create_order()` en `utils/api_testing.py`
- [x] Ejecutar la suite completa con `./venv/bin/pytest tests/e2e/choices/ -v`

### 🔍 Resumen de Resultados de Automatización:
| Test Case / Escenario | Archivo | Resultado | Tiempo |
|---|---|---|---|
| `test_buyer_selects_choices_for_a_product_and_they_persist_in_the_order` | `test_product_choices_purchase.py` | **PASSED** ✅ | ~3.5s |
| `test_product_without_choices_skips_directly_to_checkout` | `test_product_choices_purchase.py` | **PASSED** ✅ | ~3.2s |
| `test_buyer_deselects_all_choices_and_order_is_created_without_selections` | `test_product_choices_purchase.py` | **PASSED** ✅ | ~3.9s |
| `test_seller_adds_and_removes_choices_in_the_product_form_modal` | `test_product_choices_config.py` | **PASSED** ✅ | ~5.1s |
| `test_product_choices_persist_via_api_and_order_carries_selected_choices` | `test_choices_api_persistence.py` | **PASSED** ✅ | ~0.7s |
| `test_edge_case_empty_choices_string_and_null_selected_choices` | `test_choices_api_persistence.py` | **PASSED** ✅ | ~0.6s |
| **Global E2E Teardown** | `conftest.py` | **PASSED** ✅ | 200 OK (0 entidades huérfanas) |

**Total:** 6 passed en 16.07s

