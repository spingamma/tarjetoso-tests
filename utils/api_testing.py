# Archivo: utils/api_testing.py
"""
Clase auxiliar reutilizable para operaciones API en pruebas E2E.

Centraliza URLs, payloads y headers en un solo lugar
para que los cambios de endpoint se propaguen automáticamente a todos los tests.

Patrón inspirado en la arquitectura de api_client.py (principio DRY).
Todas las URLs y credenciales se consumen de variables de entorno
(regla pytest-bdd.md #4).
"""
import os
from playwright.sync_api import Playwright


class APIUtils:
    """Cliente HTTP reutilizable para operaciones de autenticación y API.

    Usa la API de request contexts de Playwright para hacer llamadas HTTP
    sin necesidad de instalar librerías adicionales como `requests`.

    Uso típico en fixtures:
        api = APIUtils()
        token = api.getToken(playwright)

    Uso con base_url personalizada:
        api = APIUtils(base_url="https://staging-api.example.com")
        token = api.getToken(playwright, email="test@example.com", password="pass")
    """

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "")

    def _url(self, path: str) -> str:
        """Construye URL completa desde path relativo."""
        return f"{self.base_url}{path}"

    def _headers(self, token: str = None) -> dict:
        """Construye headers Authorization con Bearer token.

        Args:
            token: Token de autenticación. Si es None, retorna headers vacíos.

        Returns:
            dict: Headers con Authorization si se provee token.
        """
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def getToken(
        self,
        playwright: Playwright,
        email: str = None,
        password: str = None,
        login_path: str = "api/auth/login",
        token_field: str = "data",
    ) -> str:
        """Obtiene un token de autenticación vía API.

        Args:
            playwright: Instancia de Playwright para crear contexto de API.
            email: Email del usuario. Si no se provee, usa TEST_USER_EMAIL del .env.
            password: Contraseña. Si no se provee, usa TEST_USER_PASSWORD del .env.
            login_path: Path relativo del endpoint de login (sin slash inicial).
                Por defecto "api/auth/login". Configúralo según tu backend.
            token_field: Campo del response JSON que contiene el token.
                Por defecto "data". Puede ser "access_token", "token", etc.

        Returns:
            str: Token de autenticación.

        Raises:
            AssertionError: Si el login falla.
            ValueError: Si las credenciales no están configuradas.
        """
        resolved_email = email or os.getenv("TEST_USER_EMAIL")
        resolved_password = password or os.getenv("TEST_USER_PASSWORD")

        if not resolved_email or not resolved_password:
            raise ValueError(
                "Credenciales no configuradas. "
                "Establece TEST_USER_EMAIL y TEST_USER_PASSWORD en tu archivo .env"
            )

        api_request_context = playwright.request.new_context(
            base_url=self.base_url
        )

        payload = {
            "email": resolved_email,
            "password": resolved_password
        }

        response = api_request_context.post(
            login_path,
            data=payload
        )

        assert response.ok, (
            f"Login falló ({response.status}): {response.text()}"
        )

        response_body = response.json()
        return response_body[token_field]

    def create_e2e_user(
        self,
        api_context,
        name: str,
        is_seller: bool = False,
        is_admin: bool = False,
    ) -> dict:
        """Crea y loguea un usuario de prueba (Shift-Left) usando e2e-login backdoor.
        
        Args:
            api_context: Contexto de request de Playwright (browser_instance.context.request)
            name: Nombre del usuario (debe terminar en Test)
            is_seller: Determina si el usuario se marca como vendedor
            is_admin: Determina si el usuario se marca como administrador
        
        Returns:
            dict: Datos del usuario devueltos por el backend, incluyendo token.
        """
        import random
        import uuid

        # Si no nos pasan base_url, asumimos la local o la del objeto
        base_url = self.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")
        base_url = base_url.rstrip("/")

        email = f"{name.lower().replace(' ', '')}_{uuid.uuid4().hex[:6]}@e2e.com"
        phone = f"555{random.randint(100000, 999999)}"
        
        payload = {
            "email": email,
            "name": name,
            "phone": phone,
            "is_verified": True,
            "is_vendedor": is_seller,
            "is_admin": is_admin
        }

        response = api_context.post(
            f"{base_url}/auth/e2e-login",
            data=payload
        )
        assert response.ok, f"Fallo al registrar usuario {name} en e2e-login. Status: {response.status}"
        
        user_data = response.json()
        try:
            from utils.test_tracker import TestTracker
            if user_data.get("id"):
                TestTracker.track_user(user_data["id"])
        except Exception:
            pass

        return user_data

    def inject_session_to_browser(self, browser_instance, user_data: dict):
        """Inyecta el token y los datos del usuario en el localStorage del navegador.
        
        Args:
            browser_instance: La instancia Page del navegador.
            user_data: Diccionario con la información del usuario (token, nombre, etc).
        """
        import json
        
        token = user_data.get("access_token")
        
        # Formato de usuario que espera el frontend en localStorage ('spingamma_user')
        front_user_data = {
            "id": user_data.get("id"),
            "nombre": user_data.get("nombre", user_data.get("name")),
            "celular": user_data.get("celular"),
            "email": user_data.get("email"),
            "is_verified": user_data.get("is_verified", True),
            "is_admin": user_data.get("is_admin", False),
            "is_vendedor": user_data.get("is_vendedor", False)
        }
        
        script = f"""
            localStorage.setItem('spingamma_token', '{token}');
            localStorage.setItem('spingamma_user', '{json.dumps(front_user_data)}');
        """
        browser_instance.context.add_init_script(script)

    def refresh_token(
        self,
        api_context,
        refresh_token: str = None,
        payload: dict = None,
        expected_status: list = None,
    ):
        """Envía solicitud a /auth/refresh para rotar sesión.
        
        Args:
            api_context: Contexto de request de Playwright.
            refresh_token: String del token a refrescar (si payload es None).
            payload: Diccionario crudo para enviar en el body (para tests negativos/vacíos).
            expected_status: Código o lista de códigos HTTP esperados para validar.
        """
        base_url = (self.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")).rstrip("/")
        req_body = payload if payload is not None else {"refresh_token": refresh_token}
        
        response = api_context.post(
            f"{base_url}/auth/refresh",
            data=req_body
        )
        
        if expected_status is not None:
            allowed = [expected_status] if isinstance(expected_status, int) else expected_status
            assert response.status in allowed, (
                f"Expected status {allowed} from /auth/refresh, got {response.status}: {response.text()}"
            )
        return response

    def logout(
        self,
        api_context,
        refresh_token: str = None,
        payload: dict = None,
        expected_status: list = None,
    ):
        """Envía solicitud a /auth/logout para revocar refresh token.
        
        Args:
            api_context: Contexto de request de Playwright.
            refresh_token: String del token a revocar.
            payload: Diccionario crudo para enviar en el body.
            expected_status: Código o lista de códigos HTTP esperados.
        """
        base_url = (self.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")).rstrip("/")
        req_body = payload if payload is not None else {"refresh_token": refresh_token}
        
        response = api_context.post(
            f"{base_url}/auth/logout",
            data=req_body
        )
        
        if expected_status is not None:
            allowed = [expected_status] if isinstance(expected_status, int) else expected_status
            assert response.status in allowed, (
                f"Expected status {allowed} from /auth/logout, got {response.status}: {response.text()}"
            )
        return response

    def get_user_status(
        self,
        api_context,
        access_token: str = None,
        expected_status: list = None,
    ):
        """Consulta /usuarios/status usando el Bearer token provisto.
        
        Args:
            api_context: Contexto de request de Playwright.
            access_token: Token para incluir en header Authorization: Bearer.
            expected_status: Código o lista de códigos HTTP esperados.
        """
        base_url = (self.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")).rstrip("/")
        headers = self._headers(access_token)
        
        response = api_context.get(
            f"{base_url}/usuarios/status",
            headers=headers
        )
        
        if expected_status is not None:
            allowed = [expected_status] if isinstance(expected_status, int) else expected_status
            assert response.status in allowed, (
                f"Expected status {allowed} from /usuarios/status, got {response.status}: {response.text()}"
            )
        return response

    def create_product_with_choices(
        self,
        api_context,
        slug: str,
        name: str,
        token: str,
        price: str = "50.00",
        stock: int = 100,
        choices: str = None,
        carousel_name: str = "Catálogo",
        is_visible: bool = True,
        expected_status: list = None,
    ):
        """Crea un producto con complementos (choices) vía Form multipart.
        
        Args:
            api_context: Contexto de request de Playwright.
            slug: Slug del negocio.
            name: Nombre del producto (debe terminar en Test).
            token: Access token del dueño del negocio.
            price: Precio del producto.
            stock: Stock del producto.
            choices: JSON string con lista de choices (ej: '["Ketchup", "Cebollín"]').
            carousel_name: Sección del catálogo.
            is_visible: Visibilidad pública.
            expected_status: Código o lista de códigos HTTP esperados.
        """
        base_url = (self.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")).rstrip("/")
        form_data = {
            "name": name,
            "price": str(price),
            "stock": str(stock) if stock is not None else "0",
            "carousel_name": carousel_name,
            "is_visible": "true" if is_visible else "false",
        }
        if choices is not None:
            form_data["choices"] = choices

        headers = self._headers(token)
        response = api_context.post(
            f"{base_url}/businesses/{slug}/products",
            form=form_data,
            headers=headers
        )

        if expected_status is not None:
            allowed = [expected_status] if isinstance(expected_status, int) else expected_status
            assert response.status in allowed, (
                f"Expected status {allowed} from POST products, got {response.status}: {response.text()}"
            )
        return response

    def create_order(
        self,
        api_context,
        slug: str,
        token: str,
        customer_name: str,
        items: list,
        delivery_method: str = "Entrega en el local",
        total_price: float = 50.0,
        customer_phone: str = None,
        expected_status: list = None,
    ):
        """Crea un pedido con items vía API.
        
        Args:
            api_context: Contexto de request de Playwright.
            slug: Slug del negocio.
            token: Access token del comprador.
            customer_name: Nombre del cliente.
            items: Lista de diccionarios con OrderItemCreate.
            delivery_method: Método de entrega.
            total_price: Total del pedido.
            customer_phone: Teléfono de contacto opcional.
            expected_status: Código o lista de códigos HTTP esperados.
        """
        base_url = (self.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")).rstrip("/")
        payload = {
            "customer_name": customer_name,
            "delivery_method": delivery_method,
            "total_price": total_price,
            "items": items,
        }
        if customer_phone is not None:
            payload["customer_phone"] = customer_phone

        headers = self._headers(token)
        response = api_context.post(
            f"{base_url}/businesses/{slug}/orders",
            data=payload,
            headers=headers
        )

        if expected_status is not None:
            allowed = [expected_status] if isinstance(expected_status, int) else expected_status
            assert response.status in allowed, (
                f"Expected status {allowed} from POST orders, got {response.status}: {response.text()}"
            )
        return response

    def toggle_business_open(
        self,
        api_context,
        slug: str,
        token: str,
        expected_status: list = None,
    ):
        """Alterna el estado abierto/cerrado del negocio (PATCH /businesses/{slug}/toggle-open)."""
        base_url = (self.base_url or os.getenv("API_BASE_URL", "http://localhost:8000/")).rstrip("/")
        headers = self._headers(token)
        response = api_context.patch(
            f"{base_url}/businesses/{slug}/toggle-open",
            headers=headers
        )
        if expected_status is not None:
            allowed = [expected_status] if isinstance(expected_status, int) else expected_status
            assert response.status in allowed, (
                f"Expected status {allowed} from PATCH toggle-open, got {response.status}: {response.text()}"
            )
        return response