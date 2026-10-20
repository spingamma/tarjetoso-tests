Feature: Payment Notification Lifecycle
  As a Business Owner and as a Customer
  I want to receive push notifications at each payment stage
  So that I am informed when a payment is sent and when it is accepted

  Scenario: Full payment notification cycle with correct redirect URLs
    Given a premium business "Notif Cycle Test" with push enabled for the owner
    And a customer "Client Notif Test" with push enabled
    When the customer places an order with "Transferencia / QR" payment
    And the customer uploads a payment receipt
    Then the backend sends a payment push to the owner with dollar icon
    And the owner push URL redirects to "/mis-pedidos/{slug}"
    When the business owner marks the order as paid
    Then the backend sends a payment accepted push to the customer
    And the customer push URL redirects to "/perfil/{slug}/orden/{order_id}"

  Scenario: Owner rejects payment and customer retries with new receipt
    Given a premium business "Reject Pay Test" with a "pago_enviado" order
    When the business owner rejects the payment with reason "Comprobante ilegible"
    Then the order returns to "pendiente_de_pago" status
    And the receipt URL is cleared
    And the backend sends a payment rejected push to the customer
    When the customer uploads a new receipt
    Then the order status changes to "pago_enviado"
    And a new push notification is sent to the business owner
    When the business owner marks the order as paid
    Then a payment accepted push notification is sent to the customer
