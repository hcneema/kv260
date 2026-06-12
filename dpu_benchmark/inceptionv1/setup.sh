#!/bin/bash
# InceptionV1 Benchmark Setup
# Usage: cd /home/ubuntu/dpu_benchmark && bash inceptionv1/setup.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== InceptionV1 Benchmark Setup ==="

# 1. Install onnxruntime
echo "[1/3] Installing onnxruntime..."
pip3 install onnxruntime --quiet
echo "onnxruntime: $(python3 -c 'import onnxruntime; print(onnxruntime.__version__)')"

# 2. Copy CPU model
MODEL_SRC="$SCRIPT_DIR/models/inception-v1-9.onnx"
MODEL_DST="/home/ubuntu/inception-v1-9.onnx"
if [ -f "$MODEL_SRC" ]; then
    echo "[2/3] Copying inception-v1-9.onnx to /home/ubuntu/ (27MB)..."
    cp "$MODEL_SRC" "$MODEL_DST"
    echo "Done ($(du -h $MODEL_DST | cut -f1))"
else
    echo "[2/3] WARNING: models/inception-v1-9.onnx not found"
    echo "      Download from: https://github.com/onnx/models/blob/main/validated/vision/classification/inception_and_googlenet/inception_v1/model/inception-v1-9.onnx"
    echo "      Click 'Download raw file' in browser, save to inceptionv1/models/"
fi

# 3. Verify DPU xmodel
XMODEL_PYNQ="/root/jupyter_notebooks/pynq-dpu/dpu_tf_inceptionv1.xmodel"
XMODEL_LOCAL="$SCRIPT_DIR/models/dpu_tf_inceptionv1.xmodel"
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
echo "DPU: open dpu_bench.ipynb  (expected: ~217 FPS, ~27.44 FPS/Watt — fastest model!)"
echo "CPU: open cpu_bench.ipynb  (expected: ~3.86 FPS, ~0.92 FPS/Watt)"
echo "DPU advantage: 30x more energy efficient"
