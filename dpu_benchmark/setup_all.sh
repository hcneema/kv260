#!/bin/bash
# Master Setup Script — KV260 CPU vs DPU Benchmark Suite
# Run this once on a fresh KV260 with Kria-PYNQ already installed.
# Usage: cd /home/ubuntu/dpu_benchmark && bash setup_all.sh
#
# Prerequisites:
#   1. Ubuntu 22.04 on KV260
#   2. Kria-PYNQ installed (see SETUP.md Step 5)
#   3. This entire dpu_benchmark/ folder copied to the board
#   4. Board rebooted after Kria-PYNQ install (CmaFree must be >500MB)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "========================================"
echo " KV260 DPU Benchmark Suite — Setup"
echo "========================================"
echo "Running from: $SCRIPT_DIR"
echo ""

# === STEP 0: Disable auto-updates and lock XRT (MUST BE FIRST) ===
echo "Disabling auto-updates..."
sudo systemctl disable --now unattended-upgrades 2>/dev/null || true
sudo apt-get remove -y unattended-upgrades 2>/dev/null || true
sudo apt-mark hold xrt 2>/dev/null || true
echo "Auto-updates: disabled, XRT: locked at $(dpkg -l xrt 2>/dev/null | awk '/^ii/{print $3}' || echo 'unknown')"
echo ""

# Fix CRLF line endings (scripts edited on Windows break bash)
echo "Fixing line endings in shell scripts..."
find "$SCRIPT_DIR" -name "*.sh" -exec sed -i "s/\r//" {} \;
echo "Done."
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check pynq_dpu — must source pynq_venv.sh first (sets BOARD, XILINX_XRT, activates venv)
source /etc/profile.d/pynq_venv.sh 2>/dev/null || true
/usr/local/share/pynq-venv/bin/python3 -c "from pynq_dpu import DpuOverlay; print('pynq_dpu: OK')" 2>/dev/null || {
    echo "pynq_dpu not found — installing now..."
    sudo bash -c 'source /etc/profile.d/pynq_venv.sh && python3 -m pip install pynq-dpu==2.5 --no-build-isolation -q'
    /usr/local/share/pynq-venv/bin/python3 -c "from pynq_dpu import DpuOverlay; print('pynq_dpu: OK')" 2>/dev/null || {
        echo "ERROR: pynq_dpu install failed. Install Kria-PYNQ first: sudo bash /home/ubuntu/Kria-PYNQ/install.sh -b KV260"
        exit 1
    }
}

# Check power sensor
cat /sys/class/hwmon/hwmon2/power1_input > /dev/null 2>&1 || {
    echo "ERROR: Power sensor not found at /sys/class/hwmon/hwmon2/power1_input"
    exit 1
}
echo "Power sensor: OK ($(cat /sys/class/hwmon/hwmon2/power1_input | awk '{printf "%.2f W", $1/1000000}'))"

# Check CMA memory (must be >500MB before DPU can run)
CMA_FREE=$(grep CmaFree /proc/meminfo | awk '{print $2}')
if [ "$CMA_FREE" -lt 500000 ]; then
    echo "WARNING: CmaFree is only ${CMA_FREE} kB (need >500000 kB)"
    echo "Reboot the board before running any DPU notebooks."
else
    echo "CmaFree: OK (${CMA_FREE} kB)"
fi

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

# Check / copy dpu.xclbin (required by DpuOverlay alongside dpu.bit)
XCLBIN_LOCAL="$SCRIPT_DIR/shared/dpu.xclbin"
XCLBIN_PYNQ="/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/dpu.xclbin"
if [ -f "$XCLBIN_LOCAL" ]; then
    echo "dpu.xclbin: OK (local)"
elif [ -f "$XCLBIN_PYNQ" ]; then
    echo "dpu.xclbin: copying from pynq install..."
    cp "$XCLBIN_PYNQ" "$XCLBIN_LOCAL"
    echo "dpu.xclbin: OK"
else
    echo "WARNING: dpu.xclbin not found — DpuOverlay will fail. Reinstall Kria-PYNQ."
fi

# Install onnxruntime into pynq venv (not user-local — Jupyter won't see ~/.local)
echo ""
echo "Installing onnxruntime into pynq venv..."
sudo /usr/local/share/pynq-venv/bin/pip3 install onnxruntime \
    --target /usr/local/share/pynq-venv/lib/python3.10/site-packages \
    --quiet 2>/dev/null || pip3 install onnxruntime --quiet
echo "onnxruntime: $(python3 -c 'import onnxruntime; print(onnxruntime.__version__)' 2>/dev/null || echo 'installed')"

# Fix Jupyter kernel.json to use pynq venv python (not system python)
echo ""
echo "Fixing Jupyter kernel.json..."
KERNEL_JSON="/usr/local/share/pynq-venv/share/jupyter/kernels/python3/kernel.json"
if [ -f "$KERNEL_JSON" ]; then
    CURRENT_PYTHON=$(python3 -c "import json; d=json.load(open('$KERNEL_JSON')); print(d['argv'][0])" 2>/dev/null || echo "")
    if [ "$CURRENT_PYTHON" != "/usr/local/share/pynq-venv/bin/python3" ]; then
        sudo bash -c "cat > $KERNEL_JSON << 'KEOF'
{
 \"argv\": [
  \"/usr/local/share/pynq-venv/bin/python3\",
  \"-m\",
  \"ipykernel_launcher\",
  \"-f\",
  \"{connection_file}\"
 ],
 \"display_name\": \"Python 3 (ipykernel)\",
 \"language\": \"python\",
 \"metadata\": {\"debugger\": true}
}
KEOF"
        sudo systemctl restart jupyter
        echo "kernel.json: fixed and Jupyter restarted"
    else
        echo "kernel.json: already correct"
    fi
