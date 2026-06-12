# KV260 DPU Setup Guide
**Time to complete: ~45 minutes** (we took 7+ hours figuring this out so you don't have to)

---

## Overview
This guide gets DPU inference working on AMD Kria KV260 running Ubuntu 22.04.
The key insight: **do NOT use `apt install vitis-ai-runtime`** — it is broken on Ubuntu 22.04's 2024 kernel. Use Kria-PYNQ instead.

---

## Step 1 — Flash Ubuntu 22.04
Download the image from https://ubuntu.com/download/amd (scroll to bottom, pick KV260 Ubuntu 22.04).

**Flash with dd, NOT Etcher** (Etcher crashes at 99% on large images).

**Step 1a — Find your microSD device** (run as Administrator in Git Bash):
```bash
cat /proc/partitions
# Look for a ~59GB device — typically /dev/sdb on Windows Git Bash
# Example output:
#   8     0 500107608 sda              <- your internal Windows SSD
#   8     3 494466048 sda3   C:\       <- Windows C: drive
#   8    16  61069312 sdb              <- this is the microSD (59GB)
#   8    17   1048576 sdb1   D:\       <- partition on microSD
# Use /dev/sdb (the whole device, NOT sdb1 or sdb2)
```
**Double-check the device letter** — writing to the wrong device destroys its contents.

**Step 1b — Flash the image:**
```bash
# Replace /dev/sdb with your actual device from above
xz -dc /path/to/iot-limerick-kria-classic-desktop-2204-*.img.xz | dd of=/dev/sdb bs=4M status=progress
sync
```
Takes 15-20 minutes. Do not remove the card until `sync` completes.

---

## Step 2 — First Boot
- Insert microSD, connect Ethernet to your router, power on
- First boot takes 3-5 minutes (resizes filesystem)
- Connect keyboard+monitor, login: `ubuntu` / `ubuntu`, set new password
- Find IP: `ip addr show` or check router's DHCP list

---

## Step 3 — Enable SSH (do this first!)
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```
Now you can use SSH for everything else. Disconnect monitor/keyboard.

---

## Step 4 — WiFi (if using USB WiFi adapter)
If you have a **Realtek RTL88x2bu** adapter (AC1200 Techkey):
```bash
sudo apt install -y dkms git build-essential
git clone https://github.com/morrownr/88x2bu-20210702.git
cd 88x2bu-20210702
sudo ./install-driver.sh    # say N to options, Y to reboot
```
After reboot, configure WiFi:
```bash
sudo nmtui    # Activate a connection → pick your network → enter password
```

### Set Static IP (strongly recommended — prevents IP changing on every reboot)
```bash
# Replace "YourWiFiName" with your actual SSID
sudo nmcli connection modify "YourWiFiName" \
    ipv4.method manual \
    ipv4.addresses 192.168.68.60/22 \
    ipv4.gateway 192.168.68.1 \
    ipv4.dns "8.8.8.8 8.8.4.4"
sudo nmcli connection up "YourWiFiName"
```
Verify: `ip addr show` should show `192.168.68.60`.

---

## Step 5 — Add Required APT Repos
```bash
sudo add-apt-repository -y ppa:xilinx-apps/ppa
sudo apt update
```

---

## Step 6 — Install DPU Firmware (optional)
The benchmark suite uses **B512** (from `dpu.bit` bundled in Kria-PYNQ) — no extra firmware needed.

Only install this if you want to test B4096 (larger/faster DPU config):
```bash
sudo add-apt-repository -y ppa:xilinx-apps/ppa
sudo apt update
sudo apt install -y xlnx-firmware-kv260-benchmark-b4096
```
This installs the B4096 DPU bitstream to `/lib/firmware/xilinx/kv260-benchmark-b4096/`.

> **B512 vs B4096**: B512 is what all our confirmed benchmarks use (29-50x CPU advantage). B4096 is theoretically 5x faster but requires xmodels compiled specifically for it.

---

## Step 7 — Install Kria-PYNQ (the key step — ~25 minutes)
```bash
git clone https://github.com/Xilinx/Kria-PYNQ /home/ubuntu/Kria-PYNQ
cd /home/ubuntu/Kria-PYNQ
sudo bash install.sh -b KV260
```
This installs:
- PYNQ 3.0 with pre-built binaries (no compilation needed)
- pynq-dpu 2.5.1
- JupyterLab at port 9090
- XRT runtime
- Sample DPU notebooks

> **Do NOT** use `pip install pynq-dpu` directly — it tries to compile from source and fails with missing Xilinx headers.

---

## Step 8 — Create DPU Load Script
Save this as `/home/ubuntu/setup_dpu.sh`:
```bash
#!/bin/bash
# Run this script with: sudo bash /home/ubuntu/setup_dpu.sh
sleep 2
xmutil unloadapp 2>/dev/null
xmutil loadapp kv260-benchmark-b4096
sleep 2
xbutil program -d 0 -u /lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin
chmod 666 /dev/dri/renderD128 /dev/dri/card0 /dev/dri/card1
chmod 666 /dev/dma_heap/reserved /dev/dma_heap/system
chmod 666 /dev/ttyACM0 /dev/video0 /dev/video1 2>/dev/null
```
```bash
chmod +x /home/ubuntu/setup_dpu.sh
```

---

## Step 9 — Every Time You Reboot
```bash
# Load DPU — run ONCE only, do NOT retry if it fails (reboot instead)
sudo bash /home/ubuntu/setup_dpu.sh
```
Expected output:
```
remove from slot 0 returns: 0 (Ok)     <- or -1 (Error) on fresh boot — both are fine
kv260-benchmark-b4096: loaded to slot 0
INFO: Found total 1 card(s), 1 are usable
INFO: xbutil program succeeded on 0000:00:00.0
```
> The `remove from slot 0 returns: -1 (Error)` on first run after reboot is normal — there is nothing to unload yet.

Then run the sanity checks in Step 10 before doing anything else.

---

## Step 10 — Sanity Check Before Running Anything

Run these in order. Each one confirms a layer is working before trusting the next.

**Check 1 — pynq_dpu is installed correctly (import only, no hardware)**
```bash
source /etc/profile.d/pynq_venv.sh
python3 -c "from pynq_dpu import DpuOverlay; print('pynq_dpu OK')"
```
Expected: `pynq_dpu OK`
If this fails, Kria-PYNQ install didn't complete — re-run `sudo bash install.sh -b KV260`.
> This is safe to run in SSH terminal — it's only an import, no hardware access yet.

**Check 2 — DPU firmware is loaded**
```bash
cat /sys/bus/platform/devices/axi:zyxclmm_drm/kds_numcus
```
Expected: `1`
If you get `0` or "no such file" — run `sudo bash /home/ubuntu/setup_dpu.sh` first.

**Check 3 — CMA memory is healthy**
```bash
cat /proc/meminfo | grep Cma
```
Expected: `CmaFree` > 500000 kB (500MB)
If CmaFree is low — reboot and try again. Do NOT proceed if CmaFree < 500MB.

**Check 4 — xbutil can see the device**
```bash
sudo xbutil examine 2>&1 | grep "Device Ready"
```
Expected: `Yes`

Only proceed to Step 11 if all 4 checks pass.

---

## Step 11 — Run DPU Inference
Open this URL directly in your browser (replace IP with your board's IP):
```
http://192.168.68.60:9090/lab/tree/pynq-dpu/dpu_yolov3.ipynb
```
Password: **`xilinx`**

> The `pynq-dpu/` folder in Jupyter is NOT the Kria-PYNQ git clone. It is a symlink created by `install.sh` pointing to the notebooks bundled inside the pynq-dpu package at:
> `/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/notebooks/`

Click **"Restart Kernel and Run All Cells"**.

Expected output around cell 22:
```
Number of detected objects: 6
Number of detected objects: 1
Number of detected objects: 2
Number of detected objects: 0
Performance: 6.6421665449261935 FPS
```
> 6.6 FPS is normal — this notebook uses B512 (smallest DPU config) with its own bundled bitstream.

After the notebook finishes, add two verification cells to confirm DPU really ran (press `B` on the last cell to add below):

**Verification Cell 1 — Which DPU is loaded:**
```python
import subprocess
result = subprocess.run(['cat', '/sys/bus/platform/devices/axi:zyxclmm_drm/ip_layout'], capture_output=True)
print(result.stdout.decode('ascii', errors='replace'))
# Expected: some binary + DPUCZDX8G:DPUCZDX8G_1
```

**Verification Cell 2 — How many times DPU was invoked:**
```python
import subprocess
r = subprocess.run(['cat', '/sys/bus/platform/devices/axi:zyxclmm_drm/kds_custat_raw'], capture_output=True)
print(r.stdout.decode('ascii', errors='replace'))
# Expected: 0,0,DPUCZDX8G:DPUCZDX8G_1,0x80010000,0x6,5
# Last number = invocation count. Must be > 0. 0x6 = DONE+IDLE (finished cleanly)
```

Our confirmed output after running on 5 test images:
```
0,0,DPUCZDX8G:DPUCZDX8G_1,0x80010000,0x6,5
```

---

## Step 12 — Using B4096 DPU (faster, for your own models)

The default pynq-dpu notebook uses B512 (6.6 FPS). To use the B4096 firmware we loaded via xmutil, use `download=False` — this tells PYNQ not to reflash the FPGA:

```python
from pynq_dpu import DpuOverlay
import numpy as np, time

# download=False = skip FPGA reprogramming, hook into xmutil-loaded DPU
# Use the absolute path to the B4096 xclbin already loaded by setup_dpu.sh
overlay = DpuOverlay("/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin", download=False)
overlay.load_model("/path/to/your_model.xmodel")  # must be compiled for arch DPUCZDX8G_ISA1_B4096
# Get pre-compiled models from: https://github.com/Xilinx/Vitis-AI/tree/master/model_zoo
# Or compile your own using Vitis AI on an x86 PC with Docker
dpu = overlay.runner

in_t  = dpu.get_input_tensors()
out_t = dpu.get_output_tensors()
in_d  = [np.zeros(t.dims, dtype=np.float32) for t in in_t]
out_d = [np.zeros(t.dims, dtype=np.float32) for t in out_t]

# Warmup run
job = dpu.execute_async(in_d, out_d)
dpu.wait(job)

# Benchmark
N = 50
start = time.time()
for i in range(N):
    job = dpu.execute_async(in_d, out_d)
    dpu.wait(job)
elapsed = time.time() - start
print(f"DPU: {N/elapsed:.1f} FPS, {elapsed/N*1000:.1f} ms/frame")
del overlay
```

> Run this from **Jupyter only** — not bare terminal. Python 3.10 mmap differences cause silent hangs in terminal.

---

## Developing New DPU Models (e.g. latest YOLO)

PYNQ is only the **runtime** on the KV260. Model development happens on a separate x86 PC:

```
1. Train model          → PyTorch / TensorFlow (any machine)
2. Quantize to INT8     → Vitis AI Docker on x86 PC
3. Compile to .xmodel   → target: DPUCZDX8G_ISA1_B4096 (our DPU arch)
4. Copy .xmodel to KV260 → scp model.xmodel ubuntu@192.168.68.60:/home/ubuntu/
5. Run inference        → PYNQ on KV260 loads and runs it
```

### Step 3 — Compile for B4096 (on x86 PC)
```bash
# Pull Vitis AI Docker on your x86 PC
docker pull xilinx/vitis-ai-cpu:latest

# Inside the container, compile your quantized model
vai_c_xir \
  -x quantized_model.xmodel \
  -a /opt/vitis_ai/compiler/arch/DPUCZDX8G/KV260/arch.json \
  -n my_model_b4096 \
  -o ./compiled/

# Copy to KV260
scp compiled/my_model_b4096.xmodel ubuntu@192.168.68.60:/home/ubuntu/
```

### Step 5 — Run on KV260 (via PYNQ in Jupyter)
```python
from pynq_dpu import DpuOverlay
overlay = DpuOverlay("/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin", download=False)
overlay.load_model("/home/ubuntu/my_model_b4096.xmodel")
dpu = overlay.runner
# ... run inference
```

### Runtime Options on KV260 (inference only)
| Option | Status | Notes |
|---|---|---|
| **PYNQ** | ✅ Working | What we use — Python-first, Jupyter, pre-built binaries |
| **VART (apt vitis-ai-runtime)** | ❌ Broken | ABI mismatch on kernel 5.15.0-1027 — SIGSEGV |
| **Vitis AI Docker on KV260** | 🤔 Possible | Heavy, not ideal on 4GB RAM |
| **ONNX Runtime + VOE** | 🔬 Untested | Alternative path, worth trying in future |

### How DpuOverlay finds dpu.bit
When a notebook calls `DpuOverlay("dpu.bit")`, PYNQ does NOT look in the notebook's directory.
It resolves `dpu.bit` from the **pynq-dpu package itself**:
```
/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/dpu.bit
```
This is the B512 DPU bitstream bundled with pynq-dpu 2.5.1. It is always available regardless of which directory the notebook is in.

Some projects (e.g. `kv260-ubuntu-test`) also bundle their own copy of `dpu.bit` in each project folder — when present in the same directory, that local copy takes priority.

**Summary — confirmed md5sums on our board:**
| dpu.bit location | MD5 | Used by | DPU config |
|---|---|---|---|
| pynq-dpu package (default) | `424cfe2e...` | `pynq-dpu/dpu_yolov3.ipynb` etc. | B512 |
| `kv260-ubuntu-test/yolox-test/` | `54ca6df1...` | yolox reference repo | Unknown |
| `kv260-ubuntu-test/stepper-motor/` | `109c7966...` | stepper reference repo | Unknown |
| `kv260-benchmark-b4096.xclbin` | n/a (xclbin not bit) | our `setup_dpu.sh` | B4096 (fastest) |

> Always verify which `dpu.bit` is being used — they are NOT the same file. When a notebook is in a folder with a local `dpu.bit`, that local copy takes priority over the package default.

### Key point
PYNQ is NOT needed for model development — only for running inference on the KV260.
If AMD ever fixes `vitis-ai-runtime` for kernel 5.15.0-1027, native VART could replace PYNQ entirely.

Pre-compiled models for B4096: https://github.com/Xilinx/Vitis-AI/tree/master/model_zoo

---

## Critical Gotchas (what cost us 7 hours)

### DO NOT use apt vitis-ai-runtime
```bash
# DO NOT DO THIS:
sudo apt install vitis-ai-runtime   # crashes with SIGSEGV on kernel 5.15.0-1027
```
The Ubuntu universe package was built for an older kernel ABI. It will always segfault.

### DO NOT repeatedly retry xmutil loadapp
Each failed attempt leaks CMA memory. After ~5 attempts CMA is exhausted and `DpuOverlay()` hangs forever. **Only solution: reboot.**

Check CMA before running Python:
```bash
cat /proc/meminfo | grep Cma   # CmaFree must be >500MB
```

### DO NOT run pynq_dpu from bare terminal
Python 3.10's mmap/C-API differences cause silent infinite hang outside Jupyter.
**Always run from Jupyter** (`kria:9090/lab`).

### DO NOT use download=True (the default) if xmutil already loaded the DPU
PYNQ and xmutil both try to own the FPGA manager — clash causes hang.
Use `DpuOverlay("file", download=False)` or let pynq-dpu's own notebooks handle it.

### Proof DPU actually ran (not CPU fallback)
```bash
# CMA should drop by 200-400MB during inference
cat /proc/meminfo | grep Cma

# DPU compute unit usage counter should be > 0
cat /sys/bus/platform/devices/axi:zyxclmm_drm/kds_custat_raw
# Output: 0,0,DPUCZDX8G:DPUCZDX8G_1,0x80010000,0x6,N  (N = invocation count)
```

See Step 11 for the two verification cells to add inside Jupyter after any notebook run.

---

## Benchmark Results (KV260 revB, Ubuntu 22.04.4, kernel 5.15.0-1027)

**CNN Inference — CPU vs DPU (B512 via pynq-dpu):**

| Model | Task | CPU FPS/W | DPU FPS/W | DPU advantage |
|---|---|---|---|---|
| ResNet50 | Classification | 0.37 | 10.56 | **29x** |
| YOLOv3 | Detection | 0.03 | 1.51 | **50x** |
| InceptionV1 | Classification | 0.92 | 27.44 | **30x** |

**Image Processing — CPU vs FPGA (pynq-helloworld resizer):**

| Task | CPU FPS/W | FPGA FPS/W | FPGA advantage |
|---|---|---|---|
| 4K→1080p resize | 0.79 | 4.27 | **5.4x** |

> Full benchmark suite with all models and scripts: `dpu_benchmark/` directory.

---

## Installed Software Summary
| Software | Version | Location |
|---|---|---|
| XRT | 2.13.466-0ubuntu2 | `/usr/bin/xbutil` |
| xlnx-firmware-kv260-benchmark-b4096 | 0.12-0xlnx2 | `/lib/firmware/xilinx/kv260-benchmark-b4096/` |
| PYNQ | 3.0.1 | `/usr/local/share/pynq-venv/` |
| pynq-dpu | 2.5.1 | inside pynq-venv |
| Jupyter | port 9090 | `http://<ip>:9090/lab` password: xilinx |
| WiFi driver | RTL88x2bu | via morrownr/88x2bu-20210702 dkms |

---

## Reference Links
- Working reference repo: https://github.com/iotengineer22/kv260-ubuntu-test
- Kria-PYNQ: https://github.com/Xilinx/Kria-PYNQ
- pynq-dpu notebooks: `/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/notebooks/`
