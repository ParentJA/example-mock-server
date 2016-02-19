Feature: Mock server

  Scenario: Hitting a URL on the mock server

    When I send a mock request
    Then I get a mock response