# TICKET-001 — Verify WSL2 + Docker + NVIDIA CUDA GPU access

**id:** TICKET-001
**title:** Verify WSL2 + Docker + NVIDIA CUDA GPU access
**status:** DONE
**priority:** P0
**category:** Infrastructure
**effort:** S
**depends_on:** none

## Goal

Confirm RTX 5070 (sm_120) accessible from WSL2 Ubuntu and from inside Docker containers with `--gpus all`.

## Acceptance Criteria

- `nvidia-smi` inside WSL2 Ubuntu shows RTX 5070
- `docker run --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi` shows GPU
- `.wslconfig` configured: memory=48GB, processors=16, swap=8GB
- Docker Desktop resource limits reviewed and aligned with `.wslconfig`
- Windows host driver version and CUDA version documented
- `/usr/lib/wsl/lib/libcuda.so` exists and is functional

## Implementation Notes

- Check current Windows NVIDIA driver: `nvidia-smi` on Windows host
- Inside WSL2: `nvidia-smi` works via `/usr/lib/wsl` passthrough
- Docker test: `docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi`
- `.wslconfig` location: `C:\Users\<username>\.wslconfig`
- After `.wslconfig` changes: `wsl --shutdown` then restart

## Completion Notes

GPU, Docker, CUDA passthrough verified. Services running on RTX 5070 via WSL2 CUDA. 2026-04-08.
