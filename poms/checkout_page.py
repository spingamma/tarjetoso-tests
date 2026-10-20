from poms.base_page import BasePage

class CheckoutPage(BasePage):
    """
    Representa la vista de checkout para un pedido.
    Tipo de App: SPA (React)
    """

    def go_to_checkout(self):
        """Si la app redirige tras hacer click, lo usamos aquí."""
        pass

    def verify_page_loaded(self):
        self.page.wait_for_load_state("networkidle")

    def fill_customer_name(self, name: str):
        """Llena el nombre del cliente."""
        self.page.locator("[data-testid='customer-name-input']").fill(name)

    def select_delivery_method(self, method: str):
        """Selecciona el método de entrega."""
        self.page.locator("[data-testid='delivery-method-select']").select_option(label=method)

    def select_payment_method(self, method_value: str):
        """Selecciona el método de pago en el select de order summary (usado internamente, pero el usuario puede ser dueño o cliente).
        Para el caso del flujo de cliente, el método se escoge si está habilitado o viene por defecto QR."""
        # En la UI actual el cliente no escoge método de pago o usa un select con QR_simple por defecto si no es dueño.
        pass

    def confirm_order(self):
        """Confirma la orden haciendo clic en el botón principal."""
        btn_seller = self.page.locator("[data-testid='ingresar-venta-realizada-btn']")
        if btn_seller.is_visible():
            btn_seller.click()
        else:
            self.page.locator("[data-testid='confirm-order-btn']").click()

    def verify_choices_displayed(self, *choice_names: str):
        """Verifica que los complementos seleccionados aparezcan en el resumen del checkout."""
        from playwright.sync_api import expect
        for choice in choice_names:
            expect(self.page.locator(f"text=/{choice}/i").first).to_be_visible(timeout=5000)

    def verify_no_choices_displayed(self):
        """Verifica que ningún texto de complementos ('Con: ') aparezca en el resumen."""
        from playwright.sync_api import expect
        expect(self.page.locator("text=/Con:/i")).to_have_count(0)

    def open_delivery_map(self):
        """Abre el modal interactivo de mapa para confirmar ubicación de delivery."""
        self.page.locator("[data-testid='open-delivery-map-btn']").click()

    def confirm_delivery_map(self):
        """Hace clic en confirmar ubicación dentro del modal de mapa."""
        self.page.locator("[data-testid='map-confirm-button']").click()

    def verify_delivery_confirmed_visible(self):
        """Verifica que la tarjeta de ubicación de delivery confirmada esté visible."""
        from playwright.sync_api import expect
        expect(self.page.locator("[data-testid='delivery-location-confirmed-card']")).to_be_visible(timeout=5000)

    def search_in_delivery_map(self, query: str):
        """Llena el input de búsqueda del mapa y presiona el botón de búsqueda."""
        from playwright.sync_api import expect
        self.page.locator("[data-testid='map-search-input']").fill(query)
        self.page.locator("[data-testid='map-search-button']").click()
        # Esperar a que la búsqueda resuelva y habilite el botón de confirmar ubicación
        expect(self.page.locator("[data-testid='map-confirm-button']")).to_be_enabled(timeout=10000)

    def get_delivery_distance_value(self) -> float:
        """Obtiene la distancia numérica en km mostrada en la tarjeta de delivery."""
        import re
        text_val = self.page.locator("[data-testid='delivery-distance-info']").inner_text()
        match = re.search(r"([\d\.]+)", text_val)
        return float(match.group(1)) if match else 0.0

    def get_delivery_fee_value(self) -> float:
        """Obtiene el costo numérico de envío en Bs mostrado en la tarjeta de delivery."""
        import re
        text_val = self.page.locator("[data-testid='delivery-fee-info']").inner_text()
        match = re.search(r"([\d\.]+)", text_val)
        return float(match.group(1)) if match else 0.0

    def verify_delivery_fee_displayed(self, expected_fee: str):
        """Verifica el costo de envío mostrado en la tarjeta de delivery."""
        from playwright.sync_api import expect
        expect(self.page.locator("[data-testid='delivery-fee-info']")).to_contain_text(expected_fee, timeout=5000)

    def is_confirm_button_disabled(self) -> bool:
        """Verifica si el botón de confirmar pedido está deshabilitado."""
        return self.page.locator("[data-testid='confirm-order-btn']").is_disabled()

    def cancel_delivery_map(self):
        """Cierra el modal interactivo de mapa sin confirmar."""
        self.page.locator("[data-testid='map-close-button']").click()

    def verify_delivery_map_not_visible(self):
        """Verifica que el modal de mapa ya no esté visible."""
        from playwright.sync_api import expect
        expect(self.page.locator("[data-testid='map-close-button']")).not_to_be_visible(timeout=5000)

    def verify_business_no_location_alert_visible(self):
        """Verifica que aparezca la alerta de que el comercio no tiene coordenadas registradas."""
        from playwright.sync_api import expect
        expect(self.page.locator("[data-testid='business-no-location-alert']")).to_be_visible(timeout=5000)

    def verify_business_no_location_alert_not_visible(self):
        """Verifica que la alerta de negocio sin coordenadas no esté visible."""
        from playwright.sync_api import expect
        expect(self.page.locator("[data-testid='business-no-location-alert']")).not_to_be_visible(timeout=5000)

    def get_available_delivery_options(self):
        """Devuelve los textos de las opciones disponibles en el selector de método de entrega."""
        options = self.page.locator("[data-testid='delivery-method-select'] option")
        return [options.nth(i).inner_text().strip() for i in range(options.count())]

