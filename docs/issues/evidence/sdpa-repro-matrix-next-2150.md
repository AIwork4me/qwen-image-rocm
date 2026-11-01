# SDPA repro matrix

- created: 2026-11-01T13:42:20+08:00
- torch: 2.15.0+rocm10.3.0a20261031 (git dde42be134ce10ad181f0ae4bf8666b1c875b775)
- HIP: 7.18.26434 | arch: gfx1100 | device: AMD Radeon RX 7900 XTX
- aotriton.images: ['amd-gfx110x'] sha1=['c11b5b886a10a00f925f74133d38b3505e67ccd9']; aotriton_v2.dll v3-symbols=True

## kv_heads=8 (GQA, Qwen3-VL text encoder)

| seq | mask | causal | flash | mem_efficient | math | cudnn |
|---|---|---|---|---|---|---|
| 64 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.34ms | ❌ No available kernel. Aborting execution. |
| 64 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.32ms | ❌ No available kernel. Aborting execution. |
| 64 | none | False | ✅ 0.07ms | ❌ No available kernel. Aborting execution. | ✅ 0.29ms | ❌ No available kernel. Aborting execution. |
| 64 | none | True | ✅ 0.08ms | ❌ No available kernel. Aborting execution. | ✅ 0.34ms | ❌ No available kernel. Aborting execution. |
| 120 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.42ms | ❌ No available kernel. Aborting execution. |
| 120 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.38ms | ❌ No available kernel. Aborting execution. |
| 120 | none | False | ✅ 0.17ms | ❌ No available kernel. Aborting execution. | ✅ 0.38ms | ❌ No available kernel. Aborting execution. |
| 120 | none | True | ✅ 0.10ms | ❌ No available kernel. Aborting execution. | ✅ 0.52ms | ❌ No available kernel. Aborting execution. |
| 256 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.48ms | ❌ No available kernel. Aborting execution. |
| 256 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.44ms | ❌ No available kernel. Aborting execution. |
| 256 | none | False | ✅ 0.18ms | ❌ No available kernel. Aborting execution. | ✅ 0.57ms | ❌ No available kernel. Aborting execution. |
| 256 | none | True | ✅ 0.09ms | ❌ No available kernel. Aborting execution. | ✅ 0.51ms | ❌ No available kernel. Aborting execution. |
| 1024 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 6.06ms | ❌ No available kernel. Aborting execution. |
| 1024 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 6.08ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | False | ✅ 0.55ms | ❌ No available kernel. Aborting execution. | ✅ 5.54ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | True | ✅ 0.40ms | ❌ No available kernel. Aborting execution. | ✅ 6.06ms | ❌ No available kernel. Aborting execution. |
| 4096 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 54.89ms | ❌ No available kernel. Aborting execution. |
| 4096 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 54.55ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | False | ✅ 7.77ms | ❌ No available kernel. Aborting execution. | ✅ 49.28ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | True | ✅ 2.56ms | ❌ No available kernel. Aborting execution. | ✅ 57.55ms | ❌ No available kernel. Aborting execution. |
| 16384 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | False | ✅ 121.42ms | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | True | ✅ 40.13ms | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |

## kv_heads=32 (full MHA, DiT)

| seq | mask | causal | flash | mem_efficient | math | cudnn |
|---|---|---|---|---|---|---|
| 64 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 0.10ms | ✅ 0.31ms | ❌ No available kernel. Aborting execution. |
| 64 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 0.08ms | ✅ 0.28ms | ❌ No available kernel. Aborting execution. |
| 64 | none | False | ✅ 0.07ms | ✅ 0.08ms | ✅ 0.34ms | ❌ No available kernel. Aborting execution. |
| 64 | none | True | ✅ 0.10ms | ✅ 0.08ms | ✅ 0.32ms | ❌ No available kernel. Aborting execution. |
| 120 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 0.11ms | ✅ 0.39ms | ❌ No available kernel. Aborting execution. |
| 120 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 0.09ms | ✅ 0.36ms | ❌ No available kernel. Aborting execution. |
| 120 | none | False | ✅ 0.20ms | ✅ 0.12ms | ✅ 0.35ms | ❌ No available kernel. Aborting execution. |
| 120 | none | True | ✅ 0.10ms | ✅ 0.10ms | ✅ 0.42ms | ❌ No available kernel. Aborting execution. |
| 256 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 0.22ms | ✅ 0.82ms | ❌ No available kernel. Aborting execution. |
| 256 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 0.19ms | ✅ 0.79ms | ❌ No available kernel. Aborting execution. |
| 256 | none | False | ✅ 0.19ms | ✅ 0.20ms | ✅ 0.91ms | ❌ No available kernel. Aborting execution. |
| 256 | none | True | ✅ 0.16ms | ✅ 0.16ms | ✅ 0.85ms | ❌ No available kernel. Aborting execution. |
| 1024 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 0.66ms | ✅ 5.92ms | ❌ No available kernel. Aborting execution. |
| 1024 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 0.67ms | ✅ 5.92ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | False | ✅ 0.52ms | ✅ 0.51ms | ✅ 5.58ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | True | ✅ 0.33ms | ✅ 0.32ms | ✅ 6.12ms | ❌ No available kernel. Aborting execution. |
| 4096 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 7.59ms | ✅ 55.06ms | ❌ No available kernel. Aborting execution. |
| 4096 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 7.52ms | ✅ 54.47ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | False | ✅ 7.58ms | ✅ 7.65ms | ✅ 49.71ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | True | ✅ 3.69ms | ✅ 2.77ms | ✅ 57.19ms | ❌ No available kernel. Aborting execution. |
| 16384 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 121.24ms | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 120.69ms | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | False | ✅ 120.91ms | ✅ 121.44ms | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | True | ✅ 39.34ms | ✅ 37.20ms | ❌ OOM | ❌ No available kernel. Aborting execution. |

## per-backend totals

| backend | PASS | FAIL | OOM |
|---|---|---|---|
| flash | 24 | 24 | 0 |
| mem_efficient | 24 | 24 | 0 |
| math | 40 | 0 | 8 |
| cudnn | 0 | 48 | 0 |
