"""Command-line interface for the Linux W7900 lab.

    python -m bench.linux_w7900 doctor            # environment + stack preflight
    python -m bench.linux_w7900 baseline          # run the frozen B0 baseline
    python -m bench.linux_w7900 profile           # pipeline + GPU kernel profiling
    python -m bench.linux_w7900 run --experiment L1
    python -m bench.linux_w7900 report            # aggregate all results

Every stage writes explicit PASS/FAIL/BLOCKED status and evidence paths.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import lab_env, manifests


def cmd_doctor(args) -> int:
    from . import doctor
    return doctor.run(quick=args.quick)


def cmd_baseline(args) -> int:
    from . import runner
    res = runner.run_experiment("B0", date=args.date, port=args.port,
                                smoke=args.smoke)
    print(f"BASELINE_DONE {res}")
    return 0


def cmd_profile(args) -> int:
    from . import profile
    return profile.run(layers=args.layers, date=args.date, port=args.port)


def cmd_run(args) -> int:
    from . import runner
    if args.experiment == "H1":
        from . import pipeline
        pipeline.run_h1(date=args.date)
        return 0
    if args.experiment == "H2":
        from . import pipeline
        pipeline.run_h2(date=args.date, port=args.port)
        return 0
    res = runner.run_experiment(args.experiment, date=args.date, port=args.port,
                                only_prompt=args.only_prompt, smoke=args.smoke)
    print(f"RUN_DONE {res}")
    return 0


def cmd_report(args) -> int:
    from . import report
    out = report.build(write=True)
    print(json.dumps({k: v for k, v in out.items() if k != "per_experiment"} |
                     {"per_experiment_count": len(out.get("per_experiment", []))},
                     indent=2, default=str))
    return 0


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m bench.linux_w7900",
                                 description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor", help="environment + stack preflight")
    p.add_argument("--quick", action="store_true", help="skip slow GPU probes")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("baseline", help="run the frozen B0 baseline")
    p.add_argument("--date", default=None)
    p.add_argument("--port", type=int, default=8188)
    p.add_argument("--smoke", action="store_true")
    p.set_defaults(func=cmd_baseline)

    p = sub.add_parser("profile", help="pipeline + GPU kernel profiling (Phase 2)")
    p.add_argument("--layers", default="pipeline,kernel")
    p.add_argument("--date", default=None)
    p.add_argument("--port", type=int, default=8188)
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("run", help="run one experiment manifest")
    p.add_argument("--experiment", required=True,
                   help=f"one of {manifests.KNOWN_IDS}")
    p.add_argument("--date", default=None)
    p.add_argument("--port", type=int, default=8188)
    p.add_argument("--only-prompt", default=None)
    p.add_argument("--smoke", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", help="aggregate results into report artifacts")
    p.set_defaults(func=cmd_report)

    ns = ap.parse_args(argv)
    rc = ns.func(ns)
    sys.exit(rc)


if __name__ == "__main__":
    main()
