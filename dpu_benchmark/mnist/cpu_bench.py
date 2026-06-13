"""
MNIST CPU Benchmark
Measures FPS, accuracy and power on KV260 ARM CPU (Cortex-A53)
Uses ONNX Runtime for inference

Run from terminal: python3 cpu_bench.py

Prerequisites:
- MNIST data in /home/ubuntu/mnist_data/ (downloaded by setup.sh)
- onnxruntime installed: pip3 install onnxruntime
- MNIST ONNX model: models/mnist-12.onnx (included)
"""
import os, time, gzip, numpy as np

POWER_SENSOR = "/sys/class/hwmon/hwmon2/power1_input"
DATA_DIR     = "/home/ubuntu/mnist_data"
N_WARMUP     = 5
N_BENCHMARK  = 100

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_LOCAL  = os.path.join(SCRIPT_DIR, "models", "mnist-12.onnx")
MODEL_UBUNTU = "/home/ubuntu/mnist-12.onnx"
MODEL_PATH   = MODEL_LOCAL if os.path.exists(MODEL_LOCAL) else MODEL_UBUNTU

def read_power_mw():
    with open(POWER_SENSOR) as f:
        return int(f.read().strip()) / 1000

def load_images(path):
    with gzip.open(path, 'rb') as f:
        f.read(16)
        return np.frombuffer(f.read(), dtype=np.uint8).reshape(-1, 28, 28)

def load_labels(path):
    with gzip.open(path, 'rb') as f:
        f.read(8)
        return np.frombuffer(f.read(), dtype=np.uint8)

def run():
    import onnxruntime as ort
    print(f"ONNX Runtime version: {ort.__version__}", flush=True)
    print(f"Using model: {MODEL_PATH}", flush=True)

    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found. Run setup.sh first.", flush=True)
        return

    print("Loading MNIST test data...", flush=True)
    images = load_images(f"{DATA_DIR}/t10k-images-idx3-ubyte.gz")
    labels = load_labels(f"{DATA_DIR}/t10k-labels-idx1-ubyte.gz")
    # MNIST ONNX model expects (1, 1, 28, 28) float32
    data = images.astype(np.float32)[:, np.newaxis, :, :] / 255.0
    print(f"Test set: {images.shape[0]} images", flush=True)

    session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    print(f"Input: {input_name} {session.get_inputs()[0].shape}", flush=True)

    print(f"\nWarmup ({N_WARMUP} frames)...", flush=True)
    for i in range(N_WARMUP):
        session.run(None, {input_name: data[i:i+1]})
    print("Warmup done!", flush=True)

    print(f"\nBenchmarking ({N_BENCHMARK} frames)...", flush=True)
    correct = 0
    power_samples = []
    start = time.time()
    for i in range(N_BENCHMARK):
        result = session.run(None, {input_name: data[i:i+1]})
        pred = int(np.argmax(result[0]))
        if pred == int(labels[i]):
            correct += 1
        if i % 10 == 0:
            power_samples.append(read_power_mw())
    elapsed = time.time() - start

    avg_power_w  = sum(power_samples) / len(power_samples) / 1000
    fps          = N_BENCHMARK / elapsed
    latency_ms   = elapsed / N_BENCHMARK * 1000
    fps_per_watt = fps / avg_power_w
    accuracy     = correct / N_BENCHMARK * 100

    print("\n" + "=" * 40)
    print("MNIST CPU BENCHMARK RESULTS")
    print("=" * 40)
    print(f"Platform:    KV260 ARM CPU (Cortex-A53)")
    print(f"Model:       MNIST ONNX")
    print(f"Frames:      {N_BENCHMARK}")
    print(f"Accuracy:    {accuracy:.1f}%  ({correct}/{N_BENCHMARK} correct)")
    print(f"FPS:         {fps:.1f}")
    print(f"Latency:     {latency_ms:.2f} ms/frame")
    print(f"Power:       {avg_power_w:.2f} W")
    print(f"FPS/Watt:    {fps_per_watt:.2f}")
    print("=" * 40)

    return fps, accuracy, avg_power_w, fps_per_watt

if __name__ == "__main__":
    run()
