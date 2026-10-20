from playwright.sync_api import Page, expect
from .base_page import BasePage

class HeaderPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        # Menu mobile o header desktop que contiene el PushToggle
        import re
        self.user_menu_button = page.locator("header button").filter(has_text=re.compile(r"Hola", re.IGNORECASE)).or_(
            page.locator("header button:has(div.bg-primary\\/90)")
        )
        self.notifications_button = page.locator("button:has-text('Notificaciones')")
        self.notifications_icon_active = self.notifications_button.locator("svg.text-secondary")
        self.notifications_icon_inactive = self.notifications_button.locator("svg.text-gray-400")
        
    def verify_page_loaded(self):
        try:
            self.page.wait_for_selector("#splash-screen", state="detached", timeout=8000)
        except Exception:
            pass
        expect(self.user_menu_button).to_be_visible(timeout=10000)

    def open_user_menu(self):
        # Only click if the notifications button is not visible
        if not self.notifications_button.is_visible():
            self.user_menu_button.click()
            expect(self.notifications_button).to_be_visible()

    def click_notifications_toggle(self):
        self.open_user_menu()
        self.notifications_button.click()
        
    def expect_notifications_active(self):
        expect(self.notifications_icon_active).to_be_visible(timeout=5000)
        
    def expect_notifications_inactive(self):
        expect(self.notifications_icon_inactive).to_be_visible(timeout=5000)
