# KV260 DPU Setup — Complete Guide

## Status: DPU FULLY WORKING (2026-06-10) ✅

---

## Hardware & Access
- **Board**: AMD Kria KV260 revB, Ubuntu 22.04.4 LTS (new microSD)
- **WiFi IP**: `192.168.68.59`
- **SSH**: `ssh ubuntu@192.168.68.59` / password: `redroses21`
- **Jupyter**: `http://192.168.68.59:9090/lab` / password: `xilinx`

---

## What's Installed
| Package | Version | Source |
|---|---|---|
| xrt | 2.13.466-0ubuntu2 | OEM repo (oem.archive.canonical.com) |
| xlnx-firmware-kv260-benchmark-b4096 | 0.12-0xlnx2 | ppa:xilinx-apps/ppa |
| Kria-PYNQ | 3.0.1 | github.com/Xilinx/Kria-PYNQ |
| pynq-dpu | 2.5.1 | installed by Kria-PYNQ |
| Docker | 29.1.3 | docker.io apt |

## APT Repos
```
deb http://oem.archive.canonical.com/updates/ jammy-limerick public
deb https://ppa.launchpadcontent.net/xilinx-apps/ppa/ubuntu/ jammy main
```

---

## DPU Load Sequence (after every reboot — do this ONCE only)
```bash
sudo bash /home/ubuntu/setup_dpu.sh
cat /proc/meminfo | grep Cma    # CmaFree must be >500MB before running Python
```

Contents of `/home/ubuntu/setup_dpu.sh`:
```bash
#!/bin/bash
sleep 2
sudo xmutil unloadapp 2>/dev/null
sudo xmutil loadapp kv260-benchmark-b4096
sleep 2
sudo xbutil program -d 0 -u /lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin
sudo chmod 666 /dev/dri/renderD128 /dev/dri/card0 /dev/dri/card1
sudo chmod 666 /dev/dma_heap/reserved /dev/dma_heap/system
sudo chmod 666 /dev/ttyACM0 /dev/video0 /dev/video1 2>/dev/null
```

---

## CONFIRMED RESULTS (2026-06-10)

### DPU Working — Proof
- `from pynq_dpu import DpuOverlay` — imports OK ✅
- `DpuOverlay("dpu.bit")` in Jupyter — no hang ✅
- CMA consumed: 975MB → 659MB during inference (316MB used by DPU buffers) ✅
- `kds_custat_raw`: status=0x6 (done), usage=5 (CU invoked 5 times) ✅
- Objects detected: 6, 1, 2, 0 across test images — real inference ✅

### Benchmark Result
| Metric | Value |
|---|---|
| Notebook | `pynq-dpu/dpu_yolov3.ipynb` in Jupyter |
| Model | YOLO v3 (B512 DPU config) |
| FPS | **6.64 FPS** |
| DPU config | DPUCZDX8G B512 (smallest — pynq-dpu default) |

### CPU Baseline (from 24.04 card, for comparison)
| Metric | Value |
|---|---|
| Model | MobileNetV2 ONNX (onnxruntime) |
| FPS | ~12 FPS |
| Latency | ~83ms/frame |
| CPU load | ~100% |

### Notes on 6.64 FPS
- This used the B512 (smallest) DPU config bundled in pynq-dpu
- Our `kv260-benchmark-b4096` firmware has B4096 (largest) — should be ~5x faster
- For fair CPU vs DPU comparison, need same model on both sides

---

## Key Lessons Learned (hard way)

### 1. CMA Memory Exhaustion
- `DpuOverlay()` hangs silently when CMA is exhausted
- KV260 has 1024MB CMA — repeated failed load attempts drain it fast
- **Fix**: reboot to restore CMA. Never do repeated xmutil load/unload cycles.
- Check: `cat /proc/meminfo | grep Cma` — CmaFree must be >500MB

### 2. FPGA Manager Ownership Clash
- Ubuntu 22.04 uses `xmutil` + Linux configfs to manage FPGA
- PYNQ tries to manipulate FPGA manager directly → clashes with xmutil
- **Fix**: `DpuOverlay("file", download=False)` skips PYNQ's reprogramming
- Or: let pynq-dpu's own notebook handle it (it manages xmutil internally)

### 3. Python 3.10 mmap hang in bare terminal
- pynq-dpu tuned for Python 3.8 (Ubuntu 20.04)
- Python 3.10 C-API mmap differences cause silent hang in bare terminal
- **Fix**: run from Jupyter (`kria:9090/lab`) — PYNQ's configured kernel

### 4. apt vitis-ai-runtime 2.0 is broken on this kernel
- `tools_extra_ops.cpython-310.so` crashes with SIGSEGV on kernel 5.15.0-1027
- C++ ABI mismatch — not fixable without rebuilding from source
- **Fix**: use Kria-PYNQ instead — it has pre-built binaries that work

### 5. xbutil syntax changed between XRT versions
- XRT 2.8.x: `xbutil program -p file.xclbin`
- XRT 2.13.x: `xbutil program -d 0 -u file.xclbin`

---

## Files on Board
| Path | Purpose |
|---|---|
| `/home/ubuntu/setup_dpu.sh` | DPU load script (run after reboot) |
| `/home/ubuntu/kv260-ubuntu-test/` | Reference repo with YOLOX models |
| `/home/ubuntu/kv260-ubuntu-test/yolox-test/dpu_bench.py` | Our benchmark script |
| `/home/ubuntu/Kria-PYNQ/` | Kria-PYNQ install repo |
| `/usr/local/share/pynq-venv/` | PYNQ Python venv |
| `/lib/firmware/xilinx/kv260-benchmark-b4096/` | B4096 DPU firmware |

## Files on Windows
| Path | Purpose |
|---|---|
| `C:\Users\hemn\kv260\robotics\dpu_bench.py` | Benchmark script (copy to board) |
| `C:\Users\hemn\kv260\robotics\DPU_setup.md` | This file |

---

## Next Steps
1. Run `dpu_bench.py` from Jupyter terminal for clean benchmark with `download=False`
2. Get B4096 benchmark numbers (should be much faster than 6.64 FPS)
3. Run same model on CPU for fair apples-to-apples comparison
4. Record final CPU vs DPU table in ONBOARDING.md
