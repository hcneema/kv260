# Resizer: FPGA vs CPU Image Resizer

## Task: Resize 4K (3840x2160) image to 1080p (1920x1080)
## Platform: KV260 (Ubuntu 22.04, kernel 5.15.0-1027)
## Overlay: pynq-resizer resizer.bit (Kria-PYNQ)

| Metric | CPU (ARM Cortex-A53) | FPGA (PL) | Speedup |
|---|---|---|---|
| Time/frame | 377 ms | 66.8 ms | **5.6x faster** |
| FPS | 2.65 | 14.97 | **5.6x more** |
| Power (Watts) | 3.34 | 3.51 | ~same (~5%) |
| **FPS/Watt** | **0.79** | **4.27** | **5.4x more efficient** |

## Key insight
Unlike the CNN benchmarks where DPU uses 2x more power for 29-50x speedup,
the FPGA resizer uses **virtually the same power** as the CPU (~3.5W both)
while being **5.6x faster** — making it 5.4x more energy efficient.

This shows FPGA efficiency applies beyond CNN inference to general image processing.

## Notes
- Timing from pynq-resizer notebooks (7 runs each, timeit)
- Power measured via INA260 at `/sys/class/hwmon/hwmon2/power1_input`
- CPU uses PIL (Python Imaging Library) BICUBIC resize
- FPGA uses AXI DMA + custom resize IP from pynq-resizer overlay

## How to Reproduce
```bash
# Open Jupyter at http://<board-ip>:9090/lab  password: xilinx
# Run: pynq-resizer/resizer_ps.ipynb  (CPU)
# Run: pynq-resizer/resizer_pl.ipynb  (FPGA)
```
The notebooks are pre-installed by Kria-PYNQ — no additional setup needed.
