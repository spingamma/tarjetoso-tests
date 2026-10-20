Feature: Choices API Persistence and Edge Cases
  As the system
  I want product choices and order selected_choices to persist correctly
  So that both buyer and seller see the correct data

  Scenario: Product choices persist via API and order carries selected_choices
    Given a premium business "API Choices Test" with slug "api-choices-test" is created via API
    When a product "Pizza Especial Test" is created with choices '["Extra Queso", "Jalapeños"]' via API
    Then the product response contains choices '["Extra Queso", "Jalapeños"]'
    When a product listing is fetched for the business
    Then the product appears with non-null choices
    When an order is created with selected_choices '["Extra Queso"]' for that product
    Then the order response item contains selected_choices '["Extra Queso"]'
    When the business orders are listed
    Then the order item still contains selected_choices '["Extra Queso"]'

  Scenario: Edge case empty choices string and null selected_choices
    Given a premium business "Edge Choices Test" with slug "edge-choices-test" is created via API
    When a product "Pizza Simple Test" is created without choices via API
    Then the product response has null choices
    When an order is created without selected_choices for that product
    Then the order response item has null selected_choices
