Feature: QR and Receipt Image Zoom Modal
  As a Customer viewing my order tracking
  I want to click on QR and receipt images to see them enlarged
  So that I can verify payment details clearly

  Scenario: Customer enlarges QR image and closes the modal
    Given a pending order with QR payment method
    When the customer clicks the QR payment image in tracking
    Then a fullscreen modal appears with the enlarged QR image
    And the modal has a dark backdrop and a close button
    When the customer clicks the close button
    Then the modal closes and the page returns to normal

  Scenario: Customer enlarges receipt image in tracking view
    Given an order in "pago_enviado" status with uploaded receipt
    When the customer clicks the receipt image in tracking
    Then a fullscreen modal appears with the enlarged receipt
    When the customer clicks outside the modal
    Then the modal closes
