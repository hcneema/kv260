# KV260 Board Lockdown — Auto-Update Prevention

Applied 2026-08-12. Board is frozen at a known-good state for DPU inference.
Run `resnet50/dpu_bench.py` to verify DPU is still working after any reboot.

---

## What Was Locked and Why

| Risk | Fix Applied | Why Critical |
|---|---|---|
| XRT upgrade | `apt-mark hold xrt` | Upgrading XRT breaks zocl/DPU — only fix is SD card reflash |
| Kernel upgrade | `apt-mark hold linux-image/headers` | zocl kernel module is built against 5.15.0-1027 — new kernel = broken DPU |
| apt auto-updates | timers disabled + apt config zeroed | Prevents any package from being upgraded in background |
| unattended-upgrades | package removed | Was the primary auto-update mechanism |
| update-manager | package removed | GUI/CLI upgrade tool — removed to prevent accidental upgrades |
| fwupd firmware updates | service + timer disabled | Could update board firmware |
| do-release-upgrade to 24.04 | `Prompt=never` in release-upgrades | Ubuntu 22.04 → 24.04 upgrade would break everything |
| snap auto-refresh | `refresh.hold=forever` | Snap packages (firefox etc) could auto-update |
| snap auto-repair | `snapd.snap-repair.timer` disabled | Could download and apply snap repairs |
| anacron (missed job catchup) | disabled | Runs missed cron.daily/weekly/monthly jobs on next boot |

---

## Locked Package Versions

```
xrt                                  2.13.479-0ubuntu2
linux-image-5.15.0-1027-xilinx-zynqmp  5.15.0-1027.31
linux-image-xilinx-zynqmp            5.15.0.1027.31
linux-headers-5.15.0-1027-xilinx-zynqmp
linux-headers-xilinx-zynqmp
```

Verify with:
```bash
apt-mark showhold
```

---

## DPU Boot Dependencies (all verified working)

| Component | Mechanism | Verified |
|---|---|---|
| zocl kernel module | `/etc/modules-load.d/zocl.conf` | ✅ |
| pynq device tree overlay | `pynq-dtbo.service` (enabled) | ✅ |
| CMA memory reservation | `cma=1000M` in kernel bootargs | ✅ |
| XILINX_XRT env var | `/etc/profile.d/pynq_venv.sh` | ✅ |
| Jupyter on port 9090 | `jupyter.service` (enabled) | ✅ |

---

## Quick Sanity Check After Any Reboot

```bash
# 1. Overlay applied?
cat /sys/kernel/config/device-tree/overlays/pynq/status   # must say: applied
ls /dev/dri/                                               # must include renderD128

# 2. CMA healthy?
cat /proc/meminfo | grep CmaFree                           # must be >500000 kB

# 3. DPU inference working?
source /etc/profile.d/pynq_venv.sh
sudo -E /usr/local/share/pynq-venv/bin/python3 /home/ubuntu/dpu_benchmark/resnet50/dpu_bench.py
# Expected: ~96 FPS, ~8.2W
```

---

## If Something Breaks After Reboot

**zocl not applied (renderD128 missing):**
```bash
sudo dtc -I dts -O dtb -o /tmp/pynq.dtbo /home/ubuntu/Kria-PYNQ/dts/pynq.dts
sudo cp /tmp/pynq.dtbo /lib/firmware/pynq.dtbo
sudo mkdir -p /sys/kernel/config/device-tree/overlays/pynq
echo -n pynq.dtbo | sudo tee /sys/kernel/config/device-tree/overlays/pynq/path
```

**CMA exhausted (<500MB free):** Reboot the board.

**DPU busy (another process holds it):**
```bash
sudo fuser /dev/dri/renderD128
sudo kill -9 <pid>
```

**XRT was upgraded despite hold** (check with `apt-mark showhold`): Full SD card reflash required — see `DPU_setup.md`.
