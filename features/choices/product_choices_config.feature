Feature: Product Choices Configuration by Seller
  As a business owner
  I want to add optional choices to my products
  So that buyers can customize their orders

  Scenario: Seller adds and removes choices in the product form modal
    Given a seller is logged in with a premium business "Config Choices Test" and slug "config-choices-test"
    When the seller opens the catalog editor and clicks add product
    Then the product form modal is displayed with the "A elección" section
    When the seller clicks the add choice button
    Then a choice input field appears
    When the seller types "Ketchup" in choice input 0
    And the seller clicks the add choice button again
    And the seller types "Cebollín" in choice input 1
    And the seller removes choice 0

    Then only 1 choice input remains with value "Cebollín"
    When the seller fills product name "Producto Choices Config Test" and submits
    And the seller saves the catalog
    Then the product is created with choices containing "Cebollín"

