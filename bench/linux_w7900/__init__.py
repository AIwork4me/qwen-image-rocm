"""Linux W7900 optimization laboratory for qwen-image-rocm.

Adds a Linux ROCm (Radeon PRO W7900, gfx1100) workstream on top of the
existing Windows benchmark framework, reusing ``bench.core`` protocol
planning, ``bench.comfyui_client`` workflow building and the frozen
prompt set. All Linux results land under ``bench/results/linux-w7900/``.

Experiment IDs follow the lab methodology (not the historical ``pN-``
naming): B0 baseline, L1 less-computation, F1/F2 faster-computation,
LF* combined, H1/H2 heterogeneous, BEST final.
"""
