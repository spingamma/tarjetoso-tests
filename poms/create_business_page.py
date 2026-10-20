# Archivo: poms/create_business_page.py
"""
Page Object Model para la página de Creación de Negocios en Tarjetoso.
Maneja la interacción con el formulario de creación, incluyendo el seller_code.

NOTA IMPORTANTE (sync-ui-changes 2026-07-10):
El formulario de /crear-negocio usa PlantillaGenerica en modo isCreateMode=true.
Los dropdowns de categoría y departamento se cargan de forma ASÍNCRONA:
  - Categorías: via GET /specialties/grouped (carga al montar el componente)
  - Países/Deptos: via GET /countries/ (carga al montar ProfileHero)
Por ello, NUNCA usar select_option() sin antes esperar que las opciones
estén disponibles con wait_for_loaded_state() o una espera explícita.
"""
import os
from playwright.sync_api import Page, expect
from .base_page import BasePage


class CreateBusinessPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        # Campos de texto (ProfileHero, editMode)
        self.name_input = page.locator("input[name='name']")
        self.title_input = page.locator("input[name='title']")
        self.description_input = page.locator("textarea[name='description']")

        # Dropdowns (carga asíncrona, NO usar antes de esperar)
        self.category_select = page.locator("select[name='category']")
        self.state_select = page.locator("select[name='state']")

        # Código de vendedor (solo visible en isCreateMode)
        self.seller_code_input = page.get_by_test_id("input-seller-code")

        # Botón flotante de guardar
        self.save_button = page.get_by_test_id("save-edit-btn")

    def navigate(self):
        base_url = os.getenv("BASE_URL", "http://localhost:5173/")
        self.page.goto(f"{base_url.rstrip('/')}/crear-negocio")

    def verify_page_loaded(self):
        """Verifica que el formulario de creación está visible y listo."""
        expect(self.name_input).to_be_visible(timeout=10000)

    def _wait_for_select_options(self, select_locator, timeout: int = 10000):
        """
        Espera a que un <select> tenga al menos una opción real (más allá
        del placeholder). Útil para selects que se poblan de forma async.
        """
        # En lugar de inyectar JS, usamos la API nativa de Playwright para esperar
        # a que la segunda opción (index 1, después del placeholder) se agregue al DOM.
        self.page.locator(f"{select_locator} option").nth(1).wait_for(
            state="attached", 
            timeout=timeout
        )

    def fill_business_info(self, name: str, title: str = "", description: str = ""):
        """Llena los campos básicos del negocio y selecciona el departamento."""
        self.name_input.fill(name)
        # El campo 'title' (Título o Especialidad) fue removido de la UI
        if self.title_input.is_visible():
            self.title_input.fill(title)
        desc_val = description if description else (title if not self.title_input.is_visible() and title else "")
        if desc_val:
            self.description_input.fill(desc_val)

        # Esperar a que el dropdown de países/departamentos esté cargado (async)
        self._wait_for_select_options("select[name='state']", timeout=12000)

        # Seleccionar el primer departamento real (índice 1, ya que 0 es el placeholder)
        self.state_select.select_option(index=1)

    def select_category_and_subcategory(self, category: str, subcategory: str):
        """
        Selecciona la categoría del dropdown (async) y luego hace clic
        en el botón pill de la subcategoría correspondiente.
        """
        # Esperar a que las categorías estén cargadas (async desde /specialties/grouped)
        self._wait_for_select_options("select[name='category']", timeout=12000)

        self.category_select.select_option(category)

        # Tras seleccionar la categoría, esperar la aparición del botón de subcategoría
        subcategory_button = self.page.get_by_role("button", name=subcategory, exact=True)
        expect(subcategory_button).to_be_visible(timeout=8000)
        subcategory_button.click()

    def fill_seller_code(self, seller_code: str):
        """Llena el campo de código de vendedor (opcional)."""
        self.seller_code_input.fill(seller_code)

    def submit_form(self):
        """Hace clic en el botón flotante 'Guardar Cambios'."""
        self.save_button.click()

    def verify_redirect_to_my_businesses(self, timeout: int = 10000):
        """Verifica que el usuario sea redirigido a la vista de Mis Negocios."""
        import re
        expect(self.page).to_have_url(re.compile(r".*/mis-negocios.*"), timeout=timeout)

