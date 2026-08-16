# -*- coding: utf-8 -*-
"""
ResNet50 GPU Benchmark — Google Colab T4
Measures FPS, latency, and GPU power for comparison with KV260 DPU/CPU results.

Paste into a Colab cell or run as a script.
Runtime → Change runtime type → T4 GPU before running.
"""

import time
import threading
import subprocess
import numpy as np
import tensorflow as tf

# ── Config (match KV260 benchmark settings) ───────────────────────────────────
N_ROUNDS   = 10
N_WARMUP   = 10
N_FRAMES   = 100
IDLE_SECS  = 10       # seconds to sample idle power before warmup
POWER_INTERVAL = 0.2  # seconds between nvidia-smi power samples

# ── GPU setup (from working template) ─────────────────────────────────────────
print(f"TensorFlow version: {tf.__version__}")
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    print(f"GPU available: {len(gpus)} physical, {len(tf.config.experimental.list_logical_devices('GPU'))} logical")
else:
    print("WARNING: No GPU found — running on CPU. Results not comparable to KV260 DPU benchmark.")

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
print("\nLoading ResNet50 (ImageNet weights, 1000 classes)...")
model = tf.keras.applications.ResNet50(
    input_shape=(224, 224, 3),
    include_top=True,
    weights='imagenet',
    classes=1000
)
print(f"Model loaded. Parameters: {model.count_params():,}")

dummy_input = np.random.rand(1, 224, 224, 3).astype(np.float32)
dummy_input_tf = tf.constant(dummy_input)

@tf.function
def run_inference(x):
    return model(x, training=False)

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
with tf.device('/GPU:0'):
    for _ in range(N_WARMUP):
        _ = run_inference(dummy_input_tf)
print("Warmup done.")

# ── 10-round benchmark ────────────────────────────────────────────────────────
round_fps     = []
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
    with tf.device('/GPU:0'):
        for _ in range(N_FRAMES):
            t0 = time.perf_counter()
            _ = run_inference(dummy_input_tf)
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
fps_mean      = float(np.mean(round_fps))
fps_std       = float(np.std(round_fps))
lat_mean_agg  = float(np.mean(round_lat_mean))
lat_p95_agg   = float(np.mean(round_lat_p95))
lat_p99_agg   = float(np.mean(round_lat_p99))
power_mean    = float(np.mean(round_power))
power_std     = float(np.std(round_power))
delta_mean    = float(np.mean(round_delta))
fps_w_mean    = float(np.mean(round_fps_w))
fps_w_std     = float(np.std(round_fps_w))
mj_frame      = (power_mean / fps_mean) * 1000 if fps_mean > 0 else 0.0
mj_delta      = (delta_mean / fps_mean) * 1000 if fps_mean > 0 else 0.0

gpu_name, gpu_mem_mb, driver = get_gpu_info()

print(f"""
============================================================
RESNET50 GPU BENCHMARK RESULTS ({N_ROUNDS} rounds × {N_FRAMES} frames)
============================================================
Platform:       Google Colab — {gpu_name}
GPU memory:     {gpu_mem_mb} MB
Driver:         {driver}
TensorFlow:     {tf.__version__}
Model:          ResNet50 (Keras, ImageNet weights, 1000 classes)
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
KV260 DPU ref:  84.38 ± 0.05 FPS | 8.16W active | 28.65 ± 0.79 FPS/W_delta
KV260 CPU ref:   1.58 ± 0.04 FPS | 6.01W active |  1.33 ± 0.03 FPS/W_delta
============================================================
""")
