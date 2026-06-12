#!/bin/bash
# YOLOv3 Benchmark Setup
# Usage: cd /home/ubuntu/dpu_benchmark && bash yolov3/setup.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== YOLOv3 Benchmark Setup ==="

# 1. Install onnxruntime
echo "[1/3] Installing onnxruntime..."
pip3 install onnxruntime --quiet
echo "onnxruntime: $(python3 -c 'import onnxruntime; print(onnxruntime.__version__)')"

# 2. Copy CPU model to /home/ubuntu/
MODEL_SRC="$SCRIPT_DIR/models/yolov3-10.onnx"
MODEL_DST="/home/ubuntu/yolov3-10.onnx"
if [ -f "$MODEL_SRC" ]; then
    echo "[2/3] Copying yolov3-10.onnx to /home/ubuntu/ (237MB)..."
    cp "$MODEL_SRC" "$MODEL_DST"
    echo "Done ($(du -h $MODEL_DST | cut -f1))"
else
    echo "[2/3] WARNING: models/yolov3-10.onnx not found"
    echo "      Download from: https://github.com/onnx/models/blob/main/validated/vision/object_detection_segmentation/yolov3/model/yolov3-10.onnx"
    echo "      Click 'Download raw file' in browser, save to yolov3/models/"
fi

# 3. Verify DPU xmodel
XMODEL_PYNQ="/root/jupyter_notebooks/pynq-dpu/tf_yolov3_voc.xmodel"
XMODEL_LOCAL="$SCRIPT_DIR/models/tf_yolov3_voc.xmodel"
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
echo "DPU: open dpu_bench.ipynb  (expected: ~14.7 FPS, ~1.51 FPS/Watt)"
echo "CPU: open cpu_bench.ipynb  (expected: ~0.22 FPS, ~0.03 FPS/Watt — WARNING: slow, board runs hot)"
echo "DPU advantage: 50x more energy efficient"
