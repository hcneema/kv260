# DPU Benchmark Setup Guide
## How to Get a Fresh KV260 Running These Benchmarks

> **This took us 7+ hours to figure out the first time. This guide gets you there in ~45 minutes.**
> For the full board setup guide see: `../../DPU_setup.md` (or `../SETUP.md` for benchmark-specific setup)

---

## Prerequisites

- AMD Kria KV260 revB (or KV260 Vision AI Starter Kit)
- Ubuntu 22.04 microSD card (see Step 1)
- Windows/Mac/Linux PC on the same network
- Internet connection on the board

---

## Step 1 — Flash Ubuntu 22.04

Download from: https://ubuntu.com/download/amd (scroll to bottom, KV260, Ubuntu 22.04)

**Use `dd`, NOT Etcher** (Etcher crashes at 99% on large images):
```bash
# On Windows Git Bash (run as Administrator):
# First find your microSD device:
cat /proc/partitions
# Look for ~59GB device, e.g. /dev/sdb

xz -dc /path/to/iot-limerick-kria-*.img.xz | dd of=/dev/sdb bs=4M status=progress
sync
```

---

## Step 2 — First Boot & SSH

1. Insert microSD, connect Ethernet to router, power on
2. Wait 3-5 minutes (first boot resizes filesystem)
3. Connect keyboard+monitor, login: `ubuntu` / `ubuntu`, set new password
4. Enable SSH:
```bash
sudo systemctl enable ssh && sudo systemctl start ssh
```
5. Find IP: `ip addr show` or check router's DHCP list

---

## Step 3 — WiFi (if using USB adapter)

For **Realtek RTL88x2bu** (AC1200 Techkey — confirmed working):
```bash
sudo apt install -y dkms git build-essential
git clone https://github.com/morrownr/88x2bu-20210702.git
cd 88x2bu-20210702
sudo ./install-driver.sh    # say N to options, Y to reboot
sudo nmtui                  # Activate a connection -> pick network -> enter password
```

---

## Step 4 — Set Static IP (recommended)

```bash
# Replace "YourNetworkName" with your WiFi SSID
sudo nmcli connection modify "YourNetworkName" \
    ipv4.method manual \
    ipv4.addresses 192.168.68.60/22 \
    ipv4.gateway 192.168.68.1 \
    ipv4.dns "8.8.8.8 8.8.4.4"
sudo nmcli connection up "YourNetworkName"
```

---

## Step 5 — Install Kria-PYNQ (~25 minutes)

**This is the critical step.** Do NOT use `pip install pynq-dpu` directly — it fails with missing Xilinx headers.

```bash
git clone https://github.com/Xilinx/Kria-PYNQ /home/ubuntu/Kria-PYNQ
cd /home/ubuntu/Kria-PYNQ
sudo bash install.sh -b KV260
```

**Repo**: https://github.com/Xilinx/Kria-PYNQ  
**Version used**: Kria-PYNQ 3.0 (installs pynq-dpu 2.5.1, PYNQ 3.0.1)

> ⚠️ **Fork this repo** — AMD may remove or change it. The install script downloads pre-built binaries from Xilinx servers. If those go offline, the install will fail.
> Fork at: https://github.com/Xilinx/Kria-PYNQ → click "Fork"

This installs:
- PYNQ 3.0.1 with pre-built aarch64 binaries
- pynq-dpu 2.5.1
- JupyterLab on port 9090 (password: `xilinx`)
- XRT runtime
- Sample DPU notebooks at `/root/jupyter_notebooks/pynq-dpu/`

---

## Step 6 — Add Xilinx APT Repo (optional — not needed for these benchmarks)

These benchmarks use `dpu.bit` (B512) from the Kria-PYNQ package — no additional firmware needed.

The B4096 firmware is only needed if you want to test the larger/faster DPU config:
```bash
sudo add-apt-repository -y ppa:xilinx-apps/ppa
sudo apt update
sudo apt install -y xlnx-firmware-kv260-benchmark-b4096
```

---

## Step 7 — Sanity Checks Before Running Benchmarks

Run these in order — each confirms a layer is working:

```bash
# 1. pynq_dpu installed?
source /etc/profile.d/pynq_venv.sh
python3 -c "from pynq_dpu import DpuOverlay; print('pynq_dpu OK')"

# 2. Power sensor working?
cat /sys/class/hwmon/hwmon2/power1_input
# Expected: ~4000000 to 6000000 (4-6W at idle, in microwatts)

# 3. CMA memory healthy? (MUST be >500MB before running DPU)
cat /proc/meminfo | grep Cma
# Expected: CmaFree > 500000 kB

# 4. Jupyter running?
systemctl is-active jupyter
# Expected: active
```

---

## Step 8 — Copy and Run Benchmarks

```bash
# From your PC:
scp -r dpu_benchmark/ ubuntu@<board-ip>:/home/ubuntu/

# On the board:
cd /home/ubuntu/dpu_benchmark
bash setup_all.sh
```

Then open: `http://<board-ip>:9090/lab` password: `xilinx`

---

## Step 8b — Fix onnxruntime for CPU Notebooks (required)

By default `pip3 install onnxruntime` installs to `~/.local/lib/python3.10/`
(user local) which the pynq venv does **not** include. CPU notebooks will fail
with `ModuleNotFoundError: No module named 'onnxruntime'`.

