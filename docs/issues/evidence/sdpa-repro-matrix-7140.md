# SDPA repro matrix

- created: 2026-11-01T13:12:43+08:00
- torch: 2.12.0+rocm7.14.0 (git 13eab2b3ef4e03999247f063bc2dde01c94e9eaa)
- HIP: 7.14.60850 | arch: gfx1100 | device: AMD Radeon RX 7900 XTX
- aotriton.images: ['amd-gfx11xx'] sha1=['dd1b68b604b5258ee7a9f7b66ad95e7a82c18065']; aotriton_v2.dll v3-symbols=True

## kv_heads=8 (GQA, Qwen3-VL text encoder)

| seq | mask | causal | flash | mem_efficient | math | cudnn |
|---|---|---|---|---|---|---|
| 64 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.29ms | ❌ No available kernel. Aborting execution. |
| 64 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.28ms | ❌ No available kernel. Aborting execution. |
| 64 | none | False | ✅ 0.09ms | ❌ No available kernel. Aborting execution. | ✅ 0.26ms | ❌ No available kernel. Aborting execution. |
| 64 | none | True | ✅ 0.11ms | ❌ No available kernel. Aborting execution. | ✅ 0.30ms | ❌ No available kernel. Aborting execution. |
| 120 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.41ms | ❌ No available kernel. Aborting execution. |
| 120 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.38ms | ❌ No available kernel. Aborting execution. |
| 120 | none | False | ✅ 0.11ms | ❌ No available kernel. Aborting execution. | ✅ 0.37ms | ❌ No available kernel. Aborting execution. |
| 120 | none | True | ✅ 0.17ms | ❌ No available kernel. Aborting execution. | ✅ 0.43ms | ❌ No available kernel. Aborting execution. |
| 256 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.50ms | ❌ No available kernel. Aborting execution. |
| 256 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 0.65ms | ❌ No available kernel. Aborting execution. |
| 256 | none | False | ✅ 0.11ms | ❌ No available kernel. Aborting execution. | ✅ 0.45ms | ❌ No available kernel. Aborting execution. |
| 256 | none | True | ✅ 0.17ms | ❌ No available kernel. Aborting execution. | ✅ 0.49ms | ❌ No available kernel. Aborting execution. |
| 1024 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 5.76ms | ❌ No available kernel. Aborting execution. |
| 1024 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 5.73ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | False | ✅ 0.91ms | ❌ No available kernel. Aborting execution. | ✅ 5.46ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | True | ✅ 0.97ms | ❌ No available kernel. Aborting execution. | ✅ 5.76ms | ❌ No available kernel. Aborting execution. |
| 4096 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 88.94ms | ❌ No available kernel. Aborting execution. |
| 4096 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ✅ 88.56ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | False | ✅ 11.19ms | ❌ No available kernel. Aborting execution. | ✅ 84.03ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | True | ✅ 8.52ms | ❌ No available kernel. Aborting execution. | ✅ 90.79ms | ❌ No available kernel. Aborting execution. |
| 16384 | bool4d | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | float_add | False | ❌ No available kernel. Aborting execution. | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | False | ✅ 163.60ms | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | True | ✅ 118.21ms | ❌ No available kernel. Aborting execution. | ❌ OOM | ❌ No available kernel. Aborting execution. |

## kv_heads=32 (full MHA, DiT)

| seq | mask | causal | flash | mem_efficient | math | cudnn |
|---|---|---|---|---|---|---|
| 64 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 0.12ms | ✅ 0.27ms | ❌ No available kernel. Aborting execution. |
| 64 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 0.21ms | ✅ 0.26ms | ❌ No available kernel. Aborting execution. |
| 64 | none | False | ✅ 0.10ms | ✅ 0.09ms | ✅ 0.29ms | ❌ No available kernel. Aborting execution. |
| 64 | none | True | ✅ 0.17ms | ✅ 0.12ms | ✅ 0.28ms | ❌ No available kernel. Aborting execution. |
| 120 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 0.15ms | ✅ 0.38ms | ❌ No available kernel. Aborting execution. |
| 120 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 0.14ms | ✅ 0.35ms | ❌ No available kernel. Aborting execution. |
| 120 | none | False | ✅ 0.11ms | ✅ 0.11ms | ✅ 0.49ms | ❌ No available kernel. Aborting execution. |
| 120 | none | True | ✅ 0.17ms | ✅ 0.16ms | ✅ 0.40ms | ❌ No available kernel. Aborting execution. |
| 256 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 0.23ms | ✅ 0.71ms | ❌ No available kernel. Aborting execution. |
| 256 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 0.21ms | ✅ 0.49ms | ❌ No available kernel. Aborting execution. |
| 256 | none | False | ✅ 0.21ms | ✅ 0.21ms | ✅ 0.86ms | ❌ No available kernel. Aborting execution. |
| 256 | none | True | ✅ 0.33ms | ✅ 0.30ms | ✅ 0.75ms | ❌ No available kernel. Aborting execution. |
| 1024 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 1.17ms | ✅ 5.96ms | ❌ No available kernel. Aborting execution. |
| 1024 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 1.07ms | ✅ 5.91ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | False | ✅ 0.83ms | ✅ 0.92ms | ✅ 5.57ms | ❌ No available kernel. Aborting execution. |
| 1024 | none | True | ✅ 0.95ms | ✅ 0.86ms | ✅ 5.91ms | ❌ No available kernel. Aborting execution. |
| 4096 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 12.90ms | ✅ 89.23ms | ❌ No available kernel. Aborting execution. |
| 4096 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 12.70ms | ✅ 88.67ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | False | ✅ 10.81ms | ✅ 10.78ms | ✅ 83.83ms | ❌ No available kernel. Aborting execution. |
| 4096 | none | True | ✅ 8.46ms | ✅ 8.32ms | ✅ 90.78ms | ❌ No available kernel. Aborting execution. |
| 16384 | bool4d | False | ❌ No available kernel. Aborting execution. | ✅ 202.02ms | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | float_add | False | ❌ No available kernel. Aborting execution. | ✅ 202.80ms | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | False | ✅ 162.88ms | ✅ 162.97ms | ❌ OOM | ❌ No available kernel. Aborting execution. |
| 16384 | none | True | ✅ 116.01ms | ✅ 114.12ms | ❌ OOM | ❌ No available kernel. Aborting execution. |

## per-backend totals

| backend | PASS | FAIL | OOM |
|---|---|---|---|
| flash | 24 | 24 | 0 |
| mem_efficient | 24 | 24 | 0 |
| math | 40 | 0 | 8 |
| cudnn | 0 | 48 | 0 |
