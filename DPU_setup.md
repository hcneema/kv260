# KV260 DPU Setup Guide
**Time to complete: ~45 minutes** (we took 7+ hours figuring this out so you don't have to)

---

## Overview
This guide gets DPU inference working on AMD Kria KV260 running Ubuntu 22.04.
The key insight: **do NOT use `apt install vitis-ai-runtime`** — it is broken on Ubuntu 22.04's 2024 kernel. Use Kria-PYNQ instead.

After completing Steps 1-7, run `setup_all.sh` to automate the rest.

---

## Step 1 — Flash Ubuntu 22.04

**Image used (confirmed working):**
```
iot-limerick-classic-desktop-2204-20240304-165.img
```
Available in Google Drive (kv260 folder). Also downloadable from https://ubuntu.com/download/amd (scroll to bottom, KV260, Ubuntu 22.04).

**Flash with Win32DiskImager (Windows) — confirmed working:**
1. Download and open Win32DiskImager
2. Click the folder icon, select the `.img` file
3. Select the SD card drive letter (be careful — wrong drive = data loss)
4. Click **Write**, wait ~5-10 minutes

> Do NOT use Etcher — it crashes at 99% on large images.
> Do NOT use `dd` on Windows Git Bash — path resolution is unreliable.

---

## Step 2 — First Boot

- Insert microSD, connect Ethernet **directly to your router** (not to your PC — Windows ICS does not NAT TCP reliably)
- Connect HDMI monitor and USB keyboard to the KV260
- Power on, wait 3-5 minutes (first boot resizes filesystem)
- Log in: `ubuntu` / `ubuntu` — it immediately forces a password change

---

## Step 3 — Enable SSH (do this first, on the monitor)

```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

Find the board IP: `ip addr show` or check your router's DHCP client list (device named `kria`).

Now disconnect the monitor/keyboard — use SSH for everything else.

> SSH is NOT enabled by default on the fresh image. You must do this step on the monitor before SSH works.

---

## Step 4 — WiFi (if using USB WiFi adapter)

For **Realtek RTL88x2bu** (AC1200 Techkey — confirmed working):
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

### Set Static IP (strongly recommended)
```bash
sudo nmcli connection modify "YourWiFiSSID" \
    ipv4.method manual \
    ipv4.addresses 192.168.68.60/22 \
    ipv4.gateway 192.168.68.1 \
    ipv4.dns "8.8.8.8 8.8.4.4"
sudo nmcli connection up "YourWiFiSSID"
```

---

## Step 5 — Lock XRT (do this before any apt operations)

XRT 2.13.466 is the version that works with Kria-PYNQ. If apt upgrades it, the kernel/userspace versions diverge and zocl stops working — requiring a full SD card reflash to fix.

```bash
sudo apt-mark hold xrt
sudo systemctl disable --now unattended-upgrades
sudo apt-get remove -y unattended-upgrades
```

> **This step is critical.** We lost a full working board by skipping it. `setup_all.sh` also does this, but do it manually now before anything touches apt.

---

## Step 6 — Install Kria-PYNQ (~25 minutes)

**Must be run from an interactive SSH session — not via piped sudo.**

```bash
git clone https://github.com/hcneema/Kria-PYNQ /home/ubuntu/Kria-PYNQ
cd /home/ubuntu/Kria-PYNQ
sudo bash install.sh -b KV260
```

Use the fork (`hcneema/Kria-PYNQ`) — AMD may remove or change the original.

This installs:
- PYNQ 3.0.1 with pre-built aarch64 binaries
- pynq-dpu 2.5.1
- JupyterLab on port 9090 (password: `xilinx`)
- XRT runtime
- Sample DPU notebooks at `/root/jupyter_notebooks/pynq-dpu/`

> **Why interactive SSH matters:** `install.sh` applies the pynq device tree overlay (zocl) as part of setup. This step silently skips when run via `echo pass | sudo -S`. `setup_all.sh` detects and fixes this, but better to get it right the first time.

> **Do NOT** use `pip install pynq-dpu` directly — it misses the overlay files and device tree setup.

**Reboot after install:**
```bash
sudo reboot
# wait 60s, then verify:
cat /proc/meminfo | grep CmaFree   # must be >500000 kB before running DPU
```

---

## Step 7 — Copy and Run setup_all.sh

From your PC:
```bash
scp -r dpu_benchmark/ ubuntu@<board-ip>:/home/ubuntu/
```

On the board:
```bash
cd /home/ubuntu/dpu_benchmark
bash setup_all.sh
```

`setup_all.sh` handles everything else automatically:
- Locks XRT and disables auto-updates (belt-and-suspenders with Step 5)
- Applies pynq device tree overlay (zocl) if install.sh missed it
- Creates `pynq-dtbo` systemd service so zocl persists across reboots
- Installs onnxruntime into pynq venv
- Fixes Jupyter kernel.json to use pynq venv python
- Creates Jupyter symlink for dpu_benchmark
- Installs 88x2bu WiFi driver if not already installed
- Configures WiFi from `shared/wifi.nmconnection` (see note below)
- Downloads MNIST dataset

> **WiFi note:** `shared/wifi.nmconnection` is gitignored (contains your password). Copy it back from the previous board or recreate it. If missing, `setup_all.sh` warns and skips WiFi config — set it up manually with `nmtui`.

---

## Step 8 — Sanity Checks

```bash
# 1. pynq_dpu installed?
source /etc/profile.d/pynq_venv.sh
python3 -c "from pynq_dpu import DpuOverlay; print('pynq_dpu OK')"

# 2. zocl device tree overlay applied?
cat /sys/kernel/config/device-tree/overlays/pynq/status   # must say: applied
ls /dev/dri/   # must include renderD128

# 3. Power sensor working?
cat /sys/class/hwmon/hwmon2/power1_input   # expected: 4000000-6000000 (µW)

# 4. CMA healthy?
cat /proc/meminfo | grep CmaFree   # must be >500000 kB
```

---

## Step 9 — Run DPU Inference

Open Jupyter at `http://<board-ip>:9090/lab` (password: `xilinx`).

Or run directly from SSH:
```bash
source /etc/profile.d/pynq_venv.sh
sudo -E /usr/local/share/pynq-venv/bin/python3 /home/ubuntu/dpu_benchmark/resnet50/dpu_bench.py
```

Expected ResNet50 results: **~96 FPS, ~8.2W, ~11.8 FPS/W**

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

### Compile for B4096 (on x86 PC)
```bash
docker pull xilinx/vitis-ai-cpu:latest
# Inside the container:
vai_c_xir \
  -x quantized_model.xmodel \
  -a /opt/vitis_ai/compiler/arch/DPUCZDX8G/KV260/arch.json \
  -n my_model_b4096 \
  -o ./compiled/
scp compiled/my_model_b4096.xmodel ubuntu@192.168.68.60:/home/ubuntu/
```

### Runtime Options on KV260
| Option | Status | Notes |
|---|---|---|
| **PYNQ** | ✅ Working | What we use — Python-first, Jupyter, pre-built binaries |
| **VART (apt vitis-ai-runtime)** | ❌ Broken | ABI mismatch on kernel 5.15.0-1027 — SIGSEGV |
| **Vitis AI Docker on KV260** | 🤔 Possible | Heavy, not ideal on 4GB RAM |
| **ONNX Runtime + VOE** | 🔬 Untested | Alternative path, worth trying in future |

### How DpuOverlay finds dpu.bit
When a notebook calls `DpuOverlay("dpu.bit")`, PYNQ resolves it from the pynq-dpu package:
```
/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/dpu.bit
```
This is the B512 DPU bitstream bundled with pynq-dpu 2.5.1.

Pre-compiled models for B4096: https://github.com/Xilinx/Vitis-AI/tree/master/model_zoo

---

## Critical Gotchas (what cost us 7+ hours)

### NEVER upgrade XRT — it will brick the DPU
XRT 2.13.466 is the exact version that works. If apt upgrades it, the zocl kernel module version mismatches the userspace — DpuOverlay hangs or ENODEV. The only fix is a full SD card reflash.

```bash
# Lock it immediately:
sudo apt-mark hold xrt
# Verify it's locked:
apt-mark showhold   # should show: xrt
```

### "Programming Device failed: ENODEV" — pynq dtbo not applied
`DpuOverlay("dpu.bit")` fails with ENODEV if the zocl device tree overlay wasn't applied on boot.

**Symptoms:**
```bash
lsmod | grep zocl       # zocl loaded but...
ls /dev/dri/            # renderD128 missing (only card0)
```

**Fix:**
```bash
sudo dtc -I dts -O dtb -o /tmp/pynq.dtbo /home/ubuntu/Kria-PYNQ/dts/pynq.dts
sudo cp /tmp/pynq.dtbo /lib/firmware/pynq.dtbo
sudo mkdir -p /sys/kernel/config/device-tree/overlays/pynq
echo -n pynq.dtbo | sudo tee /sys/kernel/config/device-tree/overlays/pynq/path
```

Or just run `setup_all.sh` — it detects and fixes this automatically.

### DO NOT use apt vitis-ai-runtime
```bash
# DO NOT DO THIS — crashes with SIGSEGV on kernel 5.15.0-1027:
sudo apt install vitis-ai-runtime
```

### DO NOT repeatedly retry xmutil loadapp
Each failed attempt leaks CMA memory. After ~5 attempts CMA is exhausted. **Only fix: reboot.**

```bash
cat /proc/meminfo | grep CmaFree   # must be >500000 kB before any DPU run
```

### DpuOverlay() hangs — another process holds the DPU
Only one process can use the DPU at a time. The hang message is:
```
waiting for process to release the resource: DPU_0
```
Fix:
```bash
sudo fuser /dev/dri/renderD128        # find the PID
sudo kill -9 <pid>                    # kill it
# or nuke all Jupyter kernels:
sudo systemctl restart jupyter
```

### Kria-PYNQ install must use interactive sudo
Running `echo pass | sudo -S bash install.sh` silently skips the device tree overlay step.
Always SSH in interactively and run `sudo bash install.sh -b KV260` directly.

### Running DPU from .py files (not just Jupyter)
You do NOT need Jupyter. Scripts work fine from SSH with the right invocation:
```bash
source /etc/profile.d/pynq_venv.sh
sudo -E /usr/local/share/pynq-venv/bin/python3 your_script.py
```
Requirements: pynq venv python, XILINX_XRT set (from source), run as root (DRI access).

### SSH "Offending key" after re-flashing
After reflashing the board gets a new host key. Fix:
```bash
sed -i '/192.168.68.60/d' ~/.ssh/known_hosts
ssh-keyscan 192.168.68.60 >> ~/.ssh/known_hosts
```

### apt-get update hangs on IPv6
```bash
sudo apt-get -o Acquire::ForceIPv4=true update
```

---

## Benchmark Results (KV260 revB, Ubuntu 22.04.4, kernel 5.15.0-1027)

**CNN Inference — CPU vs DPU (B512 via pynq-dpu):**

| Model | FPS | Latency | Power | FPS/W | vs CPU |
|---|---|---|---|---|---|
| ResNet50 (DPU) | 96.4 | 10.4 ms | 8.16 W | 11.81 | **32x** |
| ResNet50 (CPU) | ~1.6 | ~625 ms | ~4.3 W | ~0.37 | — |
| YOLOv3 (DPU) | 14.7 | 68.0 ms | 9.66 W | 1.52 | **50x** |
| YOLOv3 (CPU) | ~0.22 | ~4.5 s | ~7.3 W | ~0.03 | — |
| InceptionV1 (DPU) | 218.8 | 4.6 ms | 7.94 W | 27.55 | **30x** |
| InceptionV1 (CPU) | ~3.86 | ~259 ms | ~4.2 W | ~0.92 | — |

---

## Software Versions (confirmed working — do not upgrade)

| Software | Version |
|---|---|
| Ubuntu | 22.04.4 LTS |
| Kernel | 5.15.0-1027-xilinx-zynqmp |
| XRT | 2.13.479-0ubuntu2 ← locked with apt-mark hold |
| PYNQ | 3.0.1 |
| pynq-dpu | 2.5.1 |
| ONNX Runtime | 1.23.2 |
| Kria-PYNQ | 3.0 |

---

## Repos to Fork (in case they go offline)

| Repo | Fork (use this) | Why |
|---|---|---|
| Kria-PYNQ | https://github.com/hcneema/Kria-PYNQ | Critical — install script + pre-built pynq-dpu binaries for KV260 |
| WiFi driver | https://github.com/hcneema/88x2bu-20210702 | RTL88x2bu driver for USB WiFi adapter |
| kv260-ubuntu-test | https://github.com/hcneema/kv260-ubuntu-test | Working reference — dpu.bit, pre-compiled xmodels, working Python for Ubuntu 22.04 |

> Try the original first. If unavailable, use the fork.

---

## Reference Links
- Kria-PYNQ (original): https://github.com/Xilinx/Kria-PYNQ
- pynq-dpu notebooks: `/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/notebooks/`
- Full benchmark suite: `dpu_benchmark/` directory (see `dpu_benchmark/SETUP.md`)
