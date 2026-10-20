# Reportes de Bugs — Módulo Ubicación / Location

## ✅ Resuelto: Falla en la resolución de coordenadas desde URLs acortadas de Google Maps (`maps.app.goo.gl`)

**Fecha del Reporte:** 2026-09-20  
**Fecha de Resolución:** 2026-09-20  
**Estado:** ✅ Resuelto (Verificado en Suite E2E)

**Descripción:**
Al ingresar un enlace de compartir generado por la aplicación móvil de Google Maps (formato corto `https://maps.app.goo.gl/...`), el backend arrojaba `HTTP 500 Internal Server Error` debido a un desajuste en la serialización Pydantic (`ValidationError`), impidiendo que la UI autocomplete las coordenadas en el formulario de edición de ubicación de negocio.

**Causa Raíz:**
1. En Backend: `utils/url_resolver.py:resolve_url()` devolvía un diccionario `{"resolved_url": "..."}`, mientras que `routers/businesses.py` construía `ResolveUrlResponse(url=_resolve_url(url))` hacia un schema donde `url` estaba tipado como `str`.
2. En Frontend: El hook `useProfileLocation.js` consumía `data.resolved_url`, mientras que `ResolveUrlResponse` no exponía dicho atributo.

**Solución Implementada:**
1. **Backend Schema (`schemas/common.py`):** Se actualizó `ResolveUrlResponse` para incluir tanto `url: str` como `resolved_url: str`, garantizando paridad contractual con el frontend y las aserciones de prueba.
2. **Backend Router (`routers/businesses.py`):** Se adaptó `resolve_url_endpoint` para extraer la URL como string y poblar ambos campos (`url` y `resolved_url`).
3. **Backend Resolver (`utils/url_resolver.py`):** Se adaptó el formateo de respuesta para incluir ambas claves.
4. **Frontend Hook (`useProfileLocation.js`):** Se incorporó fallback defensivo `data.resolved_url || data.url`.

**🔍 Resultados de la Suite Automatizada:**
- Feature: `features/short_url_location.feature`
- Step definitions: `tests/e2e/test_short_url_location.py`
- Resultados:
  - `test_backend_resolves_short_url`: **PASSED** ✅
  - `test_ui_detects_short_url_coordinates`: **PASSED** ✅
  - `test_ui_shows_warning_for_invalid_url`: **PASSED** ✅
- Total: `3 passed in 12.07s`
