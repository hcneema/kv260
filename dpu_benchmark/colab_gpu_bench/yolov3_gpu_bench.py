# -*- coding: utf-8 -*-
"""
YOLOv3 GPU Benchmark — Google Colab T4
Measures FPS, latency, and GPU power for comparison with KV260 DPU/CPU results.

Mismatches vs KV260 (documented caveats):
  - Model variant: Ultralytics auto-upgrades yolov3.pt → yolov3u.pt (103M params vs ~62M).
    Standard YOLOv3 on T4 would be faster — this is a conservative (lower-bound) GPU estimate.
  - Framework: PyTorch FP32 (T4) vs ONNX Runtime FP32 (CPU) / pynq-dpu INT8 (DPU)
  - Input size: 640×640 (Ultralytics native) vs 416×416 (KV260)
  - Training data: COCO (T4) vs VOC (KV260 DPU xmodel)
Each platform runs at its natural operating point.

Paste into a Colab cell or run as a script.
Runtime → Change runtime type → T4 GPU before running.
"""

import subprocess
subprocess.run(['pip', 'install', 'ultralytics', '-q'], check=True)

import time
import threading
import numpy as np
import torch
from ultralytics import YOLO

# ── Config ────────────────────────────────────────────────────────────────────
N_ROUNDS       = 10
N_WARMUP       = 10
N_FRAMES       = 100
IDLE_SECS      = 10
POWER_INTERVAL = 0.2
IMG_SIZE       = 640   # Ultralytics native; KV260 used 416

# ── GPU check ─────────────────────────────────────────────────────────────────
print(f"PyTorch version: {torch.__version__}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
else:
    print("WARNING: No GPU found — running on CPU.")

# ── GPU info ──────────────────────────────────────────────────────────────────
def get_gpu_info():
    try:
        name = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            capture_output=True, text=True).stdout.strip()
        mem = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True).stdout.strip()
        driver = subprocess.run(
            ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
            capture_output=True, text=True).stdout.strip()
        return name, mem, driver
    except Exception:
        return 'Unknown', 'Unknown', 'Unknown'

# ── Power sampling ────────────────────────────────────────────────────────────
def read_gpu_power_w():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=power.draw', '--format=csv,noheader,nounits'],
            capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

class PowerSampler:
    def __init__(self):
        self.samples = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.samples = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join()

    def _run(self):
        while not self._stop.is_set():
            self.samples.append(read_gpu_power_w())
            time.sleep(POWER_INTERVAL)

    def mean_w(self):
        return float(np.mean(self.samples)) if self.samples else 0.0

    def std_w(self):
        return float(np.std(self.samples)) if self.samples else 0.0

# ── Load model ────────────────────────────────────────────────────────────────
print("\nLoading YOLOv3 (Ultralytics, COCO weights)...")
yolo = YOLO('yolov3.pt')
pt_model = yolo.model.eval().cuda()
print(f"Model loaded. Parameters: {sum(p.numel() for p in pt_model.parameters()):,}")

# Dummy input on GPU — 640×640 (Ultralytics native)
dummy_input = torch.rand(1, 3, IMG_SIZE, IMG_SIZE, dtype=torch.float32).cuda()

# ── Measure idle power (once) ─────────────────────────────────────────────────
print(f"\nMeasuring idle GPU power ({IDLE_SECS}s)...")
idle_sampler = PowerSampler()
idle_sampler.start()
time.sleep(IDLE_SECS)
idle_sampler.stop()
idle_w = idle_sampler.mean_w()
print(f"  Idle power: {idle_w:.2f} W")

# ── Warmup (once) ─────────────────────────────────────────────────────────────
print(f"\nWarmup ({N_WARMUP} frames)...")
with torch.no_grad():
    for _ in range(N_WARMUP):
        _ = pt_model(dummy_input)
        torch.cuda.synchronize()
print("Warmup done.")

# ── 10-round benchmark ────────────────────────────────────────────────────────
round_fps      = []
round_lat_mean = []
round_lat_p95  = []
round_lat_p99  = []
round_power    = []
round_delta    = []
round_fps_w    = []

print(f"\n{'Rnd':>4}  {'FPS':>7}  {'Lat_mean':>9}  {'Lat_p95':>8}  {'ActiveW':>8}  {'DeltaW':>7}  {'FPS/W_d':>8}")
print("-" * 68)

