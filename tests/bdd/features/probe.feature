Feature: Probe macros
  The Klipper set of macros to interface with the probe.

  Background:
    Given a probe

  Scenario: Probing the bed
    Given the probe measures:
      | 2 |
    When I run the PROBE macro
    Then it should log "Result is z=2"

  Scenario: Checking probe accuracy samples parameter
    Given the probe measures:
      | 10 |
    And macro parameters:
      | SAMPLES | 2 |
    When I run the PROBE_ACCURACY macro
    Then it should probe 2 times

  Scenario: Checking probe accuracy
    Given the probe measures:
      | 10 | 20 |
    When I run the PROBE_ACCURACY macro
    Then it should log "probe accuracy results"
    * it should log "minimum 10"
    * it should log "maximum 20"
    * it should log "range 10"
    * it should log "median 15"
    * it should log "standard deviation 5"

  Scenario: Query probe is triggered
    Given the probe is triggered
    When I run the QUERY_PROBE macro
    Then it should log "probe: TRIGGERED"

  Scenario: Query probe is not triggered
    Given the probe is not triggered
    When I run the QUERY_PROBE macro
    Then it should log "probe: open"
