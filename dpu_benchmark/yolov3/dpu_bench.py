"""
YOLOv3 DPU Benchmark
Measures FPS and power consumption on KV260 FPGA DPU (B512)
Run from Jupyter terminal: python3 dpu_bench.py
"""
import os
import time
import numpy as np

POWER_SENSOR = "/sys/class/hwmon/hwmon2/power1_input"
N_WARMUP = 5
N_BENCHMARK = 100

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
XMODEL_LOCAL = os.path.join(SCRIPT_DIR, "models", "tf_yolov3_voc.xmodel")
XMODEL_PYNQ  = "/root/jupyter_notebooks/pynq-dpu/tf_yolov3_voc.xmodel"
XMODEL = XMODEL_LOCAL if os.path.exists(XMODEL_LOCAL) else XMODEL_PYNQ

def read_power_mw():
    with open(POWER_SENSOR) as f:
        return int(f.read().strip()) / 1000

def run():
    from pynq_dpu import DpuOverlay

    print(f"Using xmodel: {XMODEL}", flush=True)
    print("Loading DPU overlay (dpu.bit = B512)...", flush=True)
    overlay = DpuOverlay("dpu.bit")
    print("Overlay loaded!", flush=True)

    overlay.load_model(XMODEL)
    print("YOLOv3 model loaded!", flush=True)

    dpu = overlay.runner
    in_t  = dpu.get_input_tensors()
    out_t = dpu.get_output_tensors()
    print(f"Input shape:   {in_t[0].dims}", flush=True)
    print(f"Output shapes: {[t.dims for t in out_t]}", flush=True)

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
    print("YOLOV3 DPU BENCHMARK RESULTS")
    print("="*40)
    print(f"Platform:      KV260 DPU (B512)")
    print(f"Model:         YOLOv3 (VOC)")
    print(f"Frames:        {N_BENCHMARK}")
    print(f"Total time:    {elapsed:.2f}s")
    print(f"FPS:           {fps:.1f}")
    print(f"Latency:       {latency_ms:.1f} ms/frame")
    print(f"Power (avg):   {avg_power_mw/1000:.2f} W")
    print(f"FPS/Watt:      {fps_per_watt:.2f}")
    print("="*40)
    print(f"Expected: ~14.7 FPS, ~9.75W, ~1.51 FPS/Watt")

    del overlay
    return fps, avg_power_mw/1000, fps_per_watt

if __name__ == "__main__":
    run()
