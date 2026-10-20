Feature: Short Google Maps URL Resolution
  As a business owner
  I want to paste a short Google Maps URL in the location field
  So that the system extracts coordinates automatically

  Scenario: Backend resolves a short Google Maps URL and returns parseable coordinates
    Given the backend API is available
    When a resolve-url request is sent with a short Google Maps URL
    Then the response contains a valid URL with coordinates

  Scenario: UI detects coordinates after pasting a short Google Maps URL
    Given a seller user logged in with a business "Ubicacion URL Test"
    And the user navigates to edit their business
    When the user pastes a short Google Maps URL in the location field
    And the URL resolution completes
    Then the UI shows the success indicator for detected location
    And the warning message about undetected coordinates is not visible

  Scenario: UI shows warning when pasting an invalid URL in location field
    Given a seller user logged in with a business "Ubicacion Invalida Test"
    And the user navigates to edit their business
    When the user pastes an invalid URL in the location field
    And waits for any resolution attempt to finish
    Then the UI shows the warning about undetected coordinates
