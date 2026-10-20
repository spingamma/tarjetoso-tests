from poms.base_page import BasePage
import time
import re

class BusinessOrdersPage(BasePage):
    """
    Representa la vista de gestión de pedidos para el dueño del negocio.
    Tipo de App: SPA (React)
    """

    def go_to(self, slug: str):
        """Navega a la gestión de pedidos de un negocio específico."""
        import os
        base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
        self.page.goto(f"{base_url}/mis-pedidos/{slug}")
        self.verify_page_loaded()
        
    def verify_page_loaded(self):
        self.page.wait_for_load_state("networkidle")

    def get_order_card(self, order_id: str):
        """Devuelve el locator de la tarjeta de un pedido específico."""
        return self.page.locator(f"[data-testid='business-order-card-{order_id}']")

    def mark_as_paid(self, order_id: str):
        """Aprueba el pedido (pago) para cambiar estado a pagado/pendiente."""
        card = self.get_order_card(order_id)
        card.locator("[data-testid='mark-paid-btn']").click()
        # Esperar un poco a que el backend responda y la UI se actualice
        time.sleep(1)

    def mark_as_delivered(self, order_id: str):
        """Marca el pedido como entregado."""
        card = self.get_order_card(order_id)
        card.locator("[data-testid='mark-delivered-btn']").click()
        time.sleep(1)
        
    def verify_order_status(self, order_id: str, status_text: str):
        """Verifica que el estado visible en la tarjeta coincida con el esperado."""
        card = self.get_order_card(order_id)
        card.wait_for(state="visible", timeout=15000)
        from playwright.sync_api import expect
        expect(card.locator(f"text=/{status_text}/i").first).to_be_visible(timeout=10000)

    def verify_order_choices(self, order_id: str, *choice_names: str):
        """Verifica que la tarjeta de la orden muestre los complementos indicados."""
        card = self.get_order_card(order_id)
        card.wait_for(state="visible", timeout=15000)
        from playwright.sync_api import expect
        for choice in choice_names:
            expect(card.locator(f"text=/{choice}/i").first).to_be_visible(timeout=10000)

    def get_whatsapp_button(self, order_id: str):
        """Devuelve el locator del botón de WhatsApp de un pedido."""
        card = self.get_order_card(order_id)
        return card.locator(f"[data-testid='whatsapp-customer-btn-{order_id}']")

    def verify_whatsapp_button_visible(self, order_id: str):
        """Verifica que el botón de WhatsApp del cliente esté visible en la tarjeta del pedido."""
        btn = self.get_whatsapp_button(order_id)
        from playwright.sync_api import expect
        expect(btn).to_be_visible(timeout=5000)

    def verify_whatsapp_button_not_visible(self, order_id: str):
        """Verifica que el botón de WhatsApp del cliente no esté visible en la tarjeta del pedido."""
        btn = self.get_whatsapp_button(order_id)
        from playwright.sync_api import expect
        expect(btn).not_to_be_visible(timeout=5000)

    def verify_delivery_info(self, order_id: str, cost: str = None, distance: str = None):
        """Verifica que la tarjeta muestre el desglose de delivery con costo y/o distancia."""
        card = self.get_order_card(order_id)
        card.wait_for(state="visible", timeout=15000)
        from playwright.sync_api import expect
        expect(card.locator("text=/Delivery/i").first).to_be_visible(timeout=5000)
        if cost:
            expect(card.locator(f"text=/\\+Bs\\.\\s*{cost}/i").first).to_be_visible(timeout=5000)
        if distance:
            expect(card.locator(f"text=/{distance}\\s*km/i").first).to_be_visible(timeout=5000)

    def get_delivery_map_link(self, order_id: str):
        """Devuelve el enlace al mapa de Google Maps con la ubicación de entrega del pedido."""
        card = self.get_order_card(order_id)
        return card.locator(f"[data-testid='delivery-map-btn-{order_id}']")

    def verify_delivery_map_link_visible(self, order_id: str):
        """Verifica que el enlace para ver el mapa de entrega esté visible y contenga URL de Google Maps."""
        link = self.get_delivery_map_link(order_id)
        from playwright.sync_api import expect
        expect(link).to_be_visible(timeout=5000)
        expect(link).to_have_attribute("href", re.compile(r"google\.com/maps.*"))

    def verify_handled_by(self, order_id: str, staff_name: str):
        """Verifica que la tarjeta del pedido muestre qué colaborador atendió la orden."""
        card = self.get_order_card(order_id)
        card.wait_for(state="visible", timeout=15000)
        from playwright.sync_api import expect
        expect(card.locator(f"text=/Atendido por:\\s*{staff_name}/i")).to_be_visible(timeout=10000)

