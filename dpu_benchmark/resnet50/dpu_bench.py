"""
ResNet50 DPU Benchmark
Measures FPS and power consumption on KV260 FPGA DPU (B512)
Run from Jupyter terminal: python3 dpu_bench.py

Uses dpu.bit from pynq-dpu package (B512 — installed by Kria-PYNQ)
"""
import os
import time
import numpy as np

POWER_SENSOR = "/sys/class/hwmon/hwmon2/power1_input"
N_WARMUP = 10
N_BENCHMARK = 100

# Find xmodel — check local models/ directory first, then pynq-dpu default
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
XMODEL_LOCAL  = os.path.join(SCRIPT_DIR, "models", "dpu_resnet50.xmodel")
XMODEL_PYNQ   = "/root/jupyter_notebooks/pynq-dpu/dpu_resnet50.xmodel"
XMODEL = XMODEL_LOCAL if os.path.exists(XMODEL_LOCAL) else XMODEL_PYNQ

def read_power_mw():
    with open(POWER_SENSOR) as f:
        return int(f.read().strip()) / 1000  # microwatts -> milliwatts

def run():
    from pynq_dpu import DpuOverlay

    print(f"Using xmodel: {XMODEL}", flush=True)
    print("Loading DPU overlay (dpu.bit = B512)...", flush=True)
    overlay = DpuOverlay("dpu.bit")
    print("Overlay loaded!", flush=True)

    overlay.load_model(XMODEL)
    print("ResNet50 model loaded!", flush=True)

    dpu = overlay.runner
    in_t  = dpu.get_input_tensors()
    out_t = dpu.get_output_tensors()
    print(f"Input shape:  {in_t[0].dims}", flush=True)
    print(f"Output shape: {out_t[0].dims}", flush=True)

    in_d  = [np.zeros(t.dims, dtype=np.int8) for t in in_t]
    out_d = [np.zeros(t.dims, dtype=np.int8) for t in out_t]

    print(f"\nWarmup ({N_WARMUP} frames)...", flush=True)
    for _ in range(N_WARMUP):
        job = dpu.execute_async(in_d, out_d)
        dpu.wait(job)
    print("Warmup done!", flush=True)

    print(f"\nBenchmarking ({N_BENCHMARK} frames)...", flush=True)
    power_samples = []
    start = time.time()
    for i in range(N_BENCHMARK):
        job = dpu.execute_async(in_d, out_d)
        dpu.wait(job)
        if i % 10 == 0:
            power_samples.append(read_power_mw())
    elapsed = time.time() - start

    avg_power_mw = sum(power_samples) / len(power_samples)
    fps = N_BENCHMARK / elapsed
    latency_ms = elapsed / N_BENCHMARK * 1000
    fps_per_watt = fps / (avg_power_mw / 1000)

    print("\n" + "="*40)
    print("RESNET50 DPU BENCHMARK RESULTS")
    print("="*40)
    print(f"Platform:      KV260 DPU (B512)")
    print(f"Model:         ResNet50")
    print(f"Frames:        {N_BENCHMARK}")
    print(f"Total time:    {elapsed:.2f}s")
    print(f"FPS:           {fps:.1f}")
    print(f"Latency:       {latency_ms:.1f} ms/frame")
    print(f"Power (avg):   {avg_power_mw/1000:.2f} W")
    print(f"FPS/Watt:      {fps_per_watt:.2f}")
    print("="*40)
    print(f"Expected: ~92 FPS, ~8.72W, ~10.56 FPS/Watt")

    del overlay
    return fps, avg_power_mw/1000, fps_per_watt

if __name__ == "__main__":
    run()
