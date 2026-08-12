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

**Image used (confirmed working):**
```
iot-limerick-classic-desktop-2204-20240304-165.img
```
Downloaded as a zip archive (8 parts). Extract all parts first — Windows will reassemble them automatically into the `.img` file.

**Flash with Win32DiskImager (Windows):**
1. Download and open Win32DiskImager
2. Click the folder icon, select the extracted `.img` file
3. Select the SD card drive letter (be careful — wrong drive = data loss)
4. Click **Write**
5. Wait ~5-10 minutes for the write to complete

**Also available in Google Drive — kv260 folder** (faster than re-downloading from Ubuntu).

Download from: https://ubuntu.com/download/amd (scroll to bottom, KV260, Ubuntu 22.04)

---

## Step 2 — First Boot & SSH

**SSH is NOT enabled by default on the fresh image.** You must use a monitor + USB keyboard for the first boot.

1. Insert microSD, connect Ethernet **directly to your router** (not to your PC — Windows ICS does not NAT TCP reliably)
2. Connect HDMI monitor and USB keyboard to the KV260
3. Power on, wait 3-5 minutes (first boot resizes filesystem and shows a login prompt)
4. Log in: `ubuntu` / `ubuntu` — it will immediately force you to set a new password
5. Enable SSH so you can use it from your PC going forward:
   ```bash
   sudo systemctl enable ssh && sudo systemctl start ssh
   ```
6. Find the board IP from your router's DHCP client list (look for `kria`) or run `ip addr` on the board
7. From your PC: `ssh ubuntu@<board-ip>` — use the new password you just set

> You only need the monitor/keyboard for this one step. After SSH is enabled you can work remotely.

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

> The install script reboots the board automatically (exit code 255 is normal — not a failure).
> Wait ~60 seconds then SSH back in.

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

> **Set up SSH key auth before moving the board away from your desk:**
> ```bash
> # On your PC:
> ssh-keygen -t ed25519 -f ~/.ssh/kv260_key
> ssh-copy-id -i ~/.ssh/kv260_key ubuntu@<board-ip>
> ```
> You'll need it for autonomous / remote operation later.

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

> **Reboot after install completes** — the installer exhausts CMA memory during pip builds.
> CmaFree drops to ~50MB during install; a reboot restores it to ~1000MB.
> ```bash
> sudo reboot
> # wait 60s, then SSH back in and verify:
> cat /proc/meminfo | grep CmaFree   # must be >500MB before running DPU
> ```

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
# From your PC (scp the whole folder — git clone via HTTPS doesn't work in non-interactive SSH):
scp -r dpu_benchmark/ ubuntu@<board-ip>:/home/ubuntu/

# On the board:
cd /home/ubuntu/dpu_benchmark
bash setup_all.sh
```

Then open: `http://<board-ip>:9090/lab` password: `xilinx`

> **Note for Windows users**: Shell scripts edited on Windows have CRLF line endings that break bash.
> `setup_all.sh` auto-fixes this. If you edit scripts manually, run:
> `find /home/ubuntu/dpu_benchmark -name "*.sh" -exec sed -i "s/\r//" {} \;`

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

## Step 8c — Make dpu_benchmark Visible in Jupyter

Jupyter serves from `/root/jupyter_notebooks/` but the benchmarks live in `/home/ubuntu/dpu_benchmark/`.
Create a symlink so the folder appears in the Jupyter file browser:

```bash
sudo ln -s /home/ubuntu/dpu_benchmark /root/jupyter_notebooks/dpu_benchmark
```

Then refresh the Jupyter browser tab — `dpu_benchmark` will appear in the left panel.

> `setup_all.sh` does this automatically. Only needed if you skipped `setup_all.sh`.

---

## Step 8d — dpu.xclbin (required for DpuOverlay)

`DpuOverlay("dpu.bit")` requires a matching `dpu.xclbin` in the **same directory** as the notebook's working directory. This file is **not** the same as `dpu.bit` — it is a separate XRT binary.

