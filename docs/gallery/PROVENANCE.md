# Gallery provenance

Every image is an unedited output of a recorded, schema-validated run
(records: `bench/results/<run>/`, protocol: `bench/prompts.json`).
Do not crop/recolor these files — they are evidence.

- `fast-1024-p1-zh-scene-seed42.png` — Fast profile (turbo int8 DiT + int8 TE + ck + nosmart), 1024², 8 steps, seed 42, p1-zh-scene — run 2026-11-01-r1-triple (r0 measure)
- `fast-1024-p2-en-scene-seed42.png` — Fast profile, 1024², 8 steps, seed 42, p2-en-scene — run 2026-11-01-r1-triple (r0 measure)
- `fast-1024-p3-poster-seed42.png` — Fast profile, 1024², 8 steps, seed 42, p3-poster-text (Chinese typography) — run 2026-11-01-r1-triple (r0 measure)
- `fast-2048-p2-en-scene-seed42.png` — Fast profile, 2048² native, 8 steps, seed 42, p2-en-scene — run 2026-11-01-r2-2048fast (r0 measure)
- `fast-2048-p3-poster-seed42.png` — Fast profile, 2048² native, 8 steps, seed 42, p3-poster-text (Chinese typography at native resolution) — run 2026-11-01-r3-2048matrix (r0 measure, bounded-matrix session)
