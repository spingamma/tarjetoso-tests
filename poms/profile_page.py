from playwright.sync_api import Page, expect
from poms.base_page import BasePage

class ProfilePage(BasePage):
    """
    Representa el perfil público de un negocio (Catálogo de productos).
    Tipo de App: SPA (React)
    """

    def __init__(self, page: Page):
        super().__init__(page)
        self.edit_profile_btn = page.locator("[data-testid='edit-profile-btn']")
        self.open_inventory_btn = page.locator("[data-testid='open-inventory-btn']")
        self.save_catalog_btn = page.locator("[data-testid='save-catalog-btn']")
        self.close_inventory_btn = page.locator("[data-testid='close-inventory-btn']")
        self.catalog_modal = page.locator("[data-testid='catalog-edit-modal']")
        self.orders_enabled_checkbox = page.locator("[data-testid='ordersEnabledCheckbox']")
        self.delivery_pickup_checkbox = page.locator("[data-testid='delivery-method-pickup-checkbox']")
        self.delivery_courier_checkbox = page.locator("[data-testid='delivery-method-delivery-checkbox']")
        self.add_product_btn = page.locator("[data-testid='add-product-btn']")
        self.product_modal = page.locator("[data-testid='product-modal-content']")
        self.product_cancel_btn = page.locator("[data-testid='product-modal-cancel-btn']")
        self.product_close_btn = page.locator("[data-testid='product-modal-close-btn']")
        self.add_choice_btn = page.locator("[data-testid='add-choice-btn']")
        self.product_name_input = page.locator("[data-testid='product-name-input']")
        self.product_submit_btn = page.locator("[data-testid='product-modal-submit-btn']")
        self.toggle_open_btn = page.locator("[data-testid='business-toggle-open-btn']")
        self.hero_closed_badge = page.locator("[data-testid='hero-closed-badge']")
        self.banner_img = page.locator("img[alt^='Foto de perfil de']")
        self.checkout_btn = page.locator("[data-testid='order-checkout-btn']")
        self.open_team_modal_btn = page.locator("[data-testid='open-team-modal-btn']")
        self.team_modal = page.locator("div.fixed.inset-0:has-text('Gestionar Equipo')")

    def open_catalog_editor(self):
        """Abre el modal de edición de catálogo independiente."""
        self.open_inventory_btn.click()
        expect(self.catalog_modal).to_be_visible(timeout=5000)

    def save_catalog(self):
        """Guarda los cambios del catálogo desde el modal independiente."""
        self.save_catalog_btn.click()
        expect(self.catalog_modal).not_to_be_visible(timeout=10000)

    def click_add_product(self):
        """Abre el modal para crear o editar un producto dentro del catálogo."""
        self.add_product_btn.click()
        expect(self.product_modal).to_be_visible(timeout=5000)

    def cancel_product_form(self):
        """Cancela y cierra el formulario de producto."""
        self.product_cancel_btn.click()
        expect(self.product_modal).not_to_be_visible(timeout=5000)

    def click_add_choice(self):
        """Hace click en 'Añadir' en la sección A elección."""
        expect(self.add_choice_btn).to_be_visible(timeout=5000)
        self.add_choice_btn.click()

    def fill_choice_input(self, idx: int, value: str):
        """Llena el input de opción en el índice indicado."""
        input_locator = self.page.locator(f"[data-testid='choice-input-{idx}']")
        expect(input_locator).to_be_visible(timeout=5000)
        input_locator.fill(value)

    def remove_choice(self, idx: int):
        """Hace click en el botón de quitar ('-') de la opción en el índice indicado."""
        btn_locator = self.page.locator(f"[data-testid='remove-choice-btn-{idx}']")
        expect(btn_locator).to_be_visible(timeout=5000)
        btn_locator.click()

    def count_choice_inputs(self) -> int:
        """Retorna la cantidad de inputs de choices visibles actualmente."""
        return self.page.locator("[data-testid^='choice-input-']").count()

    def get_choice_input_value(self, idx: int) -> str:
        """Retorna el valor actual del input de choice en el índice dado."""
        return self.page.locator(f"[data-testid='choice-input-{idx}']").input_value()

    def fill_product_name(self, name: str):
        """Llena el nombre del producto."""
        expect(self.product_name_input).to_be_visible(timeout=5000)
        self.product_name_input.fill(name)

    def submit_product_form(self):
        """Envía el formulario de producto para guardarlo."""
        expect(self.product_submit_btn).to_be_visible(timeout=5000)
        self.product_submit_btn.click()
        expect(self.product_modal).not_to_be_visible(timeout=10000)



    
    def go_to(self, slug: str):
        """Navega al perfil del negocio por su slug."""
        import os
        base_url = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
        
        try:
            with self.page.expect_response(lambda response: "businesses/" in response.url, timeout=30000) as response_info:
                self.page.goto(f"{base_url}/perfil/{slug}")
            api_resp = response_info.value
            print(f"API RESPONSE FOR {slug}:", api_resp.json())
        except Exception as e:
            print("FAILED TO CAPTURE API RESPONSE:", e)
            self.page.goto(f"{base_url}/perfil/{slug}")
            
        self.verify_page_loaded()
        
    def verify_page_loaded(self):
        self.page.wait_for_load_state("networkidle")
        try:
            # Esperar a que se rendericen las tarjetas de producto en el carrusel (compatibles con Free y Premium)
            self.page.wait_for_selector(".snap-center h4, [data-testid^='add-to-cart-btn-']", timeout=15000)
        except Exception as e:
            print("DEBUG ERROR en verify_page_loaded:", e)
        
    def add_to_cart(self, product_id: str):
        """Agrega un producto al carrito usando su ID."""
        # Se requiere usar .first porque el carrusel duplica los elementos
        self.page.locator(f"[data-testid='add-to-cart-btn-{product_id}']").first.click()
        
    def add_random_product_to_cart(self):
        """Busca el primer producto disponible y lo agrega al carrito."""
        btn = self.page.locator("[data-testid^='add-to-cart-btn-']").first
        btn.click()
        
    def go_to_checkout(self):
        """Hace click en el botón flotante para proceder al checkout."""
        self.page.locator("[data-testid='order-checkout-btn']").click()

    def get_unique_product_names(self):
        """Retorna el conjunto de nombres de productos únicos mostrados en el catálogo."""
        self.verify_page_loaded()
        elements = self.page.locator(".snap-center h4").all()
        names = set()
        for el in elements:
            text = el.inner_text().strip()
            if text:
                names.add(text)
        return names

    def get_unique_product_ids(self):
        """Retorna el conjunto de IDs de productos únicos mostrados en el catálogo (solo planes con pedidos habilitados)."""
        self.verify_page_loaded()
        buttons = self.page.locator("[data-testid^='add-to-cart-btn-']").all()
        ids = set()
        for btn in buttons:
            tid = btn.get_attribute("data-testid")
            if tid:
                pid = tid.replace("add-to-cart-btn-", "")
                ids.add(pid)
        return ids

    def toggle_open_close(self):
        """Hace click en el botón de Abierto/Cerrado del banner de perfil."""
        expect(self.toggle_open_btn).to_be_visible(timeout=5000)
        self.toggle_open_btn.click()

    def verify_closed_sign_visible(self):
        """Verifica que el letrero 'Cerrado' esté visible en el banner."""
        expect(self.hero_closed_badge).to_be_visible(timeout=5000)

    def verify_closed_sign_not_visible(self):
        """Verifica que el letrero 'Cerrado' no esté visible en el banner."""
        expect(self.hero_closed_badge).not_to_be_visible(timeout=5000)

    def verify_grayscale_banner(self, has_grayscale: bool):
        """Verifica que la imagen del banner tenga o no la clase grayscale."""
        expect(self.banner_img).to_be_visible(timeout=5000)
        import re
        if has_grayscale:
            expect(self.banner_img).to_have_class(re.compile(r"grayscale"))
        else:
            expect(self.banner_img).not_to_have_class(re.compile(r"grayscale"))

    def verify_checkout_not_available(self):
        """Verifica que el botón de checkout no esté disponible (bloqueado por cierre)."""
        expect(self.checkout_btn).not_to_be_visible(timeout=3000)

    def open_team_management(self):
        """Abre el modal de gestión de colaboradores."""
        expect(self.open_team_modal_btn).to_be_visible(timeout=5000)
        self.open_team_modal_btn.click()
        expect(self.team_modal).to_be_visible(timeout=5000)

    def verify_team_management_btn_visible(self):
        """Verifica que el botón 'Gestionar equipo' esté visible."""
        expect(self.open_team_modal_btn).to_be_visible(timeout=5000)

    def verify_team_management_btn_not_visible(self):
        """Verifica que el botón 'Gestionar equipo' NO esté visible en el banner de perfil."""
        expect(self.open_team_modal_btn).not_to_be_visible(timeout=3000)

    def get_product_visibility_toggle(self, product_id: str):
        """Retorna el locator del botón de visibilidad de un producto en la tarjeta digital."""
        return self.page.locator(f"[data-testid='toggle-visibility-{product_id}']").first

    def toggle_product_visibility(self, product_id: str):
        """Hace click en el botón de visibilidad del producto en la tarjeta digital."""
        btn = self.get_product_visibility_toggle(product_id)
        expect(btn).to_be_visible(timeout=5000)
        btn.click()

    def get_hidden_badge(self, product_id: str):
        """Retorna el badge 'Oculto' del producto cuando está deshabilitado para clientes."""
        return self.page.locator(f"[data-testid='badge-hidden-{product_id}']").first

    def is_product_visible_in_catalog(self, name: str) -> bool:
        """Verifica si un producto con dicho nombre está presente y visible en el catálogo."""
        cards = self.page.locator(f".snap-center h4:has-text('{name}')")
        return cards.count() > 0 and cards.first.is_visible()

    def toggle_delivery_pickup(self):
        """Alterna el checkbox de Entrega en local en el modal de catálogo."""
        self.delivery_pickup_checkbox.click()

    def toggle_delivery_courier(self):
        """Alterna el checkbox de Delivery en el modal de catálogo."""
        self.delivery_courier_checkbox.click()

    def is_delivery_pickup_checked(self) -> bool:
        """Verifica si el checkbox de Entrega en local está marcado."""
        return self.delivery_pickup_checkbox.is_checked()

    def is_delivery_courier_checked(self) -> bool:
        """Verifica si el checkbox de Delivery está marcado."""
        return self.delivery_courier_checkbox.is_checked()

