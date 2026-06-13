"""
MNIST DPU Benchmark
Measures FPS, accuracy and power on KV260 FPGA DPU (B512)
Run from Jupyter terminal: python3 dpu_bench.py

Prerequisites:
- MNIST data in /home/ubuntu/mnist_data/ (downloaded by setup.sh)
- pynq venv: source /etc/profile.d/pynq_venv.sh
"""
import os, time, gzip, numpy as np

POWER_SENSOR = "/sys/class/hwmon/hwmon2/power1_input"
DATA_DIR     = "/home/ubuntu/mnist_data"
N_WARMUP     = 5
N_BENCHMARK  = 100

# Smart path: local models/ first, then pynq default
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
XMODEL_LOCAL = os.path.join(SCRIPT_DIR, "models", "dpu_mnist_classifier.xmodel")
XMODEL_PYNQ  = "/root/jupyter_notebooks/pynq-dpu/dpu_mnist_classifier.xmodel"
XMODEL = XMODEL_LOCAL if os.path.exists(XMODEL_LOCAL) else XMODEL_PYNQ

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
    print(f"Using xmodel: {XMODEL}", flush=True)
    print("Loading MNIST test data...", flush=True)
    images = load_images(f"{DATA_DIR}/t10k-images-idx3-ubyte.gz")
    labels = load_labels(f"{DATA_DIR}/t10k-labels-idx1-ubyte.gz")
    data = (images.astype(np.float32) / 255.0)[:, :, :, np.newaxis]
    print(f"Test set: {images.shape[0]} images, 28x28 pixels", flush=True)

    print("Loading DPU overlay...", flush=True)
    from pynq_dpu import DpuOverlay
    overlay = DpuOverlay("dpu.bit")
    overlay.load_model(XMODEL)
    dpu = overlay.runner
    in_t  = dpu.get_input_tensors()
    out_t = dpu.get_output_tensors()
    print(f"Input shape:  {in_t[0].dims}", flush=True)
    print(f"Output shape: {out_t[0].dims}  (10 digit classes)", flush=True)

    in_d  = [np.zeros(t.dims, dtype=np.float32) for t in in_t]
    out_d = [np.zeros(t.dims, dtype=np.float32) for t in out_t]

    print(f"\nWarmup ({N_WARMUP} frames)...", flush=True)
    for i in range(N_WARMUP):
        in_d[0][0] = data[i]
        job = dpu.execute_async(in_d, out_d)
        dpu.wait(job)
    print("Warmup done!", flush=True)

    print(f"\nBenchmarking ({N_BENCHMARK} frames with accuracy check)...", flush=True)
    correct = 0
    power_samples = []
    start = time.time()
    for i in range(N_BENCHMARK):
        in_d[0][0] = data[i]
        job = dpu.execute_async(in_d, out_d)
        dpu.wait(job)
        pred = int(np.argmax(out_d[0][0]))
        if pred == int(labels[i]):
            correct += 1
        if i % 10 == 0:
            power_samples.append(read_power_mw())
    elapsed = time.time() - start

    avg_power_w   = sum(power_samples) / len(power_samples) / 1000
    fps           = N_BENCHMARK / elapsed
    latency_ms    = elapsed / N_BENCHMARK * 1000
    fps_per_watt  = fps / avg_power_w
    accuracy      = correct / N_BENCHMARK * 100

    print("\n" + "=" * 40)
    print("MNIST DPU BENCHMARK RESULTS")
    print("=" * 40)
    print(f"Platform:    KV260 DPU (B512)")
    print(f"Model:       MNIST Digit Classifier")
    print(f"Frames:      {N_BENCHMARK}")
    print(f"Accuracy:    {accuracy:.1f}%  ({correct}/{N_BENCHMARK} correct)")
    print(f"FPS:         {fps:.1f}")
    print(f"Latency:     {latency_ms:.1f} ms/frame")
    print(f"Power:       {avg_power_w:.2f} W")
    print(f"FPS/Watt:    {fps_per_watt:.2f}")
    print("=" * 40)

    del overlay
    return fps, accuracy, avg_power_w, fps_per_watt

if __name__ == "__main__":
    run()
