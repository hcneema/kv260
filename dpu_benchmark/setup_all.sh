#!/bin/bash
# Master Setup Script — KV260 CPU vs DPU Benchmark Suite
# Run this once on a fresh KV260 with Kria-PYNQ already installed.
# Usage: cd /home/ubuntu/dpu_benchmark && bash setup_all.sh
#
# Prerequisites:
#   1. Ubuntu 22.04 on KV260
#   2. Kria-PYNQ installed (see SETUP.md Step 5)
#   3. This entire dpu_benchmark/ folder copied to the board

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "========================================"
echo " KV260 DPU Benchmark Suite — Setup"
echo "========================================"
echo "Running from: $SCRIPT_DIR"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check pynq_dpu
source /etc/profile.d/pynq_venv.sh 2>/dev/null || true
python3 -c "from pynq_dpu import DpuOverlay; print('pynq_dpu: OK')" 2>/dev/null || {
    echo "ERROR: pynq_dpu not found."
    echo "Install Kria-PYNQ first: sudo bash /home/ubuntu/Kria-PYNQ/install.sh -b KV260"
    exit 1
}

# Check power sensor
cat /sys/class/hwmon/hwmon2/power1_input > /dev/null 2>&1 || {
    echo "ERROR: Power sensor not found at /sys/class/hwmon/hwmon2/power1_input"
    exit 1
}
echo "Power sensor: OK ($(cat /sys/class/hwmon/hwmon2/power1_input | awk '{printf "%.2f W", $1/1000000}'))"

# Check DPU xmodels — accept either local models/ or pynq install location
check_xmodel() {
    local name="$1"
    local local_path="$SCRIPT_DIR/$2"
    local pynq_path="$3"
    if [ -f "$local_path" ]; then
        echo "xmodel OK (local): $name"
    elif [ -f "$pynq_path" ]; then
        echo "xmodel OK (pynq): $name"
    else
        echo "ERROR: $name not found in models/ or pynq — is Kria-PYNQ installed?"
        exit 1
    fi
}
check_xmodel "dpu_resnet50.xmodel"      "resnet50/models/dpu_resnet50.xmodel"      "/root/jupyter_notebooks/pynq-dpu/dpu_resnet50.xmodel"
check_xmodel "tf_yolov3_voc.xmodel"     "yolov3/models/tf_yolov3_voc.xmodel"       "/root/jupyter_notebooks/pynq-dpu/tf_yolov3_voc.xmodel"
check_xmodel "dpu_tf_inceptionv1.xmodel" "inceptionv1/models/dpu_tf_inceptionv1.xmodel" "/root/jupyter_notebooks/pynq-dpu/dpu_tf_inceptionv1.xmodel"

# Install onnxruntime
echo ""
echo "Installing onnxruntime..."
pip3 install onnxruntime --quiet
echo "onnxruntime: $(python3 -c 'import onnxruntime; print(onnxruntime.__version__)')"

# Copy ONNX models from models/ directories to /home/ubuntu/
echo ""
echo "Copying CPU benchmark models to /home/ubuntu/..."

for ENTRY in \
    "$SCRIPT_DIR/resnet50/models/resnet50-v1-7.onnx:/home/ubuntu/resnet50-v1-7.onnx" \
    "$SCRIPT_DIR/yolov3/models/yolov3-10.onnx:/home/ubuntu/yolov3-10.onnx" \
    "$SCRIPT_DIR/inceptionv1/models/inception-v1-9.onnx:/home/ubuntu/inception-v1-9.onnx"; do
    SRC="${ENTRY%%:*}"
    DST="${ENTRY##*:}"
    NAME="$(basename $SRC)"
    if [ -f "$SRC" ]; then
        if [ -f "$DST" ] && [ $(stat -c%s "$DST") -eq $(stat -c%s "$SRC") ]; then
            echo "$NAME: already in place ($(du -h $DST | cut -f1))"
        else
            echo "Copying $NAME ($(du -h $SRC | cut -f1))..."
            cp "$SRC" "$DST"
            echo "Done!"
        fi
    else
        echo "WARNING: $SRC not found — $NAME will not be available for CPU benchmark"
    fi
done

echo ""
echo "========================================"
echo " Setup Complete!"
echo "========================================"
echo ""
echo "Open Jupyter at: http://$(hostname -I | awk '{print $1}'):9090/lab"
echo "Password: xilinx"
echo ""
echo "Run notebooks in this order:"
echo "  1. resnet50/dpu_bench.ipynb     DPU ~92 FPS,   10.56 FPS/W"
echo "  2. resnet50/cpu_bench.ipynb     CPU ~1.6 FPS,   0.37 FPS/W  -> 29x advantage"
echo "  3. yolov3/dpu_bench.ipynb       DPU ~14.7 FPS,  1.51 FPS/W"
echo "  4. yolov3/cpu_bench.ipynb       CPU ~0.22 FPS,  0.03 FPS/W  -> 50x advantage (slow!)"
echo "  5. inceptionv1/dpu_bench.ipynb  DPU ~217 FPS,  27.44 FPS/W"
echo "  6. inceptionv1/cpu_bench.ipynb  CPU ~3.86 FPS,  0.92 FPS/W  -> 30x advantage"
