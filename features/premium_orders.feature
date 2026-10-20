Feature: Flujo E2E de Pedidos a Comercios Premium
  Como cliente
  Quiero poder hacer un pedido a un comercio premium y subir mi comprobante
  Para que el comercio gestione mi pedido hasta entregarlo

  Scenario: Journey Completo de Compra QR y Transición de Estados
    Given a premium business exists with name "Super Burger Test" and slug "super-burger-test"
    And a product "Hamburguesa Test" exists for "super-burger-test"
    When the seller of "super-burger-test" logs in
    And the seller enables orders in catalog settings
    Given a buyer user is logged in
    When the buyer goes to "super-burger-test" profile
    And the buyer adds "Hamburguesa Test" to the cart
    And the buyer proceeds to checkout
    And the buyer fills customer name "Juan Test" and selects "Transferencia / QR"
    And the buyer confirms the order
    Then the buyer sees order tracking in "pendiente_de_pago" status
    When the buyer uploads a receipt image
    Then the order status changes to "pago_enviado"
    When the seller of "super-burger-test" logs in
    And the seller navigates to their business orders
    Then the seller sees the order as "Pago Enviado"
    When the seller marks the order as paid
    Then the seller sees the order as "Pagado"
    When the seller marks the order as delivered
    Then the seller sees the order as "Entregado"

  Scenario: Seller enters a direct sale and order is finalized immediately
    Given a premium business exists with name "Direct Burger Test" and slug "direct-burger-test"
    And a product "Hamburguesa Directa Test" exists for "direct-burger-test"
    When the seller of "direct-burger-test" logs in
    And the seller enables orders in catalog settings
    And the seller goes to "direct-burger-test" profile
    And the seller adds "Hamburguesa Directa Test" to the cart
    And the seller proceeds to checkout
    And the seller fills customer name "Cliente Local Test" and selects "efectivo"
    And the seller confirms the order
    Then the order is created in final state and does not ask for payment