**Fix — install directly into pynq venv site-packages:**
```bash
sudo /usr/local/share/pynq-venv/bin/pip3 install onnxruntime \
    --target /usr/local/share/pynq-venv/lib/python3.10/site-packages
```

**Also fix the Jupyter kernel to use the full pynq venv python path:**
```bash
sudo tee /usr/local/share/pynq-venv/share/jupyter/kernels/python3/kernel.json << 'EOF'
{
 "argv": [
  "/usr/local/share/pynq-venv/bin/python3",
  "-m",
  "ipykernel_launcher",
  "-f",
  "{connection_file}"
 ],
 "display_name": "Python 3 (ipykernel)",
 "language": "python",
 "metadata": {"debugger": true}
}
EOF
sudo systemctl restart jupyter
```

**Verify it works:**
```python
# Run in any Jupyter notebook cell:
import sys
print(sys.executable)   # should show: /usr/local/share/pynq-venv/bin/python3
import onnxruntime
print(onnxruntime.__version__)   # should show: 1.23.2
```

> **Why this happens**: The default kernel.json uses `python` (no path) which
> resolves to system python. System python doesn't include pynq_dpu.
> The pynq venv python doesn't include user-local packages (~/.local).
> Fixing both ensures all notebooks (CPU and DPU) use the same correct python.

---

## Critical Gotchas (learned the hard way)

### DO NOT use apt vitis-ai-runtime
```bash
# NEVER do this — crashes with SIGSEGV on kernel 5.15.0-1027:
sudo apt install vitis-ai-runtime
```
The Ubuntu universe package has a C++ ABI mismatch with the 2024 kernel. Always use Kria-PYNQ instead.

### DO NOT retry xmutil loadapp repeatedly
Each failed attempt leaks CMA memory. After ~5 attempts `DpuOverlay()` hangs forever.
**Only fix: reboot.**

### Check CMA before every DPU run
```bash
cat /proc/meminfo | grep Cma   # CmaFree must be >500MB
```
If low — reboot before running any notebook.

### Always run DPU notebooks from Jupyter, not bare terminal
Python 3.10 mmap differences cause silent infinite hang in bare terminal.
Use `http://<board-ip>:9090/lab` always.

### Power sensor location
```bash
# Board total power (microwatts):
cat /sys/class/hwmon/hwmon2/power1_input
# Divide by 1,000,000 for Watts
```

### xbutil syntax changed between XRT versions
```bash
# XRT 2.8.x:
sudo xbutil program -p file.xclbin

# XRT 2.13.x (OEM repo):
sudo xbutil program -d 0 -u file.xclbin
```
We went through both versions trying to fix the DPU. The OEM repo (2.13) version is what works with Kria-PYNQ.

### Snap packages do NOT work on Ubuntu 22.04
The AMD snap packages (`xlnx-nlp-smartvision`, `xlnx-vai-lib-samples` etc.) were built for Ubuntu 20.04 / Python 3.8.
On Ubuntu 22.04 with Python 3.10 they fail with library incompatibilities:
- `libboost_filesystem.so.1.71.0` not found (22.04 has 1.74)
- Python 3.8 `.so` bindings won't load in Python 3.10
- `DpuOverlay()` hangs due to version mismatch
**Use Kria-PYNQ instead** — it's built specifically for 22.04.

### DpuOverlay() hangs if another process holds the DPU
Only one process can use the DPU at a time. If a previous Jupyter kernel or script is still running:
```bash
sudo pkill -f jupyter-kernel   # kill stale kernels
sudo systemctl restart jupyter  # or restart Jupyter entirely
```
Then reboot if CMA is still low.

---

## Software Versions (confirmed working)

| Software | Version |
|---|---|
| Ubuntu | 22.04.4 LTS |
| Kernel | 5.15.0-1027-xilinx-zynqmp |
| XRT | 2.13.466-0ubuntu2 |
| PYNQ | 3.0.1 |
| pynq-dpu | 2.5.1 |
| ONNX Runtime | 1.23.2 |
| Kria-PYNQ | 3.0 |

---

## Repos to Fork (in case they go offline)

All three have been forked to https://github.com/hcneema — use these as the authoritative backup copies.

| Repo | Original | Fork (use this) | Why |
|---|---|---|---|
| Kria-PYNQ | https://github.com/Xilinx/Kria-PYNQ | https://github.com/hcneema/Kria-PYNQ | Critical — install script + pre-built pynq-dpu binaries for KV260 |
| WiFi driver | https://github.com/morrownr/88x2bu-20210702 | https://github.com/hcneema/88x2bu-20210702 | RTL88x2bu driver for USB WiFi adapter |
| kv260-ubuntu-test | https://github.com/iotengineer22/kv260-ubuntu-test | https://github.com/hcneema/kv260-ubuntu-test | Critical reference — working dpu.bit, pre-compiled B512+B4096 xmodels, working Python for Ubuntu 22.04. This proved DPU works when AMD docs were unclear. Community repo — could disappear anytime. |

> **Usage**: Try the original first. If it's unavailable or broken, use the fork.
> To install Kria-PYNQ from the fork instead of original:
> ```bash
> git clone https://github.com/hcneema/Kria-PYNQ /home/ubuntu/Kria-PYNQ
> ```
