"""HIP/ROCm smoke test for the Phase 1 environment.

Prints torch/HIP/device info and exits nonzero if the AMD ROCm stack is not
usable: torch.cuda unavailable, or the active device is not gfx1100.
Any failure here is a ROCm-on-Windows finding — log it in docs/issues/.
"""

import sys

EXPECTED_ARCH = "gfx1100"


def check(torch) -> list[str]:
    problems = []
    if not torch.cuda.is_available():
        problems.append("torch.cuda.is_available() is False (no usable HIP runtime)")
        return problems
    props = torch.cuda.get_device_properties(0)
    arch = getattr(props, "gcnArchName", "")
    arch = arch.split(":")[0]
    if EXPECTED_ARCH not in arch:
        problems.append(f"device arch is '{arch}', expected '{EXPECTED_ARCH}'")
    return problems


def main() -> None:
    import torch

    print(f"torch={torch.__version__}")
    print(f"hip={torch.version.hip}")
    print(f"cuda_available={torch.cuda.is_available()}")
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        print(f"device={props.name}")
        print(f"gcn_arch={getattr(props, 'gcnArchName', 'n/a')}")
        x = torch.randn(512, 512, device="cuda")
        y = x @ x
        torch.cuda.synchronize()
        print(f"matmul_ok={float(y.sum()) == float(y.sum())}")
    problems = check(torch)
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
