Feature: Independent Catalog Management
  As a business owner
  I want to edit and save my catalog directly from my digital card
  So that I can manage products and inventory independently from business details

  Scenario: Owner opens catalog editor from public profile and saves changes independently
    Given an owner user is logged in with a premium business "Catalogo Independiente Test" and slug "catalogo-indep-test"
    When the owner visits their business profile "catalogo-indep-test"
    And clicks the "Edita tu menú aquí" button
    Then the catalog edit modal is displayed with independent save action
    When the owner updates catalog settings and clicks save catalog
    Then the catalog modal closes and the public catalog reflects the updated state

  Scenario: Cancelling product creation inside catalog editor keeps the catalog modal open
    Given an owner user is logged in with a premium business "Catalogo Cancel Test" and slug "catalogo-cancel-test"
    When the owner visits their business profile "catalogo-cancel-test"
    And clicks the "Edita tu menú aquí" button
    Then the catalog edit modal is displayed with independent save action
    When the owner clicks the add product button
    Then the product form modal is displayed
    When the owner clicks cancel on the product form
    Then the product form modal is closed
    And the catalog edit modal remains open and functional

