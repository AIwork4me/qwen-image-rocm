name: Bug report
description: Something broke or produced a wrong result
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks! Text output over screenshots, please. Reports without an
        environment snapshot may be closed.
  - type: textarea
    id: what
    attributes:
      label: What happened?
      description: What did you run, what did you expect, what happened instead (paste full error text)
    validations:
      required: true
  - type: textarea
    id: env
    attributes:
      label: Environment snapshot
      description: |
        Run and paste the output (JSON) of:
        `python -I tools\snapshot_env.py` (any venv that has torch; on a broken install, say so and paste `python --version` + driver version)
    validations:
      required: true
  - type: input
    id: mode
    attributes:
      label: Entry point
      description: e.g. `.\quickstart.ps1 -Mode Fast`, `bench\run_variant.ps1 -Experiment …`, `.\reproduce.ps1 -Quick`
  - type: dropdown
    id: gpu
    attributes:
      label: GPU
      options:
        - RX 7900 XTX (tested reference)
        - Other gfx1100 Radeon (used -AllowUntestedGpu)
        - Other AMD Radeon
        - Not AMD / not applicable
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Minimal reproduction
      description: Exact commands, prompt id, resolution, seed
