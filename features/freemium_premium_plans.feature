Feature: Freemium vs Premium Business Plans
  As the platform operator and store owner
  I want freemium and premium plan rules to be enforced across the public catalog, directory, and owner dashboard
  So that free businesses get visibility with limits and premium businesses enjoy unrestricted features

  Scenario: Free plan business has a 3-product limit for visitors but full access for owner
    Given a free tier business exists with name "Comercio Free Test" and slug "comercio-free-test" with 5 products
    When a public visitor navigates to the public profile of "comercio-free-test"
    Then the public visitor sees exactly 3 products in the catalog
    When the owner of "comercio-free-test" navigates to "Mis Negocios"
    Then the owner sees the business listed with the "Plan Gratuito" badge

  Scenario: Premium plan business shows full catalog to visitors and displays premium badge
    Given a premium tier business exists with name "Comercio Premium Test" and slug "comercio-premium-test" with 5 products
    When a public visitor navigates to the public profile of "comercio-premium-test"
    Then the public visitor sees exactly 5 products in the catalog
    When the owner of "comercio-premium-test" navigates to "Mis Negocios"
    Then the owner sees the business listed with the "Plan Premium" badge and expiration info

  Scenario: Expired business stays visible in directory but degrades to free tier limits
    Given an expired tier business exists with name "Comercio Expirado Test" and slug "comercio-expirado-test" with 4 products
    When a public visitor searches for "Comercio Expirado Test" in the directory
    Then the business "comercio-expirado-test" appears in the search results
    When a public visitor navigates to the public profile of "comercio-expirado-test"
    Then the public profile loads successfully without 403 error
    And the public visitor sees exactly 3 products in the catalog
    When the owner of "comercio-expirado-test" navigates to the orders panel of "comercio-expirado-test"
    Then the owner sees the premium lock screen
