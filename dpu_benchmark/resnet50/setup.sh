#!/bin/bash
# ResNet50 Benchmark Setup
# Run this once on a fresh KV260 board.
# Usage: cd /home/ubuntu/dpu_benchmark && bash resnet50/setup.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== ResNet50 Benchmark Setup ==="

# 1. Install onnxruntime
echo "[1/3] Installing onnxruntime..."
pip3 install onnxruntime --quiet
echo "onnxruntime: $(python3 -c 'import onnxruntime; print(onnxruntime.__version__)')"

# 2. Copy CPU model to /home/ubuntu/ (scripts also check models/ directly)
MODEL_SRC="$SCRIPT_DIR/models/resnet50-v1-7.onnx"
MODEL_DST="/home/ubuntu/resnet50-v1-7.onnx"
if [ -f "$MODEL_SRC" ]; then
    echo "[2/3] Copying resnet50-v1-7.onnx to /home/ubuntu/..."
    cp "$MODEL_SRC" "$MODEL_DST"
    echo "Done ($(du -h $MODEL_DST | cut -f1))"
else
    echo "[2/3] WARNING: models/resnet50-v1-7.onnx not found — scripts will use /home/ubuntu/ path if available"
fi

# 3. Verify DPU xmodel
XMODEL_PYNQ="/root/jupyter_notebooks/pynq-dpu/dpu_resnet50.xmodel"
XMODEL_LOCAL="$SCRIPT_DIR/models/dpu_resnet50.xmodel"
if [ -f "$XMODEL_LOCAL" ]; then
    echo "[3/3] DPU xmodel found: $XMODEL_LOCAL"
elif [ -f "$XMODEL_PYNQ" ]; then
    echo "[3/3] DPU xmodel found: $XMODEL_PYNQ"
else
    echo "[3/3] ERROR: DPU xmodel not found. Install Kria-PYNQ first."
    exit 1
fi

echo ""
echo "=== Setup Complete ==="
echo "Open Jupyter: http://$(hostname -I | awk '{print $1}'):9090/lab  password: xilinx"
echo "DPU: open dpu_bench.ipynb  (expected: ~92 FPS, ~10.6 FPS/Watt)"
echo "CPU: open cpu_bench.ipynb  (expected: ~1.6 FPS, ~0.37 FPS/Watt)"
echo "DPU advantage: 29x more energy efficient"
