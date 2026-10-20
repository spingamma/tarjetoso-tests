from playwright.sync_api import Page, expect
from .base_page import BasePage

class PushPromptModalPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.modal_container = page.locator("text=Notificaciones de Pedidos").locator("..")
        self.permitir_button = page.locator("button:has-text('Permitir')")
        self.bloquear_button = page.locator("button:has-text('Bloquear')")
        
    def verify_page_loaded(self):
        expect(self.modal_container).to_be_visible(timeout=5000)
        expect(self.permitir_button).to_be_visible()

    def click_permitir(self):
        self.permitir_button.click()
        
    def click_bloquear(self):
        self.bloquear_button.click()
