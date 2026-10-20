Feature: Role-Based Access Control (RBAC) Menus
  In order to ensure platform security and proper user experience
  As a system administrator
  I want to verify that different user roles see only their authorized menus and tabs

  Scenario: A normal client cannot access admin or seller menus
    Given a normal client user "Cliente Comun Test" is logged in
    When the user opens the user menu
    Then the user should not see the admin or seller panel buttons
    
  Scenario: A seller can access the seller panel but not full admin
    Given a seller user "Vendedor Limitado Test" is logged in
    When the user opens the user menu
    Then the user should see the "Panel Ventas" button
    When the user clicks the "Panel Ventas" button
    Then the user should see seller specific tabs
    And the user should not see full admin tabs

  Scenario: An administrator can access the full admin panel
    Given an admin user "Super Admin Test" is logged in
    When the user opens the user menu
    Then the user should see the "Panel Admin" button
    When the user clicks the "Panel Admin" button
    Then the user should see full admin tabs

  Scenario: A visitor on a public profile cannot see owner management controls
    Given a premium business exists with name "Card RBAC Test" and slug "card-rbac-test"
    When an anonymous visitor goes to "card-rbac-test" profile
    Then the visitor should not see the edit profile button or edit catalog button

