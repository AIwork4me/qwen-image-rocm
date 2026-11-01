name: Feature request
description: Propose an experiment, lever, or tooling improvement
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes:
      label: What problem would this solve?
      description: Not the feature itself — the user-facing problem
    validations:
      required: true
  - type: textarea
    id: idea
    attributes:
      label: Your proposal
    validations:
      required: true
  - type: textarea
    id: evidence
    attributes:
      label: Prior evidence / links
      description: Issues, upstream PRs, papers, or your own measurements
  - type: dropdown
    id: cost
    attributes:
      label: Who can validate it?
      options:
        - Needs the tested RX 7900 XTX rig
        - Anyone with any Radeon + this repo
        - CPU-only (tests/docs/tooling)
