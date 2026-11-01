"""Quickstart profiles: the only two user-facing generation configs.

Fast and Quality map to frozen experiment manifests (single source of truth:
``bench/experiments/``) plus the exact weight files each mode needs, so the
one-command path cannot drift from what was actually measured and quality-
gated. PowerShell glue (``quickstart.ps1``) consumes this module through its
small CLI; tests pin the mapping (tests/test_quickstart.py).

Weight integrity (release-review P0-4): every file must match a PINNED
sha256 below — pre-existing files included; exact size alone is NOT enough.
The pins were recorded at upstream revision ``WEIGHTS_REVISION`` and
cross-checked two ways at pin time (2026-11-01): the revision's git-LFS
pointers, and full sha256 of the local working copies that produced every
committed benchmark in this repo. See ``DIGEST_PROVENANCE``.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow -I runs

from bench.experiments import load_manifest  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
WEIGHTS_ROOT = REPO / "weights" / "comfyui-split"
STAMP_PATH = WEIGHTS_ROOT / ".digest_cache.json"

# Frozen upstream revision of Comfy-Org/Qwen-Image-2.1 all downloads pin to
# (immutable resolve/<rev>/ URLs; never a moving `main`).
WEIGHTS_REVISION = "aacf31a6d48e707f352ecba714cee0680da3479b"

# OFFICIAL source is the huggingface.co repo; hf-mirror.com is the default
# TRANSPORT on networks where huggingface.co is unreachable. Because
# integrity is anchored to the pinned digests below (not to whichever
# transport served the bytes), a mirror cannot silently corrupt a file.
OFFICIAL_URL_BASE = "https://huggingface.co/Comfy-Org/Qwen-Image-2.1"
DEFAULT_MIRROR_BASE = "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1"

DIGEST_PROVENANCE = (
    "sha256 pins recorded 2026-11-01 at upstream revision "
    f"{WEIGHTS_REVISION}: git-LFS pointer oids fetched via hf-mirror.com "
    "(huggingface.co unreachable from the recording network) AND "
    "independently matched by full-file sha256 of the local working copies "
    "that produced every committed benchmark in this repo. The trust anchor "
    "for verification is THIS in-repo table, not any live endpoint."
)

# rel path -> (exact byte size, pinned sha256)
WEIGHTS: dict[str, tuple[int, str]] = {
    "diffusion_models/qwen_image_2.1_bf16.safetensors": (
        14_230_280_616,
        "89f4158d066cc33906a199fca85634f766892dd78f49b6698dabf187ac86c4bc"),
    "diffusion_models/qwen_image_2.1_int8_convrot.safetensors": (
        7_256_783_064,
        "cb74113cb03faecd79611b01fd7fd642f0aa60d6f0b95086abee214d75eaa57d"),
    "diffusion_models/qwen_image_2.1_turbo_bf16.safetensors": (
        14_230_280_616,
        "8b74237a7f505773e2c66726fa696444b4c704585c93a347cff9044937f7914a"),
    "diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors": (
        7_256_787_829,
        "8144a0182964aa8403ad6dbc011db837304167d235161b9aabaa8532e967314c"),
    "text_encoders/qwen3vl_8b_bf16.safetensors": (
        17_534_334_616,
        "68bdc82bc1b66851162ae656225e7e2068166b603db19bd5d5a3b90eb12669a9"),
    "text_encoders/qwen3vl_8b_int8_convrot.safetensors": (
        9_350_798_360,
        "8bfd0f6e12abf2d2d697ecc888e5e90b0d6741d6708f05799f53afa560452e8f"),
    "text_encoders/qwen3vl_8b_w4a8.safetensors": (
        6_312_105_364,
        "7754425e55e7bea2bfde4dde59a4cc236cb44e5ee9c215ea66ef8d47012824eb"),
    "vae/qwen_image_2.1_vae_bf16.safetensors": (
        675_509_688,
        "bb21f7473051e1ac368515dd3f2e15cd44d7a11748ee8823e1ddca3e4876b7c9"),
}

MODES = {
    # Fast = E8 config (turbo int8 DiT + BF16 TE + ck), owner-approved
    # (A1 无感; #5 verdict 2026-11-01). The int8-TE "production triple"
    # variant measured in bench/results/2026-11-01-r1-triple/ was REJECTED
    # as the Fast default by the same verdict: p1 略降, p3 typography
    # 不可接受 (LPIPS 0.0137 did not predict it — human gate is binding).
    "fast": {
        "manifest": "p4-qs-fast-1024x1024",
        "resolutions": (1024, 2048),
        "weights": (
            "diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors",
            "text_encoders/qwen3vl_8b_bf16.safetensors",
            "vae/qwen_image_2.1_vae_bf16.safetensors",
        ),
    },
    # Bit-identical to the phase-3 bf16 baseline (p3-vram-nosmart: LPIPS
    # 0.0000 vs control) with the measured --disable-smart-memory gain.
    "quality": {
        "manifest": "p4-qs-quality-1024x1024",
        "resolutions": (1024,),
        "weights": (
            "diffusion_models/qwen_image_2.1_bf16.safetensors",
            "text_encoders/qwen3vl_8b_bf16.safetensors",
            "vae/qwen_image_2.1_vae_bf16.safetensors",
        ),
    },
}


def config_for(mode: str) -> dict:
    """Mode -> {manifest fields..., resolutions, weights}; ValueError on typo."""
    try:
        cfg = MODES[mode.lower()]
    except KeyError:
        raise ValueError(
            f"unknown mode {mode!r} (available: {', '.join(sorted(MODES))})"
        ) from None
    out = dict(load_manifest(cfg["manifest"]))
    out["resolutions"] = cfg["resolutions"]
    out["weights"] = cfg["weights"]
    out["revision"] = WEIGHTS_REVISION
    return out


def check_resolution(mode: str, resolution: int) -> None:
    cfg = MODES[mode.lower()]
    if resolution not in cfg["resolutions"]:
        if mode.lower() == "quality" and resolution == 2048:
            raise ValueError(
                "Quality mode at 2048 is not supported: bf16 VAE decode "
                "allocates a 20.25 GB conv tensor and OOMs on 24 GB cards "
                "(docs/issues/evidence/sdpa-7140-2048-vae-oom.log). Use "
                "-Mode Fast for 2048."
            )
        raise ValueError(
            f"resolution {resolution} not validated for mode {mode!r} "
            f"(tested: {', '.join(str(r) for r in cfg['resolutions'])})"
        )


def weights_state(mode: str) -> list[dict]:
    """Per-file state for the mode's weights: present/absent/truncated.

    'present' means exact size match ONLY — quickstart.ps1 always follows
    this with verify-weight (sha256 vs the pinned digest) before use.
    """
    states = []
    for rel in MODES[mode.lower()]["weights"]:
        path = WEIGHTS_ROOT / rel
        expected = WEIGHTS[rel][0]
        if not path.exists():
            state = "absent"
        elif path.stat().st_size != expected:
            state = "truncated"
        else:
            state = "present"
        states.append({"rel": rel, "path": str(path), "expected_bytes": expected,
                       "state": state, "revision": WEIGHTS_REVISION})
    return states


def _load_stamps() -> dict:
    try:
        return json.loads(STAMP_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 23), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_weight(rel: str, update_stamp: bool = True) -> dict:
    """Trusted integrity check: local file sha256 vs the PINNED digest.

    Runs for every file on every invocation (P0-4: size-only shortcuts are
    a bypass). A stamp cache (size+mtime keyed) makes repeat checks fast,
    but any change to the file re-hashes. ``ok=false`` is reported, never
    raised, so callers decide policy; result carries which trust anchor
    was used.
    """
    if rel not in WEIGHTS:
        raise ValueError(f"unknown weight {rel!r}")
    path = WEIGHTS_ROOT / rel
    expected_size, pinned = WEIGHTS[rel]
    if not path.exists():
        return {"rel": rel, "ok": False, "reason": "absent",
                "expected_sha256": pinned}
    st = path.stat()
    if st.st_size != expected_size:
        return {"rel": rel, "ok": False, "reason": "size-mismatch",
                "local_size": st.st_size, "expected_size": expected_size,
                "expected_sha256": pinned}
    stamps = _load_stamps()
    entry = stamps.get(rel)
    if (entry and entry.get("size") == st.st_size
            and entry.get("mtime_ns") == st.st_mtime_ns
            and entry.get("sha256") == pinned):
        return {"rel": rel, "ok": True, "reason": "stamp-cache-hit",
                "sha256": pinned, "anchor": "pinned-digest+cache"}
    local = _sha256(path)
    ok = local == pinned
    if ok and update_stamp:
        stamps[rel] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns,
                       "sha256": pinned, "verified_at": int(time.time())}
        try:
            STAMP_PATH.write_text(json.dumps(stamps, indent=2), encoding="utf-8")
        except OSError:
            pass  # cache is best-effort; verification result stands
    return {"rel": rel, "ok": ok,
            "reason": "hashed" if ok else "digest-mismatch",
            "local_sha256": local, "expected_sha256": pinned,
            "anchor": "pinned-digest"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["config", "weights-state", "verify-weight",
                                        "digests"])
    ap.add_argument("--mode", default=None, help="fast | quality")
    ap.add_argument("--rel", default=None, help="weight path relative to weights root")
    ns = ap.parse_args(sys.argv[1:])

    if ns.command == "config":
        print(json.dumps(config_for(ns.mode or "fast"), indent=2))
    elif ns.command == "weights-state":
        print(json.dumps(weights_state(ns.mode or "fast"), indent=2))
    elif ns.command == "digests":
        print(json.dumps({"revision": WEIGHTS_REVISION,
                          "official": OFFICIAL_URL_BASE,
                          "default_mirror": DEFAULT_MIRROR_BASE,
                          "provenance": DIGEST_PROVENANCE,
                          "weights": {k: {"size": v[0], "sha256": v[1]}
                                      for k, v in WEIGHTS.items()}}, indent=2))
    else:
        print(json.dumps(verify_weight(ns.rel), indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
