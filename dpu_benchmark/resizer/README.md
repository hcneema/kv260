# Resizer: FPGA vs CPU Image Resizer

A simple but powerful demonstration: the same task (resize 4K→1080p image)
running on ARM CPU vs FPGA fabric — **same power, 5.6x faster on FPGA.**

---

## Results (measured 2026-06-12)

| Metric | CPU (ARM Cortex-A53) | FPGA (PL) | Speedup |
|---|---|---|---|
| Time/frame | 377 ms | 66.8 ms | **5.6x faster** |
| FPS | 2.65 | 14.97 | **5.6x more** |
| Power (Watts) | 3.34 | 3.51 | ~same (~5% diff) |
| **FPS/Watt** | **0.79** | **4.27** | **5.4x more efficient** |

**Key insight**: Unlike CNN benchmarks where DPU uses 2x more power for 29-50x speedup,
the FPGA resizer uses **virtually the same power** as the CPU while being 5.6x faster.
FPGA efficiency applies to general image processing, not just AI inference.

---

## How to Run

### Prerequisites
Kria-PYNQ already installed (see `../SETUP.md`).
The resizer notebooks are **pre-installed** — no additional setup needed.

### Run via Jupyter (recommended)
```
http://<board-ip>:9090/lab  password: xilinx
```
1. Open `pynq-resizer/resizer_ps.ipynb` → Run All Cells (CPU)
2. Open `pynq-resizer/resizer_pl.ipynb` → Run All Cells (FPGA)

### Run our benchmark scripts (with power measurement)
```bash
source /etc/profile.d/pynq_venv.sh
python3 cpu_bench.py    # CPU resizer with power
sudo python3 fpga_bench.py   # FPGA resizer with power (needs sudo for DMA)
```

---

## Files

| File | Purpose |
|---|---|
| `cpu_bench.py` | CPU resizer benchmark with power measurement |
| `fpga_bench.py` | FPGA resizer benchmark with power measurement |
| `cpu_bench.ipynb` | Step-by-step CPU notebook |
| `fpga_bench.ipynb` | Step-by-step FPGA notebook |
| `results.md` | Detailed results |

**No model files needed** — this benchmark uses the FPGA fabric directly (not DPU).
The `resizer.bit` overlay comes pre-installed with Kria-PYNQ at:
`/root/jupyter_notebooks/pynq-resizer/resizer.bit`

---

## Gotchas Discovered

### 1. NumPy version conflict on system Python
```bash
# DO NOT use system python3 for anything PYNQ-related:
python3 script.py   # FAILS — numpy 2.2.6 vs compiled module mismatch

# ALWAYS use pynq venv:
source /etc/profile.d/pynq_venv.sh
python3 script.py   # Works
```

### 2. DMA overhead inflates FPGA timing
Direct DMA calls in Python add overhead vs the notebook's timeit measurement.
- Our DMA script: ~56ms per frame
- Notebook timeit: ~66.8ms per frame (includes Python overhead per call)
- **Use notebook results for fair comparison** — both CPU and FPGA measured same way.

### 3. sudo needed for DMA/FPGA access
```bash
sudo python3 fpga_bench.py   # required for /dev/mem access
# Or add user to relevant groups permanently
```

### 4. FPGA and DPU cannot coexist
Loading `resizer.bit` replaces whatever was in the FPGA (including DPU).
After running FPGA resizer, reload DPU before running DPU benchmarks:
```bash
sudo bash /home/ubuntu/setup_dpu.sh
```
