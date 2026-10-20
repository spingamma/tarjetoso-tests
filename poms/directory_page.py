from playwright.sync_api import Page, expect
from .base_page import BasePage

class DirectoryPage(BasePage):
    """POM for Directory View (SPA React)."""

    def __init__(self, page: Page):
        super().__init__(page)
        
        # Locators
        self.search_input = page.get_by_test_id("search-input")
        self.search_button = page.get_by_test_id("search-button")
        
        # Filtros Combinados (DirectoryFilterBar)
        self.category_badge = page.get_by_test_id("category-badge")
        self.location_dropdown_btn = page.get_by_test_id("filter-trigger-location")
        self.rating_dropdown_btn = page.get_by_test_id("filter-trigger-rating")
        self.subcategory_dropdown_btn = page.get_by_test_id("filter-trigger-subcategory")
        
        # Resultados
        self.back_to_categories_btn = page.get_by_test_id("back-to-categories-btn")
        self.clear_filters_empty_btn = page.get_by_test_id("clear-filters-empty-btn")
        self.professional_cards = page.locator("[data-testid^='business-feed-card-']").or_(page.get_by_test_id("professional-card"))
        
    def navigate(self):
        """Navigates to the directory page and waits for base content to load."""
        import os
        base_url = os.getenv("BASE_URL", "http://localhost:5173/")
        self.page.goto(base_url)
        # Handle lazy loading splash screen explicitly
        try:
            self.page.wait_for_selector("#splash-screen", state="detached", timeout=5000)
        except:
            pass
        self.verify_page_loaded()

    def go_to(self):
        """Alias for navigate."""
        self.navigate()

    def verify_page_loaded(self):
        """Verifies directory page is visible."""
        expect(self.search_input).to_be_visible(timeout=10000)

    def search_term(self, term: str):
        """Fills the search input and presses search."""
        self.search_input.fill(term)
        self.search_button.click()

    def search_by_text(self, term: str):
        """Alias for search_term."""
        self.search_term(term)

    def get_business_card(self, slug: str):
        """Devuelve la tarjeta del negocio en el directorio por su slug."""
        return self.page.locator(f"[data-testid='business-feed-card-{slug}']").or_(
            self.page.locator(f"a[data-testid='professional-card'][href*='{slug}']")
        )

    def verify_card_closed(self, slug: str):
        """Verifica que la tarjeta del negocio en el directorio tenga badge 'Cerrado' y estilo grayscale u opacity."""
        card = self.get_business_card(slug)
        expect(card).to_be_visible(timeout=10000)
        closed_badge = card.locator(
            f"[data-testid='feed-closed-badge-{slug}'], [data-testid='card-closed-badge']"
        ).or_(card.get_by_text("Cerrado")).first
        expect(closed_badge).to_be_visible(timeout=5000)
        import re
        expect(card).to_have_class(re.compile(r"(grayscale|opacity-90)"))