for rnd in range(1, N_ROUNDS + 1):
    sampler = PowerSampler()
    sampler.start()

    latencies_ms = []
    t_total_start = time.perf_counter()
    with torch.no_grad():
        for _ in range(N_FRAMES):
            torch.cuda.synchronize()          # flush any pending GPU work
            t0 = time.perf_counter()
            _ = pt_model(dummy_input)
            torch.cuda.synchronize()          # wait for GPU to finish
            latencies_ms.append((time.perf_counter() - t0) * 1000)
    t_total = time.perf_counter() - t_total_start

    sampler.stop()

    fps      = N_FRAMES / t_total
    lat_mean = float(np.mean(latencies_ms))
    lat_p95  = float(np.percentile(latencies_ms, 95))
    lat_p99  = float(np.percentile(latencies_ms, 99))
    pwr_avg  = sampler.mean_w()
    delta_w  = max(pwr_avg - idle_w, 0.0)
    fps_w    = fps / delta_w if delta_w > 0 else float('inf')

    round_fps.append(fps)
    round_lat_mean.append(lat_mean)
    round_lat_p95.append(lat_p95)
    round_lat_p99.append(lat_p99)
    round_power.append(pwr_avg)
    round_delta.append(delta_w)
    round_fps_w.append(fps_w)

    print(f"{rnd:>4}  {fps:>7.1f}  {lat_mean:>9.2f}  {lat_p95:>8.2f}  {pwr_avg:>8.2f}  {delta_w:>7.2f}  {fps_w:>8.2f}")

# ── Aggregate stats ───────────────────────────────────────────────────────────
fps_mean     = float(np.mean(round_fps))
fps_std      = float(np.std(round_fps))
lat_mean_agg = float(np.mean(round_lat_mean))
lat_p95_agg  = float(np.mean(round_lat_p95))
lat_p99_agg  = float(np.mean(round_lat_p99))
power_mean   = float(np.mean(round_power))
power_std    = float(np.std(round_power))
delta_mean   = float(np.mean(round_delta))
fps_w_mean   = float(np.mean(round_fps_w))
fps_w_std    = float(np.std(round_fps_w))
mj_frame     = (power_mean / fps_mean) * 1000 if fps_mean > 0 else 0.0
mj_delta     = (delta_mean / fps_mean) * 1000 if fps_mean > 0 else 0.0

gpu_name, gpu_mem_mb, driver = get_gpu_info()

print(f"""
============================================================
YOLOV3 GPU BENCHMARK RESULTS ({N_ROUNDS} rounds × {N_FRAMES} frames)
============================================================
Platform:       Google Colab — {gpu_name}
GPU memory:     {gpu_mem_mb} MB
Driver:         {driver}
PyTorch:        {torch.__version__}
Model:          YOLOv3 (Ultralytics, COCO weights, {IMG_SIZE}×{IMG_SIZE})
Caveats:        PyTorch/FP32 vs ONNX RT (CPU) / pynq-dpu INT8 (DPU)
                640×640 input (T4) vs 416×416 (KV260)
                COCO training (T4) vs VOC training (KV260 DPU)
------------------------------------------------------------
FPS:            {fps_mean:.2f} ± {fps_std:.2f}
Latency mean:   {lat_mean_agg:.2f} ms
Latency p95:    {lat_p95_agg:.2f} ms
Latency p99:    {lat_p99_agg:.2f} ms
------------------------------------------------------------
Idle power:     {idle_w:.2f} W
Active power:   {power_mean:.2f} ± {power_std:.2f} W
Delta power:    {delta_mean:.2f} W  (active − idle)
FPS/W (delta):  {fps_w_mean:.2f} ± {fps_w_std:.2f}   ← primary efficiency metric
mJ/frame:       {mj_frame:.2f}
mJ/frame delta: {mj_delta:.2f}
------------------------------------------------------------
KV260 DPU ref (YOLOv3, 416×416, VOC): 13.23 ± 0.02 FPS | 3.09 ± 0.10 FPS/W_delta
KV260 CPU ref (YOLOv3, 416×416, COCO): 0.22 ± 0.00 FPS | 0.17 ± 0.01 FPS/W_delta
============================================================
""")
