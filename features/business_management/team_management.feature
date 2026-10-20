Feature: Team Management and Staff Operations
  As a business owner
  I want to search, manage, and configure permissions for sales collaborators
  So that staff members can handle orders while respecting plan and RBAC limits

  @smoke @e2e
  Scenario: Owner searches candidate and adds collaborators up to the maximum limit of 2
    Given a registered owner "Dueño Staff Test" with a premium business "Equipo Staff Test" and slug "equipo-staff"
    And registered users "Colaborador Uno Test" and "Colaborador Dos Test" exist in the system
    When the owner logs in and navigates to "Mis Negocios"
    Then the "Gestionar equipo" button is visible for "equipo-staff" in "Mis Negocios"
    When the owner clicks "Gestionar equipo" button for "equipo-staff"
    Then the team management modal opens with counter "0 / 2"
    When the owner searches for a non-existent candidate "usuario_inexistente_999@test.com"
    Then an error message "Usuario no encontrado" is displayed in the modal
    When the owner searches for their own email
    And the owner confirms adding the candidate to the team
    Then an error message "El dueño del negocio ya cuenta con todos los accesos" is displayed in the modal
    When the owner searches for "Colaborador Uno Test"
    Then the candidate preview card displays "Colaborador Uno Test"
    When the owner confirms adding the candidate to the team
    Then "Colaborador Uno Test" appears in the active staff list
    And the team counter updates to "1 / 2"
    When the owner searches and adds "Colaborador Dos Test" to the team
    Then "Colaborador Dos Test" appears in the active staff list
    And the team counter updates to "2 / 2"
    And the limit reached warning banner is visible
    And the search input is not visible
    When an unauthorized attempt via API is made to add a third collaborator
    Then the API rejects the addition with status 400 and limit reached message

  @e2e
  Scenario: Sub-modal dismissal vector and collaborator removal with quota release
    Given a registered owner "Dueño Descarte Test" with a premium business "Descarte Staff Test" and slug "descarte-staff"
    And the business already has two staff members "Colaborador Alpha Test" and "Colaborador Beta Test"
    When the owner logs in and navigates to "Mis Negocios"
    And the owner clicks "Gestionar equipo" button for "descarte-staff"
    Then the team management modal opens with counter "2 / 2"
    When the owner clicks the modal close button
    Then the team management modal is closed
    And the "Mis Negocios" panel remains visible and interactive
    When the owner clicks "Gestionar equipo" button for "descarte-staff"
    And the owner expands permissions for "Colaborador Alpha Test"
    Then granular permission toggles are visible for "Colaborador Alpha Test"
    When the owner removes "Colaborador Alpha Test" from the team
    Then "Colaborador Alpha Test" is no longer in the active staff list
    And the team counter updates to "1 / 2"
    And the search input is visible again
    And the staff member is deleted from the database

  @security @rbac
  Scenario: RBAC security enforcement for standard free businesses and non-owners
    Given a registered owner "Dueño Gratis Test" with a standard free business "Gratis Staff Test" and slug "gratis-staff"
    And a non-owner user "Cliente Visitante Test" exists
    When the free business owner logs in and navigates to "gratis-staff" profile
    Then the "Gestionar equipo" button is not visible
    When the free business owner attempts to add staff via API
    Then the API rejects with status 403 and premium required message
    When the non-owner user attempts to list staff via API
    Then the API rejects with status 403 and owner required message
    When a staff member attempts to delete another collaborator via API
    Then the API rejects with status 403 forbidden

  @e2e @search
  Scenario: Candidate search by contains matching name, username or phone with up to 2 closest results
    Given a registered owner "Dueño Busqueda Test" with a premium business "Busqueda Staff Test" and slug "busqueda-staff"
    And three registered candidates with unique search token exist in the system
    When the owner logs in and navigates to "Mis Negocios"
    And the owner clicks "Gestionar equipo" button for "busqueda-staff"
    Then the team management modal opens with counter "0 / 2"
    When the owner searches for candidate unique token
    Then exactly 2 candidate preview cards are displayed
    And both candidate preview cards match the unique token
    When the owner searches for third candidate unique token
    Then exactly 1 candidate preview cards are displayed
    When the owner confirms adding the third candidate to the team
    Then the third candidate appears in the active staff list
    And the team counter updates to "1 / 2"
    When the owner searches candidate via API for candidate unique token
    Then the API search returns at most 2 results ordered by closeness
