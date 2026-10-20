Feature: Product Choices Selection During Purchase
  As a buyer
  I want to select optional complements for products that offer them
  So that my order reflects my personalized preferences

  Scenario: Buyer selects choices for a product and they persist in the order
    Given a premium business "Burger Choices Test" with slug "burger-choices-test" exists via API
    And orders are enabled for "burger-choices-test"
    And a product "Hamburguesa Especial Test" with choices '["Ketchup","Cebollín","Mayonesa"]' exists for "burger-choices-test"
    And a buyer user is logged in
    When the buyer navigates to the "burger-choices-test" profile
    And the buyer adds "Hamburguesa Especial Test" to the cart
    And the buyer clicks the order button
    Then the choices screen is displayed with title "Complementos de tu Pedido"
    And the product "Hamburguesa Especial Test" shows 3 choice options
    When the buyer selects "Ketchup" and "Mayonesa" as choices
    Then the selection counter shows "2 selec."
    When the buyer clicks "Continuar al Pedido"
    Then the checkout screen displays "Ketchup" and "Mayonesa" in the order summary
    When the buyer completes the checkout with name "Buyer Choices Test" and payment "Transferencia / QR"
    Then the order is created successfully
    When the seller of "burger-choices-test" logs in and views their orders
    Then the order item shows "Ketchup" and "Mayonesa" as selected choices

  Scenario: Product without choices skips directly to checkout
    Given a premium business "No Choices Test" with slug "no-choices-test" exists via API
    And orders are enabled for "no-choices-test"
    And a product "Hamburguesa Simple Test" without choices exists for "no-choices-test"
    And a buyer user is logged in
    When the buyer navigates to the "no-choices-test" profile
    And the buyer adds "Hamburguesa Simple Test" to the cart
    And the buyer clicks the order button
    Then the buyer is navigated directly to the checkout screen
    When the buyer completes the checkout with name "No Choices Buyer Test" and payment "efectivo"
    Then the order is created successfully
    And the order item has no selected choices

  Scenario: Buyer deselects all choices and order is created without selections
    Given a premium business "Deselect Choices Test" with slug "deselect-choices-test" exists via API
    And orders are enabled for "deselect-choices-test"
    And a product "Burger Deselect Test" with choices '["Ketchup","Cebollín"]' exists for "deselect-choices-test"
    And a buyer user is logged in
    When the buyer navigates to the "deselect-choices-test" profile
    And the buyer adds "Burger Deselect Test" to the cart
    And the buyer clicks the order button
    Then the choices screen is displayed with title "Complementos de tu Pedido"
    When the buyer selects "Ketchup" and then deselects "Ketchup"
    Then the selection counter shows "0 selec."
    When the buyer clicks "Continuar al Pedido"
    Then the checkout screen shows no choices in the order summary
    When the buyer completes the checkout with name "Deselect Buyer Test" and payment "efectivo"
    Then the order is created successfully
    And the order item has no selected choices
