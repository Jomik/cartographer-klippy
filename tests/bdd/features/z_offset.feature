Feature: Adjust z-offset

  Rule: Apply z-offset to scan if touch is not ready

    Example: Touch not ready
      Given a probe
      When I run the Z_OFFSET_APPLY_PROBE macro
      Then it should set z-offset on the scan model

    Example: Scan and touch ready
      Given a probe
      And the probe has touch ready
      When I run the Z_OFFSET_APPLY_PROBE macro
      Then it should not set z-offset on the scan model

  Rule: Apply z-offset to touch if touch is ready

    Example: Touch ready
      Given a probe
      And the probe has touch ready
      When I run the Z_OFFSET_APPLY_PROBE macro
      Then it should set z-offset on the touch model

  Rule: Apply offset from baby stepping

    Example: Scan - Nozzle raised 0.4mm
      Given a probe
      And the probe's current z-offset is 2.0
      And I have baby stepped the nozzle 0.4mm up
      When I run the Z_OFFSET_APPLY_PROBE macro
      Then it should set scan z-offset to 1.6

    Example: Scan - Nozzle lowered 0.4mm
      Given a probe
      And the probe's current z-offset is 2.0
      And I have baby stepped the nozzle 0.4mm down
      When I run the Z_OFFSET_APPLY_PROBE macro
      Then it should set scan z-offset to 2.4

    Example: Touch - Nozzle raised 0.4mm
      Given a probe
      And the probe has touch ready
      And the probe's current z-offset is 0.0
      And I have baby stepped the nozzle 0.4mm up
      When I run the Z_OFFSET_APPLY_PROBE macro
      Then it should set touch z-offset to -0.4