The `shared/dpu.xclbin` in this repo is the correct file (copied from the Kria-PYNQ install).
`setup_all.sh` verifies it is present. If missing, copy it manually:

```bash
cp /usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/dpu.xclbin \
   /home/ubuntu/dpu_benchmark/shared/
```

> The notebooks call `DpuOverlay("dpu.bit")` which looks for `dpu.xclbin` relative to the
> **Jupyter working directory** (`/root`), not the notebook's folder. This is handled automatically
> by the Kria-PYNQ runtime (`/etc/vart.conf` is updated on overlay load).

---

## Critical Gotchas (learned the hard way)

### "Programming Device failed: ENODEV" — zocl device tree overlay not applied

`DpuOverlay("dpu.bit")` fails with `RuntimeError: Programming Device failed: ENODEV (19)` if the pynq device tree overlay was not applied on boot. This overlay adds the `zocl` device node that XRT needs to talk to the FPGA.

**Root cause:** The Kria-PYNQ `install.sh` applies this overlay as part of setup, but the step requires `sudo`. If the install ran without proper sudo (e.g., via a non-interactive SSH pipe), this step silently fails.

**Symptoms:**
```bash
lsmod | grep zocl       # zocl is loaded but...
ls /dev/dri/            # ...renderD128 is missing (only card0)
xbutil examine          # shows "0 devices found"
```

**Fix — run once, then it persists across reboots:**
```bash
# Compile and apply the device tree overlay
cd /home/ubuntu/Kria-PYNQ/dts
sudo dtc -I dts -O dtb -o /tmp/pynq.dtbo pynq.dts
sudo cp /tmp/pynq.dtbo /lib/firmware/pynq.dtbo
sudo mkdir -p /sys/kernel/config/device-tree/overlays/pynq
echo -n pynq.dtbo | sudo tee /sys/kernel/config/device-tree/overlays/pynq/path
# Verify:
cat /sys/kernel/config/device-tree/overlays/pynq/status   # should say: applied
ls /dev/dri/   # should now show renderD128
```

**Make it persist across reboots:**
`setup_all.sh` now handles this automatically via a `pynq-dtbo` systemd service.
If you set up manually, create `/lib/systemd/system/pynq-dtbo.service` and enable it.

### Disable unattended-upgrades immediately after setup
Ubuntu's automatic updater runs in the background and can silently update the kernel, XRT, or Python packages — any of which can break DPU. Disable it right after Kria-PYNQ is confirmed working:

```bash
sudo systemctl disable unattended-upgrades
sudo systemctl stop unattended-upgrades
sudo systemctl disable apt-daily.timer
sudo systemctl stop apt-daily.timer
sudo systemctl disable apt-daily-upgrade.timer
sudo systemctl stop apt-daily-upgrade.timer
```

Verify:
```bash
systemctl is-enabled unattended-upgrades    # should say: disabled
systemctl is-enabled apt-daily.timer        # should say: disabled
```

After this, updates only happen if you manually run `sudo apt upgrade`. The working versions are pinned in the Software Versions table below — do not upgrade them.

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
CmaFree drops to ~50MB right after Kria-PYNQ install — always reboot before first DPU run.

### Running DPU inference from .py files (not just Jupyter)

You do NOT need Jupyter. You can run `.py` files directly over SSH — confirmed working at 84+ FPS.
Three requirements must all be met:

```bash
# On the board:
source /etc/profile.d/pynq_venv.sh          # sets XILINX_XRT=/usr and BOARD=KV260
sudo -E /usr/local/share/pynq-venv/bin/python3 your_script.py
```

- `source pynq_venv.sh` — sets `XILINX_XRT=/usr` without which XRT returns ENODEV
- `sudo -E` — DRI device (`/dev/dri/renderD128`) requires root; `-E` preserves the env vars from the source
- Full path to pynq venv python — system `python3` doesn't have pynq_dpu installed

From your PC over SSH:
```bash
ssh ubuntu@192.168.68.60 "source /etc/profile.d/pynq_venv.sh && sudo -E /usr/local/share/pynq-venv/bin/python3 /home/ubuntu/dpu_benchmark/resnet50/run_bench.py"
```

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

