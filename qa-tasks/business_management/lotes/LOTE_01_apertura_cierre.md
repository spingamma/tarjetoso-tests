# Lote 01 — Apertura, Cierre y Contacto en Ciclo de Pedido

| Campo | Valor |
| :--- | :--- |
| Módulo | `business_management` |
| Flujos | 1. Dueño abre y cierra su negocio — Cliente ve grayscale y bloqueo<br>2. Visibilidad condicional de botón WhatsApp en el ciclo del pedido |
| Pytest | `pytest tests/e2e/business_management/test_business_open_close.py -v` |
| Bug Reports | Ninguno activo |

---

## Journeys del Lote

### 1. Dueño abre y cierra su negocio — Cliente ve grayscale y bloqueo [Prioridad: 🔴 Crítica]

> **Precondición:** Negocio premium aprobado con al menos 1 producto y pedidos habilitados en base de datos de test.  
> **Actor:** Dueño del negocio + Cliente visitante anónimo.

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Dueño inicia sesión y navega a su perfil `/perfil/{slug}` **[UI]** | El switch de Abierto/Cerrado (`data-testid="business-toggle-open-btn"`) es visible en la esquina superior del banner **[UI]**. |
| 2 | Dueño desactiva el switch (cierra el negocio) **[UI]** | Petición `PATCH /businesses/{slug}/toggle-open` retorna `is_open: false` **[API]**. El letrero `"Cerrado"` (`data-testid="hero-closed-badge"`) aparece en el banner **[UI]**. La imagen del banner se muestra en escala de grises (`grayscale`) **[UI]**. |
| 3 | Visitante anónimo navega al perfil del mismo negocio `/perfil/{slug}` **[UI]** | La foto de portada se muestra en escala de grises **[UI]**. El letrero `"Cerrado"` es visible **[UI]**. Los botones de compra/checkout quedan bloqueados/deshabilitados **[UI]**. |
| 4 | Visitante navega al directorio y busca el negocio **[UI]** | La tarjeta del negocio (`ProfessionalCard`) aparece con filtro grayscale y el badge compacto "Cerrado" **[UI]**. |
| 5 | Dueño reactiva el switch (abre el negocio) **[UI]** | `is_open: true` en respuesta API **[API]**. El letrero "Cerrado" desaparece **[UI]**. Los productos vuelven a permitir pedidos **[UI]**. |

- **Feature:** `features/business_management/business_open_close.feature`
- **Steps:** `tests/e2e/business_management/test_business_open_close.py`
- **POMs:** `poms/profile_page.py`, `poms/directory_page.py`
- **Requerimientos cubiertos:** `REQ-BIZ-01`, `REQ-BIZ-02`
- **Cobertura implícita:** Sincronización en tiempo real del estado `is_open` en endpoints públicos del catálogo.

---

### 2. Visibilidad condicional del botón WhatsApp en el ciclo del pedido [Prioridad: 🟡 Alta]

> **Precondición:** Pedido activo generado en un negocio con número de teléfono configurado.  
> **Actor:** Comerciante (vendedor) gestionando pedidos en `/mis-pedidos/{slug}`.

| Paso | Acción del Usuario | Validación Esperada |
| :--- | :--- | :--- |
| 1 | Vendedor ingresa a la pestaña de pedidos en preparación **[UI]** | La tarjeta de pedido (`OrderCard`) muestra el botón verde de contacto por WhatsApp **[UI]**. |
| 2 | Vendedor valida el enlace de WhatsApp **[UI]** | El atributo `href` contiene el número internacional y el mensaje preformateado con el código de orden **[UI]**. |
| 3 | Vendedor cambia el estado del pedido a `entregado` **[UI]** | La API actualiza el pedido a `entregado` **[API]**. El botón de WhatsApp desaparece de la tarjeta **[UI]**. |
| 4 | En un pedido cancelado, el vendedor revisa la tarjeta **[UI]** | El botón de WhatsApp NO está disponible para pedidos en estado `cancelado` **[UI]**. |

- **Feature:** `features/business_management/business_open_close.feature`
- **Steps:** `tests/e2e/business_management/test_business_open_close.py`
- **POMs:** `poms/business_orders_page.py`
- **Requerimientos cubiertos:** `REQ-BIZ-03`
- **Cobertura implícita:** Formateo de números telefónicos y sanitización de enlaces `wa.me`.

---

## Mapeo a Tríada BDD (Feature + Steps + POM/Cliente) y Fixtures

| Flujo | Feature | Test / Steps | POMs / Clientes Requeridos | Fixtures Requeridos |
| :--- | :--- | :--- | :--- | :--- |
| 1. Switch Abierto/Cerrado | `features/business_management/business_open_close.feature` | `tests/e2e/business_management/test_business_open_close.py` | `profile_page.py`, `directory_page.py` | `backend_api`, `shared_data` |
| 2. WhatsApp en Pedidos | `features/business_management/business_open_close.feature` | `tests/e2e/business_management/test_business_open_close.py` | `business_orders_page.py` | `backend_api`, `shared_data` |

---

## Checklist de Ejecución

- [x] Tríada creada en disco (`business_open_close.feature`, `test_business_open_close.py`, POMs correspondientes)
- [x] Suite del lote ejecutada (Fecha: 2026-10-01, Ambiente: local)
- [x] Resultado: 3 passed / 0 failed / 0 xfail / 0 skipped
- [x] Teardown verificado (entidades generadas terminan en `*Test` y se limpian)
- [x] Bugs pendientes del lote: ninguno activo
