Feature: Staff Operational RBAC and Order Processing
  As a business collaborator or owner
  I want staff members to access operational views, manage orders, and receive payment alerts
  So that day-to-day operations are distributed safely according to assigned permissions

  @smoke @e2e
  Scenario: Collaborator views assigned business in my businesses panel and toggles open status conditionally
    Given a premium business "Restaurante Staff Test" with owner "Dueño Op Test" and slug "restaurante-staff"
    And a registered collaborator "Colaborador Operativo Test" is assigned to the business with default permissions
    When the collaborator logs in and navigates to the my businesses page
    Then the business card displays the "Colaborador" badge
    And the public card and open-close toggle buttons are visible
    And the metrics and delete request buttons are not visible for the collaborator
    When the collaborator toggles the open-close switch
    Then the toggle shows closed state for the business
    When the owner revokes the "can_toggle_open" permission for the collaborator via API
    And the collaborator attempts to toggle open-close via API
    Then the API rejects the toggle with status 403 and permission denied message

  @e2e
  Scenario: Direct sale and payment verification with handled_by traceability
    Given a premium business "Operativa Pedidos Test" with owner "Dueño Pedidos Test" and slug "operativa-pedidos"
    And a registered collaborator "Colaborador Ventas Test" is assigned to the business with default permissions
    When the collaborator processes a direct sale order of 50 Bs via API
    Then the order is created with status "completado" and handled_by assigned to the collaborator
    When the collaborator logs in and navigates to orders page for "operativa-pedidos"
    Then the direct sale order card displays "Atendido por: Colaborador Ventas Test"
    When a customer creates an order with QR payment and submits a receipt
    Then the customer order is in status "pago_enviado" with handled_by unassigned
    When the collaborator verifies and approves the customer payment
    Then the customer order status is updated to "pagado" and handled_by is assigned to the collaborator
    When the owner logs in and navigates to orders page for "operativa-pedidos"
    Then the customer order card displays "Atendido por: Colaborador Ventas Test"

  @push @e2e
  Scenario: Multi-recipient push notification dispatch for payment receipts to authorized business team
    Given a premium business "Push Alertas Test" with owner "Dueño Push Test" and slug "push-alertas"
    And a collaborator "Staff Alerta ON Test" with payment notifications enabled and web push subscription
    And a collaborator "Staff Alerta OFF Test" with payment notifications disabled and web push subscription
    And the owner has an active web push subscription
    When a customer creates an order and uploads a payment receipt
    Then the background task dispatches push notifications to the business team
    And the owner receives the payment push notification with dollar icon
    And "Staff Alerta ON Test" receives the payment push notification
    And "Staff Alerta OFF Test" does not receive the payment push notification
