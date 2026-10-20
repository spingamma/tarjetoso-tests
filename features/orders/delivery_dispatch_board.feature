Feature: Multi-Business Delivery Dispatch Board and Live Tracking
  As an authorized delivery agent
  I want to view available paid orders sorted by distance to the restaurant
  And manage active deliveries with live GPS tracking and settlement reports

  Scenario: Delivery role navigation replacement and distance tiering
    Given a delivery agent user logged into the application
    And an available order located 2.0 km from the delivery agent
    And another available order located 10.0 km from the delivery agent
    When the delivery agent visits the home navigation bar
    Then the navigation menu should display the delivery motorcycle button instead of my businesses
    When the delivery agent navigates to the delivery dispatch board
    Then the close order card should display a green badge and an active accept button
    And the far order card should display a red badge and a disabled button with distance warning

  Scenario: Atomic order claiming and delivery modal dismissal vector
    Given a delivery agent user logged into the application
    And an available order ready for dispatch
    When the delivery agent clicks accept order
    Then the order should vanish from available orders
    And the view should switch to active deliveries showing the order in transit
    When the delivery agent opens the deliver confirmation modal
    And the delivery agent clicks not yet to dismiss the modal
    Then the confirmation modal should close and the order should remain in transit
    When the delivery agent opens the deliver confirmation modal
    And the delivery agent confirms order delivered
    Then the order should transition to completed with a success notification

  Scenario: Delivery earnings settlement report with date range filtering
    Given a delivery agent with delivered orders completed today
    When the delivery agent switches to the completed deliveries subtab
    And filters the history by today date range
    Then the settlement summary card should display the total completed runs and accumulated earnings
