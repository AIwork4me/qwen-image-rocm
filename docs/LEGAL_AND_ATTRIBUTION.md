# Legal, licensing & attribution

**This project is an independent community benchmark by @AIwork4me. It is
not an official AMD, Alibaba, or Qwen project, and is not endorsed by them.**
No claim of official recommendation may be made in forks, forks' marketing,
or social posts derived from this repo.

## License boundaries

| Artifact | License | Where |
|---|---|---|
| This project's code (bench drivers, tools, scripts, tests) | MIT | [LICENSE](../LICENSE) |
| Benchmark data & reports (`bench/results/**`, `docs/benchmarks/**`, gallery provenance) | CC-BY-4.0 | [docs/DATA_LICENSE.md](DATA_LICENSE.md) |
| Qwen-Image-2.1 model weights (DiT / VAE) | Alibaba's Qwen license (Apache-2.0–based model license, see the model repo) — **not MIT, not CC-BY** | upstream `Qwen/Qwen-Image-2.1`, `Comfy-Org/Qwen-Image-2.1` |
| Qwen3-VL text encoder weights | Alibaba's Qwen3-VL license — **not MIT, not CC-BY** | upstream |
| ComfyUI | GPL-3.0 | upstream `Comfy-Org/ComfyUI` |
| LPIPS weights (AlexNet, torchvision) | their upstream licenses | auto-downloaded by the quality gate, never committed |

**You** are responsible for reading and accepting the model licenses before
downloading/using the weights (`quickstart.ps1` prints the source and
verifies hashes; it does not and cannot accept licenses for you).

## Redistribution rules this repo follows

1. **No model weights are ever committed** (`.gitignore` blocks `weights/`).
2. Downloads always come from the official `Qwen`/`Comfy-Org` repositories
   (HF or its mirrors via `HF_ENDPOINT`); mirrors are labeled explicitly in
   `docs/weights.md`, and third-party mirrors are never silently substituted.
3. Model SHA256s are only asserted from the download host's own LFS pointer
   (`bench/quickstart_config.py`) — never invented.
4. ComfyUI is cloned at a pinned commit at setup time; none of its code is
   copied into this repository. The `websocket_image_save.py` custom node
   present in historical logs came with the pinned ComfyUI checkout.
5. Gallery/social-preview images are unedited outputs of recorded runs
   (`docs/gallery/PROVENANCE.md`); CC-BY-4.0 with provenance intact.

## Trademarks

"AMD", "Radeon", "ROCm", "Adrenalin" are AMD trademarks; "Qwen" is an
Alibaba trademark. Used here descriptively (nominative fair use) to state
compatibility facts, never to imply affiliation.

## Privacy / sensitive-content audit of committed evidence

- Committed server logs contain the maintainer's local filesystem paths
  (`C:\Users\…\Desktop\image\…`). They are retained deliberately as
  historical evidence (read-only policy); they contain no credentials.
  New evidence batches are pattern-scanned for tokens/keys before commit
  (`ghp_|gho_|hf_…|api_key|password|authorization|secret`) — scan recorded
  in the release-audit commits.
- Run records contain no personal data beyond a machine profile (GPU/driver
  versions), which is the point of the evidence.
- If you fork and commit your own run logs, run the same scan; example:
  `grep -riEl 'ghp_|gho_|hf_[A-Za-z0-9]{20}|api[_-]?key|password|authorization:|secret' <dir>`
