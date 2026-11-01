name: GPU compatibility report
description: How this runs on Radeon hardware we haven't tested
labels: ["gpu-compat", "data"]
body:
  - type: markdown
    attributes:
      value: |
        We publish numbers for the RX 7900 XTX only. Reports from other
        cards feed the community support matrix — thank you!
  - type: input
    id: gpu
    attributes:
      label: GPU (exact model + VRAM)
    validations:
      required: true
  - type: input
    id: driver
    attributes:
      label: Adrenalin driver version
    validations:
      required: true
  - type: input
    id: os
    attributes:
      label: Windows version (winver)
    validations:
      required: true
  - type: textarea
    id: result
    attributes:
      label: Result
      description: |
        Which quickstart mode/resolution, did it run, timings if you have
        them (the quickstart prints cold/warm), any errors. If you can,
        attach the JSON records from `bench/results/quickstart-*/`.
    validations:
      required: true
  - type: checkboxes
    id: license
    attributes:
      label: Data license
      options:
        - label: I agree the timings/records I paste may be republished under CC-BY-4.0 with attribution to my username
          required: true
