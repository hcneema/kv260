"""
Helloworld CPU Benchmark: Image Resizer
Measures FPS and power on KV260 ARM CPU (Cortex-A53)
Task: Resize 4K (3840x2160) -> 1080p (1920x1080) using PIL

IMPORTANT: Run with pynq venv to avoid NumPy version conflict:
    source /etc/profile.d/pynq_venv.sh
    python3 cpu_bench.py
"""
import time
import numpy as np
from PIL import Image

POWER_SENSOR = "/sys/class/hwmon/hwmon2/power1_input"
N_WARMUP = 3
N_RUNS = 7  # match notebook (7 runs)

IN_SIZE  = (3840, 2160)   # 4K
OUT_SIZE = (1920, 1080)   # 1080p

def read_power_mw():
    with open(POWER_SENSOR) as f:
        return int(f.read().strip()) / 1000

def run():
    print(f"Creating test image {IN_SIZE[0]}x{IN_SIZE[1]}...", flush=True)
    img = Image.fromarray(
        np.random.randint(0, 255, (IN_SIZE[1], IN_SIZE[0], 3), dtype=np.uint8))
    print(f"Input:  {img.size} pixels", flush=True)
    print(f"Output: {OUT_SIZE[0]}x{OUT_SIZE[1]} pixels", flush=True)

    # Warmup
    print(f"\nWarmup ({N_WARMUP} runs)...", flush=True)
    for _ in range(N_WARMUP):
        img.resize(OUT_SIZE, Image.BICUBIC)
    print("Warmup done!", flush=True)

    # Benchmark with power
    print(f"\nBenchmarking ({N_RUNS} runs)...", flush=True)
    times_ms = []
    power_samples = []
    for i in range(N_RUNS):
        p_before = read_power_mw()
        t0 = time.time()
        img.resize(OUT_SIZE, Image.BICUBIC)
        t1 = time.time()
        p_after = read_power_mw()
        times_ms.append((t1 - t0) * 1000)
        power_samples.append((p_before + p_after) / 2)

    avg_ms = sum(times_ms) / len(times_ms)
    avg_power_w = sum(power_samples) / len(power_samples) / 1000
    fps = 1000 / avg_ms
    fps_per_watt = fps / avg_power_w

    print("\n" + "=" * 40)
    print("CPU RESIZER BENCHMARK RESULTS")
    print("=" * 40)
    print(f"Platform:    KV260 ARM CPU (Cortex-A53)")
    print(f"Task:        4K -> 1080p resize (PIL BICUBIC)")
    print(f"Time/frame:  {avg_ms:.1f} ms")
    print(f"FPS:         {fps:.2f}")
    print(f"Power:       {avg_power_w:.2f} W")
    print(f"FPS/Watt:    {fps_per_watt:.2f}")
    print("=" * 40)
    print(f"Expected:    ~377ms, ~2.65 FPS, ~3.34W, ~0.79 FPS/Watt")

    return avg_ms, fps, avg_power_w, fps_per_watt

if __name__ == "__main__":
    run()
