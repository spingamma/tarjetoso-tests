Feature: Business Creation Flow
  As a verified user
  I want to create a business from the main panel
  So that it can be listed in the Tarjetoso directory

  Scenario: Creating a business without a seller code results in pending status
    Given a new user registered and logged in with "StandardUserTest"
    And the user is on the create business page
    When the user fills the business form with "Negocio Sin Vendedor Test"
    And leaves the seller code field empty
    And submits the form
    Then the business is created with pending status
    And the business is not visible in the public directory

  Scenario: Creating a business with a valid seller code results in active status and premium plan
    Given a seller user exists in the backend with name "Seller User Test" and code generated from their email and phone
    And a new user registered and logged in with "ReferredUserTest"
    And the user is on the create business page
    When the user fills the business form with "Negocio Referido Test"
    And provides the valid seller code in the form
    And submits the form
    Then the business is created with active status
    And the business is assigned the premium plan
    And the business is linked to the seller

  Scenario: Creating a business as a seller automatically links to them and gives active status and premium plan
    Given a seller user registered and logged in with "Seller Owner Test"
    And the user is on the create business page
    When the user fills the business form with "Negocio Propio Test"
    And leaves the seller code field empty
    And submits the form
    Then the business is created with active status
    And the business is assigned the premium plan
    And the business is linked to the seller
