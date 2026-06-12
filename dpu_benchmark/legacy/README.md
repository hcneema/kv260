# Legacy Scripts

## dpu_bench.py
Early prototype script used during initial DPU testing (2026-06-10).
- Used `download=False` targeting B4096 xclbin — this approach was abandoned
- The B4096 DPU inference was never fully verified (runner hung due to CMA issues)
- Superseded by the per-model benchmark scripts in `resnet50/`, `yolov3/`, `inceptionv1/`

**Do not use** — kept for reference only.
