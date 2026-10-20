# Archivo: poms/edit_business_location_page.py
"""
Page Object Model for the Location section of the Business Edit form.

Encapsulates the location-related locators within HeroInfoEdit.jsx:
- Google Maps URL input
- Success indicator (green "Ubicación detectada correctamente")
- Warning indicator (orange "No pudimos extraer coordenadas")
- Resolving spinner (Loader2)

Used in: short_url_location.feature tests.
"""
import os
from playwright.sync_api import Page, expect
from poms.base_page import BasePage


class EditBusinessLocationPage(BasePage):
    """POM for the location section of the business edit form."""

    def __init__(self, page: Page):
        super().__init__(page)

        # Location URL input field
        self.ubicacion_url_input = page.locator("input[name='ubicacion_url']")

        # Success indicator: green div with "Ubicación detectada correctamente"
        self.location_success_indicator = page.locator(
            "text=Ubicación detectada correctamente"
        )

        # Warning indicator: orange div with "No pudimos extraer coordenadas"
        self.location_warning_indicator = page.locator(
            "text=No pudimos extraer coordenadas del enlace"
        )

        # Resolving spinner (Loader2 with animate-spin)
        self.resolving_spinner = page.locator(".animate-spin")

        # Edit profile button (to enter edit mode)
        self.edit_profile_btn = page.get_by_test_id("edit-profile-btn")

    def navigate_to_business(self, slug: str):
        """Navigate to a business profile by slug."""
        base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
        self.page.goto(f"{base_url}/perfil/{slug}")
        self.verify_page_loaded()

    def verify_page_loaded(self):
        """Verify the profile page has loaded."""
        self.page.wait_for_load_state("networkidle")
        # Wait for the edit button to confirm it's the owner's view
        self.edit_profile_btn.wait_for(state="visible", timeout=15000)

    def enter_edit_mode(self):
        """Click the edit button to enter edit mode."""
        self.edit_profile_btn.click()
        # Wait for the location input to appear (edit mode renders HeroInfoEdit)
        expect(self.ubicacion_url_input).to_be_visible(timeout=10000)

    def fill_location_url(self, url: str):
        """Clear and fill the location URL field."""
        self.ubicacion_url_input.clear()
        self.ubicacion_url_input.fill(url)

    def wait_for_resolution_complete(self, timeout: int = 15000):
        """Wait for the resolving spinner to appear and then disappear.
        
        The frontend has an 800ms debounce before triggering the API call,
        plus the time for the HTTP request + redirect resolution.
        """
        try:
            # Wait for spinner to appear (debounce + request start)
            self.resolving_spinner.wait_for(state="visible", timeout=5000)
        except Exception:
            # Spinner may have already disappeared if resolution was fast
            pass

        # Wait for spinner to disappear (resolution complete)
        self.resolving_spinner.wait_for(state="hidden", timeout=timeout)

    def is_success_visible(self) -> bool:
        """Check if the green success indicator is visible."""
        return self.location_success_indicator.is_visible()

    def is_warning_visible(self) -> bool:
        """Check if the orange warning indicator is visible."""
        return self.location_warning_indicator.is_visible()
