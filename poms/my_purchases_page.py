import os
from poms.base_page import BasePage
from playwright.sync_api import expect
import re

class MyPurchasesPage(BasePage):
    """
    Representa la vista general de Mis Compras del cliente (/mis-compras).
    Tipo de App: SPA (React)
    """

    def go_to(self):
        """Navega a la página de Mis Compras."""
        base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
        self.page.goto(f"{base_url}/mis-compras")
        self.verify_page_loaded()

    def verify_page_loaded(self):
        self.page.wait_for_load_state("networkidle")

    def get_order_card(self, order_id: str):
        """
        Devuelve el locator de la tarjeta de un pedido específico.
        Usa el data-testid del componente CustomerOrderCard o fallback.
        """
        test_id_locator = self.page.locator(f"[data-testid='customer-order-card-{order_id}']")
        return test_id_locator.first

    def verify_confirm_button_visible(self, order_id: str, is_visible: bool, btn_text: str = "Producto recibido"):
        """
        Verifica si el botón de confirmación está visible o no dentro de la tarjeta.
        """
        card = self.get_order_card(order_id)
        card.wait_for(state="visible", timeout=10000)
        
        btn = card.locator("button", has_text=re.compile(btn_text, re.IGNORECASE)).first
        
        if is_visible:
            expect(btn).to_be_visible(timeout=5000)
        else:
            # Si esperamos que no esté visible
            expect(btn).not_to_be_visible(timeout=5000)
