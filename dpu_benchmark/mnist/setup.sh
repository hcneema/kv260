#!/bin/bash
# MNIST Benchmark Setup
# Usage: cd /home/ubuntu/dpu_benchmark && bash mnist/setup.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== MNIST Benchmark Setup ==="

# 1. Install onnxruntime
echo "[1/3] Installing onnxruntime..."
pip3 install onnxruntime --quiet
echo "onnxruntime: $(python3 -c 'import onnxruntime; print(onnxruntime.__version__)')"

# 2. Download MNIST data from Google mirror (official URL is dead)
echo "[2/3] Downloading MNIST dataset..."
python3 << 'PYEOF'
import urllib.request, os, sys

base = "https://storage.googleapis.com/cvdf-datasets/mnist/"
files = [
    "train-images-idx3-ubyte.gz",
    "train-labels-idx1-ubyte.gz",
    "t10k-images-idx3-ubyte.gz",
    "t10k-labels-idx1-ubyte.gz"
]
data_dir = "/home/ubuntu/mnist_data"
os.makedirs(data_dir, exist_ok=True)

for fname in files:
    dest = os.path.join(data_dir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  Cached: {fname}")
    else:
        print(f"  Downloading {fname}...", flush=True)
        urllib.request.urlretrieve(base + fname, dest)
        print(f"  Done: {os.path.getsize(dest)} bytes")
print("MNIST data ready!")
PYEOF

# 3. Copy MNIST ONNX model to /home/ubuntu/
MODEL_SRC="$SCRIPT_DIR/models/mnist-12.onnx"
MODEL_DST="/home/ubuntu/mnist-12.onnx"
if [ -f "$MODEL_SRC" ]; then
    cp "$MODEL_SRC" "$MODEL_DST"
    echo "[3/3] Copied mnist-12.onnx ($(du -h $MODEL_DST | cut -f1))"
else
    echo "[3/3] WARNING: models/mnist-12.onnx not found"
fi

echo ""
echo "=== Setup Complete ==="
echo "Run benchmarks:"
echo "  DPU: source /etc/profile.d/pynq_venv.sh && python3 $SCRIPT_DIR/dpu_bench.py"
echo "  CPU: python3 $SCRIPT_DIR/cpu_bench.py"
echo ""
echo "Expected results:"
echo "  DPU: ~2863 FPS, 99.0% accuracy, 5.61W, 510 FPS/Watt"
echo "  CPU: ~2060 FPS, 98.0% accuracy, 5.57W, 370 FPS/Watt"
echo "  DPU advantage: 1.4x (small model — DPU shines on larger CNNs)"
