# Archivo: poms/choices_screen_page.py
"""
Page Object Model para la pantalla intermedia de selección de complementos (ChoicesScreen).
Ruta: /perfil/:slug/complementos
Tipo de App: SPA (React)
"""
from playwright.sync_api import Page, expect
from poms.base_page import BasePage


class ChoicesScreenPage(BasePage):
    """Representa la pantalla de selección de complementos (A elección) del comprador."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.back_button = page.locator("[data-testid='back-button-choices']")
        self.continue_button = page.locator("[data-testid='continue-to-order-btn']")
        self.header_title = page.locator("h1", has_text="Complementos de tu Pedido")
        self.banner_tag = page.locator("span", has_text="A elección")

    def verify_page_loaded(self):
        """Verifica que la pantalla de complementos cargó correctamente."""
        self.page.wait_for_load_state("networkidle")
        expect(self.header_title).to_be_visible(timeout=10000)

    def get_product_card(self, product_id_or_key: str = None):
        """Retorna el locator de la tarjeta de producto en la pantalla de complementos."""
        if product_id_or_key:
            return self.page.locator(f"[data-testid='choices-card-{product_id_or_key}']")
        return self.page.locator("[data-testid^='choices-card-']").first

    def toggle_choice(self, choice_text: str):
        """Hace click en la opción de complemento indicada por su texto."""
        option_label = self.page.locator(f"label:has-text('{choice_text}')").first
        expect(option_label).to_be_visible(timeout=5000)
        option_label.click()

    def get_selection_counter_text(self, product_id_or_key: str = None) -> str:
        """Obtiene el texto del contador de complementos seleccionados (ej: '2 selec.')."""
        card = self.get_product_card(product_id_or_key)
        counter_badge = card.locator("span:has-text('selec.')")
        expect(counter_badge).to_be_visible(timeout=5000)
        return counter_badge.inner_text().strip()

    def count_choices_for_product(self, product_id_or_key: str = None) -> int:
        """Cuenta la cantidad de opciones de complementos disponibles para el producto."""
        card = self.get_product_card(product_id_or_key)
        return card.locator("[data-testid^='choice-option-']").count()

    def is_ready_badge_visible(self, product_id_or_key: str = None) -> bool:
        """Verifica si el badge 'Listo' está visible (producto sin choices)."""
        card = self.get_product_card(product_id_or_key)
        return card.locator("span:has-text('Listo')").is_visible()

    def continue_to_order(self):
        """Hace click en 'Continuar al Pedido' y espera la navegación al checkout."""
        expect(self.continue_button).to_be_visible(timeout=5000)
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")