else
    echo "kernel.json: not found (skipping)"
fi

# Create Jupyter symlink so dpu_benchmark appears in the file browser
echo ""
echo "Creating Jupyter symlink..."
JUPYTER_LINK="/root/jupyter_notebooks/dpu_benchmark"
if [ ! -e "$JUPYTER_LINK" ]; then
    sudo ln -s "$SCRIPT_DIR" "$JUPYTER_LINK"
    echo "Symlink created: $JUPYTER_LINK -> $SCRIPT_DIR"
else
    echo "Symlink: already exists"
fi

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
echo "IMPORTANT: Run 'sudo reboot' now to activate WiFi driver."
echo "After reboot, unplug Ethernet — board will be at 192.168.68.60 via WiFi."
echo ""
echo "Open Jupyter at: http://$(hostname -I | awk '{print $1}'):9090/tree"
echo "Password: xilinx"
echo ""
echo "Run notebooks in this order:"
echo "  1. resnet50/dpu_bench.ipynb     DPU ~96 FPS,   11.84 FPS/W"
echo "  2. resnet50/cpu_bench.ipynb     CPU ~1.6 FPS,   0.37 FPS/W  -> 32x advantage"
echo "  3. yolov3/dpu_bench.ipynb       DPU ~14.7 FPS,  1.51 FPS/W"
echo "  4. yolov3/cpu_bench.ipynb       CPU ~0.22 FPS,  0.03 FPS/W  -> 50x advantage (slow!)"
echo "  5. inceptionv1/dpu_bench.ipynb  DPU ~217 FPS,  27.44 FPS/W"
echo "  6. inceptionv1/cpu_bench.ipynb  CPU ~3.86 FPS,  0.92 FPS/W  -> 30x advantage"
echo ""
echo "Before each DPU notebook, check CMA:"
echo "  cat /proc/meminfo | grep CmaFree   # must be >500000 kB"
echo "  If low: sudo reboot, wait 60s, re-open Jupyter"

# MNIST dataset (downloaded separately — too large for git)
echo ""
echo "Downloading MNIST dataset (from Google mirror)..."
python3 << 'PYEOF'
import urllib.request, os
base = "https://storage.googleapis.com/cvdf-datasets/mnist/"
files = ["train-images-idx3-ubyte.gz","train-labels-idx1-ubyte.gz","t10k-images-idx3-ubyte.gz","t10k-labels-idx1-ubyte.gz"]
data_dir = "/home/ubuntu/mnist_data"
os.makedirs(data_dir, exist_ok=True)
for f in files:
    dest = os.path.join(data_dir, f)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  Cached: {f}")
    else:
        print(f"  Downloading {f}...", flush=True)
        urllib.request.urlretrieve(base + f, dest)
PYEOF

# Copy MNIST ONNX model
cp "$SCRIPT_DIR/mnist/models/mnist-12.onnx" /home/ubuntu/ 2>/dev/null && echo "mnist-12.onnx copied" || true

# === WiFi Driver (88x2bu for USB WiFi adapter) ===
echo ""
echo "Installing 88x2bu WiFi driver..."
if lsmod | grep -q 88x2bu || find /lib/modules -name "88x2bu.ko" 2>/dev/null | grep -q .; then
    echo "88x2bu: already installed"
else
    sudo apt-get install -y dkms git build-essential bc > /dev/null 2>&1
    git clone https://github.com/morrownr/88x2bu-20210702.git /tmp/88x2bu-src 2>/dev/null || \
        (cd /tmp/88x2bu-src && git pull)
    cd /tmp/88x2bu-src
    sudo ./install-driver.sh NoPrompt
    cd "$SCRIPT_DIR"
    echo "88x2bu: installed (active after reboot)"
fi

# === Configure WiFi static IP ===
echo ""
echo "Configuring WiFi static IP..."
WIFI_CONN_SRC="$SCRIPT_DIR/shared/wifi.nmconnection"
WIFI_CONN_DST="/etc/NetworkManager/system-connections"
if [ -d "$WIFI_CONN_DST" ] && ls "$WIFI_CONN_DST"/*.nmconnection 2>/dev/null | grep -q .; then
    echo "WiFi: connection already configured"
elif [ -f "$WIFI_CONN_SRC" ]; then
    CONN_NAME=$(grep "^id=" "$WIFI_CONN_SRC" | cut -d= -f2)
    sudo cp "$WIFI_CONN_SRC" "$WIFI_CONN_DST/${CONN_NAME}.nmconnection"
    sudo chmod 600 "$WIFI_CONN_DST/${CONN_NAME}.nmconnection"
    sudo chown root:root "$WIFI_CONN_DST/${CONN_NAME}.nmconnection"
    sudo nmcli connection reload 2>/dev/null || true
    echo "WiFi: configured from shared/wifi.nmconnection (static IP 192.168.68.60)"
else
    echo "WARNING: shared/wifi.nmconnection not found — WiFi not configured"
    echo "  Copy your NM connection file to shared/wifi.nmconnection and re-run"
fi
