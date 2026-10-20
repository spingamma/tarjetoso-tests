from playwright.sync_api import Page, expect
from poms.base_page import BasePage
import os


class MyBusinessesPage(BasePage):
    """
    Representa el panel de gestión 'Mis Negocios' (/mis-negocios).
    Tipo de App: SPA (React)
    """

    def __init__(self, page: Page):
        super().__init__(page)
        self.page_title = page.locator("h1:has-text('Mis Negocios')")
        self.nuevo_negocio_btn = page.locator("a:has-text('Nuevo Negocio')")
        self.open_team_modal_btn = page.locator("[data-testid='open-team-modal-btn']")
        self.team_modal = page.locator("div.fixed.inset-0:has-text('Gestionar Equipo')")

    def go_to(self):
        """Navega a la vista de Mis Negocios."""
        base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
        self.page.goto(f"{base_url}/mis-negocios")
        self.verify_page_loaded()

    def verify_page_loaded(self):
        """Verifica que la página de Mis Negocios cargó correctamente."""
        self.page.wait_for_load_state("networkidle")
        expect(self.page_title).to_be_visible(timeout=10000)

    def get_business_card(self, slug: str):
        """Retorna el contenedor de la tarjeta del negocio con el slug indicado."""
        return self.page.locator("div", has=self.page.locator(f"[data-testid='toggle-open-{slug}'], [data-testid='orders-btn-{slug}']")).filter(has=self.page.locator("[data-testid='open-team-modal-btn']")).first

    def get_toggle_switch(self, slug: str):
        """Devuelve el locator del switch Abierto/Cerrado para un negocio."""
        return self.page.locator(f"[data-testid='toggle-open-{slug}']")

    def toggle_business_open(self, slug: str):
        """Hace click en el switch de Abierto/Cerrado de un negocio."""
        toggle = self.get_toggle_switch(slug)
        expect(toggle).to_be_visible(timeout=5000)
        toggle.click()

    def verify_toggle_state(self, slug: str, is_open: bool):
        """Verifica el estado visual del switch (Abierto o Cerrado)."""
        toggle = self.get_toggle_switch(slug)
        expect(toggle).to_be_visible(timeout=5000)
        expected_text = "Abierto" if is_open else "Cerrado"
        expect(toggle.locator("span", has_text=expected_text)).to_be_visible(timeout=5000)

    def verify_collaborator_badge_visible(self):
        """Verifica que el badge '👥 Colaborador' esté visible en la tarjeta del negocio."""
        badge = self.page.locator("[data-testid='colaborador-badge']")
        expect(badge).to_be_visible(timeout=5000)
        expect(badge).to_contain_text("Colaborador")

    def verify_metrics_button_not_visible(self):
        """Verifica que el botón de Métricas NO esté disponible para el colaborador."""
        metrics_btn = self.page.locator("a[href*='/metricas/'], button:has-text('Métricas')")
        expect(metrics_btn).not_to_be_visible(timeout=3000)

    def verify_delete_button_not_visible(self):
        """Verifica que el botón 'Eliminar Solicitud' NO esté visible para el colaborador."""
        delete_btn = self.page.locator("button:has-text('Eliminar Solicitud')")
        expect(delete_btn).not_to_be_visible(timeout=3000)

    def get_team_modal_btn(self, slug: str = None):
        """Retorna el locator del botón 'Gestionar equipo' en Mis Negocios."""
        if slug:
            card = self.get_business_card(slug)
            if card.count() > 0:
                card_btn = card.locator("[data-testid='open-team-modal-btn']")
                if card_btn.count() > 0:
                    return card_btn
        return self.open_team_modal_btn.first

    def open_team_management(self, slug: str = None):
        """Abre el modal de gestión de colaboradores desde la tarjeta en Mis Negocios."""
        btn = self.get_team_modal_btn(slug)
        expect(btn).to_be_visible(timeout=5000)
        btn.click()
        expect(self.team_modal).to_be_visible(timeout=5000)

    def verify_team_management_btn_visible(self, slug: str = None):
        """Verifica que el botón 'Gestionar equipo' esté visible en Mis Negocios."""
        btn = self.get_team_modal_btn(slug)
        expect(btn).to_be_visible(timeout=5000)

    def verify_team_management_btn_not_visible(self, slug: str = None):
        """Verifica que el botón 'Gestionar equipo' NO esté visible en Mis Negocios."""
        btn = self.get_team_modal_btn(slug)
        expect(btn).not_to_be_visible(timeout=3000)

    def get_orders_button(self, slug: str):
        """Retorna el locator del botón 'Ordenes' para el negocio."""
        return self.page.locator(f"[data-testid='orders-btn-{slug}']")

    def verify_orders_button_visible(self, slug: str):
        """Verifica que el botón 'Ordenes' esté visible para el negocio."""
        expect(self.get_orders_button(slug)).to_be_visible(timeout=5000)

    def verify_view_card_link(self, slug: str):
        """Verifica el link 'Ver Tarjeta' (nuevo texto sin 'Pública')."""
        card = self.get_business_card(slug)
        link = card.locator("a", has_text="Ver Tarjeta")
        expect(link).to_be_visible(timeout=5000)
