Feature: Order Push Notifications
  As a Business Owner
  I want order creation to remain silent without push notifications
  So that I only receive push notifications when a payment is submitted

  Scenario: Business owner receives no push notification when a customer places an order
    Given a seller user registered and logged in with "Owner Notif Test"
    And the owner has enabled push notifications
    And a customer Test is browsing the owner's business
    When the customer places a new order
    Then the order is created in pending payment status without sending push notification

  Scenario: Pure business owner receives no push notification when an admin places an order
    Given a standard business owner registered and logged in with "Pure Owner Test"
    And the owner has enabled push notifications
    And an admin buyer Test is browsing the owner's business
    When the customer places a new order
    Then the order is created in pending payment status without sending push notification

  Scenario: Owner disables notifications and stops receiving them
    Given a seller user registered and logged in with "Owner OptOut Test"
    And the owner has enabled push notifications
    When the owner clicks the notifications toggle to disable
    And a customer Test is browsing the owner's business
    And the customer places a new order
    Then the business owner does NOT receive a push notification

  Scenario: Order placement succeeds when owner has no push subscription
    Given a standard business owner registered and logged in with "NoSub Owner Test"
    And a customer Test is browsing the owner's business
    When the customer places a new order
    Then the order is placed and push dispatch is skipped without error
