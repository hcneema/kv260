"""
InceptionV1 (GoogLeNet) CPU Benchmark
Measures FPS and power consumption on KV260 ARM CPU (Cortex-A53)
Run from terminal: python3 cpu_bench.py
"""
import os
import time
import numpy as np

POWER_SENSOR = "/sys/class/hwmon/hwmon2/power1_input"
N_WARMUP = 3
N_BENCHMARK = 20

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_LOCAL  = os.path.join(SCRIPT_DIR, "models", "inception-v1-9.onnx")
MODEL_UBUNTU = "/home/ubuntu/inception-v1-9.onnx"
MODEL_PATH   = MODEL_LOCAL if os.path.exists(MODEL_LOCAL) else MODEL_UBUNTU

def read_power_mw():
    with open(POWER_SENSOR) as f:
        return int(f.read().strip()) / 1000

def run():
    import onnxruntime as ort

    print(f"ONNX Runtime version: {ort.__version__}", flush=True)

    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        print("Run setup_all.sh first, or copy inception-v1-9.onnx to models/")
        exit(1)

    print(f"Using model: {MODEL_PATH}", flush=True)
    print("Loading InceptionV1 ONNX model...", flush=True)
    session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])

    input_name = session.get_inputs()[0].name
    print(f"Input: {input_name} {session.get_inputs()[0].shape}", flush=True)

    dummy_input = np.random.randn(1, 3, 224, 224).astype(np.float32)

    print(f"\nWarmup ({N_WARMUP} frames)...", flush=True)
    for _ in range(N_WARMUP):
        session.run(None, {input_name: dummy_input})
    print("Warmup done!", flush=True)

    print(f"\nBenchmarking ({N_BENCHMARK} frames)...", flush=True)
    power_samples = []
    start = time.time()
    for i in range(N_BENCHMARK):
        session.run(None, {input_name: dummy_input})
        if i % 5 == 0:
            power_samples.append(read_power_mw())
    elapsed = time.time() - start

    avg_power_mw = sum(power_samples) / len(power_samples)
    fps = N_BENCHMARK / elapsed
    latency_ms = elapsed / N_BENCHMARK * 1000
    fps_per_watt = fps / (avg_power_mw / 1000)

    print("\n" + "="*40)
    print("INCEPTIONV1 CPU BENCHMARK RESULTS")
    print("="*40)
    print(f"Platform:      KV260 ARM CPU (Cortex-A53)")
    print(f"Model:         InceptionV1 ONNX (GoogLeNet)")
    print(f"Frames:        {N_BENCHMARK}")
    print(f"Total time:    {elapsed:.2f}s")
    print(f"FPS:           {fps:.2f}")
    print(f"Latency:       {latency_ms:.1f} ms/frame")
    print(f"Power (avg):   {avg_power_mw/1000:.2f} W")
    print(f"FPS/Watt:      {fps_per_watt:.2f}")
    print("="*40)
    print(f"Expected: ~3.86 FPS, ~4.21W, ~0.92 FPS/Watt")

    return fps, avg_power_mw/1000, fps_per_watt

if __name__ == "__main__":
    run()
