import re
from playwright.sync_api import Page, expect
from poms.base_page import BasePage

class DeliveryDashboardPage(BasePage):
    """
    Page Object Model para el Tablero de Despachos de Delivery (/tablero-delivery).
    """

    def __init__(self, page: Page):
        super().__init__(page)
        # Topbar y navegación
        self.back_button = page.locator("[data-testid='delivery-back-btn']")
        self.tab_available = page.locator("[data-testid='tab-disponibles']")
        self.tab_my_deliveries = page.locator("[data-testid='tab-mis-entregas']")

        # Subpestañas en Mis Entregas
        self.subtab_active = page.locator("[data-testid='subtab-activas']")
        self.subtab_history = page.locator("[data-testid='subtab-historial']")

        # Filtros de fecha en historial
        self.start_date_input = page.locator("[data-testid='delivery-start-date']")
        self.end_date_input = page.locator("[data-testid='delivery-end-date']")
        self.filter_today_button = page.locator("[data-testid='delivery-filter-today-btn']")
        self.filter_week_button = page.locator("[data-testid='delivery-filter-week-btn']")
        self.filter_month_button = page.locator("[data-testid='delivery-filter-month-btn']")
        self.summary_card = page.locator("[data-testid='delivery-earnings-summary-card']")

        # Selector de zona y modo trabajo
        self.zone_select = page.locator("[data-testid='delivery-zone-select']")
        self.work_mode_toggle = page.locator("[data-testid='delivery-work-mode-toggle']")

    def verify_page_loaded(self):
        """Verifica que el tablero cargó correctamente."""
        expect(self.tab_available).to_be_visible(timeout=10000)
        expect(self.tab_my_deliveries).to_be_visible(timeout=10000)

    def ensure_work_mode_active(self):
        """Verifica que el modo trabajo esté activo; si está pausado, lo activa."""
        turn_paused = self.page.locator("text=Turno en Pausa")
        if turn_paused.is_visible():
            activate_btn = self.page.locator("button:has-text('Conectar y Activar Turno')")
            if activate_btn.is_visible():
                activate_btn.click()
                self.page.wait_for_timeout(500)

    def switch_to_available_tab(self):
        self.tab_available.click()
        expect(self.tab_available).to_have_class(re.compile(r".*bg-white.*"))

    def select_zone(self, department: str):
        self.zone_select.select_option(department)

    def switch_to_my_deliveries_tab(self):
        self.tab_my_deliveries.click()
        expect(self.tab_my_deliveries).to_have_class(re.compile(r".*bg-white.*"))

    def switch_to_active_subtab(self):
        self.switch_to_my_deliveries_tab()
        self.subtab_active.click()

    def switch_to_history_subtab(self):
        self.switch_to_my_deliveries_tab()
        self.subtab_history.click()

    def get_available_card(self, order_id: str):
        return self.page.locator(f"[data-testid='delivery-order-card-{order_id}']")

    def get_accept_button(self, order_id: str):
        return self.page.locator(f"[data-testid='accept-delivery-btn-{order_id}']")

    def get_blocked_button(self, order_id: str):
        return self.page.locator(f"[data-testid='blocked-delivery-btn-{order_id}']")

    def claim_order(self, order_id: str):
        btn = self.get_accept_button(order_id)
        expect(btn).to_be_visible()
        btn.click()

    def get_active_card(self, order_id: str):
        return self.page.locator(f"[data-testid='active-delivery-card-{order_id}']")

    def open_deliver_modal(self, order_id: str):
        btn = self.page.locator(f"[data-testid='deliver-order-btn-{order_id}']")
        expect(btn).to_be_visible()
        btn.click()
        # Verificar que el modal de confirmación se abre
        expect(self.page.locator(f"[data-testid='confirm-deliver-modal-btn-{order_id}']")).to_be_visible()

    def dismiss_deliver_modal(self):
        dismiss_btn = self.page.locator("button:has-text('Aún no')")
        expect(dismiss_btn).to_be_visible()
        dismiss_btn.click()
        expect(dismiss_btn).not_to_be_visible()

    def confirm_delivery(self, order_id: str):
        confirm_btn = self.page.locator(f"[data-testid='confirm-deliver-modal-btn-{order_id}']")
        expect(confirm_btn).to_be_visible()
        confirm_btn.click()

    def get_completed_card(self, order_id: str):
        return self.page.locator(f"[data-testid='completed-delivery-card-{order_id}']")

    def filter_history_by_dates(self, start_date: str, end_date: str):
        self.switch_to_history_subtab()
        self.start_date_input.fill(start_date)
        self.end_date_input.fill(end_date)
