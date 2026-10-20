from poms.base_page import BasePage

class OrderTrackingPage(BasePage):
    """
    Representa la vista de tracking y comprobante de un pedido para el comprador.
    Tipo de App: SPA (React)
    """

    def get_status_text(self):
        """Retorna el estado actual visible en la página (a través del header de estado o texto en la pantalla)."""
        # Como no vi un testid para el texto del estado directamente en TrackingSection, podemos buscar el texto que incluye el estado o usar un locator genérico.
        # En la UI actual el estado se mapea a palabras como "Pendiente de pago", "En preparación", etc.
        # Por ahora esperaremos a que la UI se renderice y podemos usar la aserción directamente en el test.
        pass

    def wait_for_status(self, status: str):
        """Espera a que el estado del pedido se actualice."""
        self.page.locator(f"[data-testid='order-status-{status}']").wait_for(state="visible")
        
    def verify_page_loaded(self):
        self.page.wait_for_load_state("networkidle")

    def upload_payment_receipt(self, file_path: str):
        """Sube el comprobante de pago."""
        # El input file no tiene testid, pero es el único input de type file en la vista de subida.
        file_input = self.page.locator("input[type='file']")
        file_input.set_input_files(file_path)

    def verify_status(self, status: str):
        """Verifica que un estado específico esté visible en la página."""
        self.page.wait_for_selector(f"text={status}")

    def upload_receipt(self, file_path: str):
        """Sube el comprobante de pago."""
        # El input file no tiene testid, pero es el único input de type file en la vista de subida.
        file_input = self.page.locator("input[type='file']")
        file_input.set_input_files(file_path)

    def submit_receipt(self):
        """Envía el comprobante cargado."""
        self.page.locator("[data-testid='submit-receipt-btn']").click()

    def click_qr_image(self):
        """Hace clic en la imagen del QR para ampliarla."""
        qr_btn = self.page.locator("[data-testid='enlarge-qr-btn']")
        qr_btn.wait_for(state="visible", timeout=10000)
        qr_btn.click()

    def click_receipt_image(self):
        """Hace clic en la imagen del comprobante subido para ampliarla."""
        receipt_img = self.page.locator("img[alt='Comprobante enviado']")
        receipt_img.wait_for(state="visible", timeout=10000)
        receipt_img.click()

    def verify_zoom_modal_open(self, title: str = None):
        """Verifica que el modal de imagen ampliada esté visible."""
        modal = self.page.locator("[data-testid='enlarged-image-modal']")
        modal.wait_for(state="visible", timeout=10000)
        if title:
            from playwright.sync_api import expect
            expect(modal.locator(f"text={title}")).to_be_visible(timeout=5000)

    def close_zoom_modal_via_button(self):
        """Cierra el modal de imagen ampliada haciendo clic en el botón de cerrar."""
        close_btn = self.page.locator("[data-testid='close-enlarged-image-btn']")
        close_btn.wait_for(state="visible", timeout=5000)
        close_btn.click()

    def close_zoom_modal_via_backdrop(self):
        """Cierra el modal de imagen ampliada haciendo clic en el backdrop oscuro."""
        # Se hace clic en la esquina del modal (fuera del contenedor interior)
        modal = self.page.locator("[data-testid='enlarged-image-modal']")
        modal.click(position={"x": 10, "y": 10})

    def verify_zoom_modal_closed(self):
        """Verifica que el modal de imagen ampliada ya no esté visible."""
        from playwright.sync_api import expect
        modal = self.page.locator("[data-testid='enlarged-image-modal']")
        expect(modal).not_to_be_visible(timeout=5000)