### SSH "Offending key" error after re-flashing the SD card
After flashing a new SD card the board gets a new SSH host key, but your PC still has the old one.
SSH refuses to connect with: `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` or `Offending ECDSA key in ~/.ssh/known_hosts:7`

**Fix** — remove the old key and re-scan:
```bash
sed -i '/192.168.68.60/d' ~/.ssh/known_hosts
ssh-keyscan 192.168.68.60 >> ~/.ssh/known_hosts
```
Or just delete `~/.ssh/known_hosts` if this is a dev machine and you don't care about strict host verification.

### "sudo is disabled" means you are in Windows Git Bash, not SSH
If you see `sudo: command not found` or `sudo is disabled on this machine`, you ran the command in a
Windows terminal (Git Bash, PowerShell, WSL) instead of an SSH session to the board.
Always confirm you are on the board: `whoami` should show `ubuntu`, not your Windows username.

### Kria-PYNQ install MUST run with interactive sudo, not piped password

The install.sh has a step that applies the pynq device tree overlay (`pynq.dtbo`). This step requires a real interactive terminal with sudo — it silently skips when run via piped password (`echo pass | sudo -S`).

**Wrong (device tree step is silently skipped):**
```bash
echo redroses21 | sudo -S bash install.sh -b KV260
```

**Right (use an interactive SSH session):**
```bash
ssh ubuntu@192.168.68.60   # interactive terminal
sudo bash install.sh -b KV260
```

If you ran it the wrong way, `setup_all.sh` detects and fixes this automatically (creates the `pynq-dtbo` systemd service). The symptom is `ENODEV` when loading DpuOverlay — see the gotcha above.

### Kria-PYNQ install compiles packages from source — do not interrupt
The install takes ~25 minutes on ARM. Several packages (pycurl, etc.) are compiled from C source code.
The CPU hits 40-50% during compilation. This is normal.
- Do not Ctrl-C or close the SSH session
- If interrupted, re-run `sudo bash install.sh -b KV260` from the Kria-PYNQ directory
- The install is idempotent — re-running is safe

### apt-get update hangs connecting to IPv6 addresses
If `apt-get update` hangs with lines like:
`0% [Connecting to ports.ubuntu.com (2a06:bc80:...)]`

Force IPv4:
```bash
sudo apt-get -o Acquire::ForceIPv4=true update
```
This happens when the network doesn't route IPv6 properly (common with some routers and ICS setups).

### onnxruntime GPU warning is harmless
When importing onnxruntime you will see:
```
[W:onnxruntime:Default, device_discovery.cc:164] GPU device discovery failed: ...
    Failed to open file: "/sys/class/drm/card1/device/vendor"
```
This is expected — the KV260 has no GPU. onnxruntime falls back to CPU inference, which is correct.
The DPU is accessed through pynq-dpu, not onnxruntime.

### vart.conf modification message during DpuOverlay() is normal
When loading a DPU overlay you will see:
```
/etc/vart.conf file was modified, replacing contents '/run/media/mmcblk0p1/dpu.xclbin'
with '/usr/lib/dpu.xclbin'.
```
This is normal — the runtime updates the xclbin path for the current session. It is not an error.

### git clone via HTTPS fails in non-interactive SSH sessions
Git tries to open `/dev/tty` for credential prompts even on public repos, which doesn't exist in
non-interactive SSH. Use `scp` to copy files from your PC to the board instead:
```bash
# From your PC:
scp -r dpu_benchmark/ ubuntu@<board-ip>:/home/ubuntu/
```

### Windows ICS does not work for board internet
Windows Internet Connection Sharing (ICS) passes ICMP (ping works) but does not reliably NAT TCP.
`apt-get update`, `curl`, `git clone` all hang or fail through ICS.
**Fix**: Connect the board directly to your router via Ethernet. Both your PC (WiFi) and board (Ethernet)
on the same router — SSH works fine from PC to board.

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
