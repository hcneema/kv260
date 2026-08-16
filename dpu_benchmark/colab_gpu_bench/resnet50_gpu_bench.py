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
    """Read current GPU power draw in watts via nvidia-smi."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=power.draw', '--format=csv,noheader,nounits'],
            capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

class PowerSampler:
    """Background thread that samples GPU power every POWER_INTERVAL seconds."""
    def __init__(self):
        self.samples = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.samples = []
        self._stop.clear()
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

# Dummy input — match KV260 benchmark (random float32, batch=1)
dummy_input = np.random.rand(1, 224, 224, 3).astype(np.float32)
dummy_input_tf = tf.constant(dummy_input)  # keep on GPU side

# Compiled inference function — forces GPU graph execution
@tf.function
def run_inference(x):
    return model(x, training=False)

# ── Measure idle power ────────────────────────────────────────────────────────
print(f"\nMeasuring idle GPU power ({IDLE_SECS}s)...")
idle_sampler = PowerSampler()
idle_sampler.start()
time.sleep(IDLE_SECS)
idle_sampler.stop()
idle_w = idle_sampler.mean_w()
print(f"  Idle power: {idle_w:.2f} W")

# ── Warmup ────────────────────────────────────────────────────────────────────
print(f"\nWarmup ({N_WARMUP} frames)...")
with tf.device('/GPU:0'):
    for _ in range(N_WARMUP):
        _ = run_inference(dummy_input_tf)
print("Warmup done.")

# ── Benchmark ─────────────────────────────────────────────────────────────────
print(f"\nBenchmarking ({N_FRAMES} frames)...")
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

# ── Compute stats ─────────────────────────────────────────────────────────────
fps          = N_FRAMES / t_total
lat_mean     = float(np.mean(latencies_ms))
lat_std      = float(np.std(latencies_ms))
lat_min      = float(np.min(latencies_ms))
lat_max      = float(np.max(latencies_ms))
lat_p95      = float(np.percentile(latencies_ms, 95))
lat_p99      = float(np.percentile(latencies_ms, 99))
power_avg    = sampler.mean_w()
power_std    = sampler.std_w()
delta_w      = max(power_avg - idle_w, 0.0)
fps_w_total  = fps / power_avg  if power_avg  > 0 else 0.0
fps_w_delta  = fps / delta_w    if delta_w    > 0 else float('inf')
mj_frame     = (power_avg / fps) * 1000 if fps > 0 else 0.0
mj_delta     = (delta_w   / fps) * 1000 if fps > 0 else 0.0

# ── GPU info ──────────────────────────────────────────────────────────────────
gpu_name, gpu_mem_mb, driver = get_gpu_info()

# ── Print results ─────────────────────────────────────────────────────────────
print(f"""
============================================================
RESNET50 GPU BENCHMARK RESULTS
============================================================
Platform:       Google Colab — {gpu_name}
GPU memory:     {gpu_mem_mb} MB
Driver:         {driver}
TensorFlow:     {tf.__version__}
Model:          ResNet50 (Keras, ImageNet weights, 1000 classes)
Frames:         {N_FRAMES}
------------------------------------------------------------
FPS:            {fps:.1f}
Latency mean:   {lat_mean:.2f} ms
Latency std:    {lat_std:.2f} ms
Latency min:    {lat_min:.2f} ms
Latency max:    {lat_max:.2f} ms
Latency p95:    {lat_p95:.2f} ms
Latency p99:    {lat_p99:.2f} ms
------------------------------------------------------------
Idle power:     {idle_w:.2f} W
Active power:   {power_avg:.2f} ± {power_std:.2f} W
Delta power:    {delta_w:.2f} W  (active − idle)
FPS/W (total):  {fps_w_total:.2f}
FPS/W (delta):  {fps_w_delta:.2f}   ← primary efficiency metric
mJ/frame:       {mj_frame:.2f}
mJ/frame delta: {mj_delta:.2f}
------------------------------------------------------------
KV260 DPU ref:  84.4 FPS | 8.16W active | 28.65 FPS/W_delta
KV260 CPU ref:   1.6 FPS | 6.01W active |  1.33 FPS/W_delta
============================================================
""")
