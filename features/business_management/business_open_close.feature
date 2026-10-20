Feature: Business Open Close Toggle and Order WhatsApp Visibility
  As a business owner
  I want to toggle my business open or closed and manage order contacts
  So that customers see it greyed out when closed and WhatsApp contact is available only while active

  Scenario: Owner closes business and visitor sees grayscale profile with orders blocked
    Given a premium business exists with name "Toggle Biz Test" and slug "toggle-biz-test"
    And a product "Producto Toggle Test" exists for "toggle-biz-test"
    When the seller of "toggle-biz-test" logs in
    And the seller enables orders in catalog settings
    And the seller goes to "toggle-biz-test" profile
    Then the open close toggle switch is visible on the hero banner
    When the seller toggles the business to closed
    Then the hero banner shows the wooden "Cerrado" sign
    And the hero banner image has grayscale filter
    When a public visitor navigates to the public profile of "toggle-biz-test"
    Then the hero banner image has grayscale filter
    And the wooden "Cerrado" sign is visible
    And the checkout button is not available
    When the seller of "toggle-biz-test" logs in
    And the seller goes to "toggle-biz-test" profile
    And the seller toggles the business to open
    Then the wooden "Cerrado" sign is not visible
    And the hero banner image does not have grayscale filter

  Scenario: Owner toggles open close from My Businesses panel and directory reflects grayscale
    Given a premium business exists with name "Panel Toggle Test" and slug "panel-toggle-test"
    When the seller of "panel-toggle-test" logs in
    And the seller navigates to "Mis Negocios"
    Then the open close toggle for "panel-toggle-test" is visible in the list
    When the seller toggles "panel-toggle-test" to closed from the panel
    Then the toggle shows closed state for "panel-toggle-test"
    When a public visitor searches for "Panel Toggle Test" in the directory
    Then the business card for "panel-toggle-test" appears in grayscale with "Cerrado" badge
    When the seller of "panel-toggle-test" logs in
    And the seller navigates to "Mis Negocios"
    And the seller toggles "panel-toggle-test" to open from the panel
    Then the toggle shows open state for "panel-toggle-test"

  Scenario: WhatsApp button disappears from order card after delivery
    Given a premium business exists with name "WA Button Test" and slug "wa-button-test"
    And a product "Producto WA Test" exists for "wa-button-test"
    When the seller of "wa-button-test" logs in
    And the seller enables orders in catalog settings
    And an order with customer phone is created for "wa-button-test" via API
    And the seller navigates to their business orders
    Then the seller sees the order as "Pagado"
    And the WhatsApp button is visible on the order card
    When the seller marks the order as delivered
    Then the seller sees the order as "Entregado"
    And the WhatsApp button is not visible on the order card
