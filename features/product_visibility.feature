Feature: Product Catalog Visibility Management
  As a business owner
  I want to hide and unhide products from my catalog using the visibility toggle
  So that customers only see available products while I retain my hidden items

  Scenario: Owner toggles product visibility to hide and unhide it from catalog
    Given an owner user is logged in with a business "Visib Test" and slug "visib-prod-test" having product "Prod Test"
    When the owner visits their business profile "visib-prod-test"
    Then the product card is displayed in the catalog with a visible toggle icon
    When the owner clicks the visibility toggle on product "Prod Test"
    Then the product card displays the hidden badge and dimmed status for the owner
    And the owner API endpoint confirms the product has is_visible false
    And the public API endpoint returns 0 products for visitors
    And an anonymous visitor viewing profile "visib-prod-test" does not see the product in the catalog
    When the owner clicks the visibility toggle again on product "Prod Test"
    Then the product card removes the hidden badge and restores active status
    And the owner API endpoint confirms the product has is_visible true
    And the public API endpoint returns 1 product for visitors
    And an anonymous visitor viewing profile "visib-prod-test" sees the product in the catalog
