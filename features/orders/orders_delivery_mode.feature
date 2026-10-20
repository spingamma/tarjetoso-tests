Feature: Geolocated Delivery Mode and Dynamic Quoting Flow
  As a buyer purchasing from a premium business
  I want to calculate delivery fee using the interactive map and place delivery orders
  So that the business receives my exact delivery location and charges the correct shipping fee

  Scenario: Customer quotes and places an order with delivery mode using map
    Given a premium business with location exists with name "Burger Express Test" and slug "burger-express-test"
    And a product "Hamburguesa Delivery Test" exists for "burger-express-test"
    And the seller of "burger-express-test" has orders and delivery enabled
    Given a buyer user is logged in
    When the buyer goes to "burger-express-test" profile
    And the buyer adds "Hamburguesa Delivery Test" to the cart
    And the buyer proceeds to checkout
    When the buyer fills customer name "Carlos Test"
    And the buyer selects "Delivery" delivery method
    Then the confirm order button is disabled
    When the buyer opens the delivery map modal
    And the buyer confirms delivery location on the map
    Then the delivery location confirmed card is visible
    And the confirm order button is enabled
    When the buyer confirms the order
    Then the buyer sees order tracking with delivery fee
    When the seller of "burger-express-test" logs in
    And the seller navigates to their business orders
    Then the seller sees the order with delivery badge and map link

  Scenario: Checkout is blocked when business has no dispatch coordinates
    Given a premium business without location exists with name "No Map Store Test" and slug "no-map-store-test"
    And a product "Item Sin Mapa Test" exists for "no-map-store-test"
    And the seller of "no-map-store-test" has orders and delivery enabled
    Given a buyer user is logged in
    When the buyer goes to "no-map-store-test" profile
    And the buyer adds "Item Sin Mapa Test" to the cart
    And the buyer proceeds to checkout
    When the buyer fills customer name "Marcos Test"
    And the buyer selects "Delivery" delivery method
    Then the business no location alert is displayed
    And the confirm order button is disabled
    When the buyer selects "Entrega en el local" delivery method
    Then the business no location alert is not visible
    And the confirm order button is enabled

  Scenario: Submodal dismissal vector preserves parent checkout form state
    Given a premium business with location exists with name "Dismiss Modal Test" and slug "dismiss-modal-test"
    And a product "Combo Descarte Test" exists for "dismiss-modal-test"
    And the seller of "dismiss-modal-test" has orders and delivery enabled
    Given a buyer user is logged in
    When the buyer goes to "dismiss-modal-test" profile
    And the buyer adds "Combo Descarte Test" to the cart
    And the buyer proceeds to checkout
    When the buyer fills customer name "Valeria Test"
    And the buyer selects "Delivery" delivery method
    When the buyer opens the delivery map modal
    And the buyer cancels and closes the delivery map modal
    Then the delivery map modal is not visible
    And the parent checkout form remains visible with customer name "Valeria Test"
    And the confirm order button remains disabled

  Scenario: Catalog delivery methods configuration enforces minimum one invariant
    Given a premium business with location exists with name "Config Methods Test" and slug "config-methods-test"
    And a product "Hamburguesa Invariante Test" exists for "config-methods-test"
    When the seller of "config-methods-test" logs in
    And the seller opens the catalog editor
    When the seller unchecks the pickup delivery method
    And the seller attempts to uncheck the delivery courier method
    Then the delivery courier method remains checked
    When the seller saves the catalog configuration
    Given a buyer user is logged in
    When the buyer goes to "config-methods-test" profile
    And the buyer adds a product to cart and goes to checkout
    Then the delivery method select only contains "Delivery"

  Scenario: Buyer searches delivery location using Google Maps link in map modal
    Given a premium business with location exists with name "Search Maps Store Test" and slug "search-maps-store-test"
    And a product "Pizza Delivery Test" exists for "search-maps-store-test"
    And the seller of "search-maps-store-test" has orders and delivery enabled
    Given a buyer user is logged in
    When the buyer goes to "search-maps-store-test" profile
    And the buyer adds "Pizza Delivery Test" to the cart
    And the buyer proceeds to checkout
    When the buyer fills customer name "Lucia Test"
    And the buyer selects "Delivery" delivery method
    When the buyer opens the delivery map modal
    And the buyer searches "https://maps.app.goo.gl/jyS4XdTsSY88LmAh7" in the delivery map
    And the buyer confirms the searched delivery location on the map
    Then the delivery location confirmed card is visible
    And the confirm order button is enabled

  Scenario: Road circuity factor increases delivery distance and fee above straight line
    Given a premium business in La Paz with location exists with name "Circuity Test Store Test" and slug "circuity-test-store-test"
    And a product "Lomo Montaña Test" exists for "circuity-test-store-test"
    And the seller of "circuity-test-store-test" has orders and delivery enabled
    Given a buyer user is logged in
    When the buyer goes to "circuity-test-store-test" profile
    And the buyer adds "Lomo Montaña Test" to the cart
    And the buyer proceeds to checkout
    When the buyer fills customer name "Mateo Test"
    And the buyer selects "Delivery" delivery method
    When the buyer opens the delivery map modal
    And the buyer searches "https://www.google.com/maps?q=-16.5108315,-68.1277939" in the delivery map
    And the buyer confirms the searched delivery location on the map
    Then the delivery distance is greater than straight line distance
    And the delivery fee reflects the urban circuity road factor

