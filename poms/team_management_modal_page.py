from playwright.sync_api import Page, expect
from poms.base_page import BasePage


class TeamManagementModalPage(BasePage):
    """
    Representa el modal de gestión de colaboradores de un negocio (/perfil/{slug} -> Gestionar Equipo).
    Tipo de App: SPA (React)
    """

    def __init__(self, page: Page):
        super().__init__(page)
        self.modal_container = page.locator("div.fixed.inset-0:has-text('Gestionar Equipo')")
        self.close_btn = self.modal_container.locator("[data-testid='close-team-modal-btn']")
        self.search_input = self.modal_container.locator("[data-testid='staff-search-input']")
        self.search_btn = self.modal_container.locator("[data-testid='staff-search-btn']")
        self.confirm_add_btn = self.modal_container.locator("[data-testid='confirm-add-staff-btn']").first
        self.counter_badge = self.modal_container.locator("span.bg-secondary\\/15")
        self.limit_warning = self.modal_container.locator("text=/Has alcanzado el límite máximo de 2 colaboradores/i")
        self.error_alert = self.modal_container.locator("div.bg-red-50")

    def verify_page_loaded(self):
        """Verifica que el modal de gestión de equipo esté cargado y visible."""
        expect(self.modal_container).to_be_visible(timeout=5000)
        expect(self.close_btn).to_be_visible(timeout=5000)

    def search_candidate(self, query: str):
        """Escribe en el input de búsqueda y pulsa Buscar."""
        expect(self.search_input).to_be_visible(timeout=5000)
        self.search_input.fill(query)
        self.search_btn.click()

    def verify_candidate_preview(self, name: str):
        """Verifica que la tarjeta de previsualización del candidato esté visible con su nombre."""
        candidate_card = self.modal_container.locator(".bg-emerald-50", has_text=name)
        expect(candidate_card).to_be_visible(timeout=5000)

    def verify_candidate_count(self, expected_count: int):
        """Verifica la cantidad exacta de tarjetas de candidatos desplegadas."""
        cards = self.modal_container.locator(".bg-emerald-50")
        expect(cards).to_have_count(expected_count, timeout=5000)

    def confirm_add_staff_by_name(self, name: str):
        """Hace clic en 'Confirmar y Agregar' dentro de la tarjeta de un candidato específico."""
        card = self.modal_container.locator(".bg-emerald-50", has_text=name)
        btn = card.locator("[data-testid='confirm-add-staff-btn']")
        expect(btn).to_be_visible(timeout=5000)
        btn.click()

    def confirm_add_staff(self):
        """Hace clic en 'Confirmar y Agregar' para vincular al colaborador."""
        expect(self.confirm_add_btn).to_be_visible(timeout=5000)
        self.confirm_add_btn.click()

    def verify_staff_in_list(self, name: str):
        """Verifica que un colaborador aparezca listado en el equipo actual."""
        staff_item = self.modal_container.locator("[data-testid^='staff-item-']", has_text=name)
        expect(staff_item).to_be_visible(timeout=5000)

    def verify_staff_not_in_list(self, name: str):
        """Verifica que un colaborador ya no aparezca en el equipo actual."""
        staff_item = self.modal_container.locator("[data-testid^='staff-item-']", has_text=name)
        expect(staff_item).not_to_be_visible(timeout=5000)

    def verify_counter(self, expected_text: str):
        """Verifica el texto del contador de cupos (ej: '0 / 2', '1 / 2', '2 / 2')."""
        expect(self.counter_badge).to_have_text(expected_text, timeout=5000)

    def verify_limit_warning_visible(self):
        """Verifica que el banner de aviso de cupo máximo alcanzado esté visible."""
        expect(self.limit_warning).to_be_visible(timeout=5000)

    def verify_search_input_not_visible(self):
        """Verifica que el input de búsqueda no esté visible al alcanzar el cupo máximo."""
        expect(self.search_input).not_to_be_visible(timeout=3000)

    def verify_search_input_visible(self):
        """Verifica que el input de búsqueda esté visible."""
        expect(self.search_input).to_be_visible(timeout=5000)

    def verify_error_message(self, message_substring: str):
        """Verifica que se muestre un mensaje de error con un texto determinado."""
        expect(self.error_alert).to_be_visible(timeout=5000)
        expect(self.error_alert).to_contain_text(message_substring)

    def expand_permissions(self, staff_id: str):
        """Expande el acordeón de permisos para un colaborador específico."""
        toggle_btn = self.modal_container.locator(f"[data-testid='toggle-permissions-{staff_id}']")
        expect(toggle_btn).to_be_visible(timeout=5000)
        toggle_btn.click()

    def verify_permission_checkbox_visible(self, staff_id: str, perm_key: str):
        """Verifica que el checkbox del permiso indicado esté visible."""
        checkbox = self.modal_container.locator(f"[data-testid='perm-{perm_key}-{staff_id}']")
        expect(checkbox).to_be_visible(timeout=5000)

    def remove_staff(self, staff_id: str):
        """Remueve a un colaborador gestionando el confirm dialog nativo."""
        self.page.once("dialog", lambda dialog: dialog.accept())
        remove_btn = self.modal_container.locator(f"[data-testid='remove-staff-{staff_id}']")
        expect(remove_btn).to_be_visible(timeout=5000)
        remove_btn.click()

    def close_modal(self):
        """Cierra el modal haciendo clic en el botón 'X'."""
        expect(self.close_btn).to_be_visible(timeout=5000)
        self.close_btn.click()

    def close_modal_via_escape(self):
        """Cierra el modal presionando la tecla Escape."""
        self.page.keyboard.press("Escape")

    def verify_modal_closed(self):
        """Verifica que el modal se haya cerrado completamente."""
        expect(self.modal_container).not_to_be_visible(timeout=5000)
