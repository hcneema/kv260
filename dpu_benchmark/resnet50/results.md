# ResNet50 Benchmark Results

## Platform: KV260 (Ubuntu 22.04, kernel 5.15.0-1027)
## Model: ResNet50 (image classification, 1000 classes, input 224x224)

| Metric | CPU (ARM Cortex-A53) | DPU (B512) | Speedup |
|---|---|---|---|
| FPS | 1.59 | 92.1 | **58x faster** |
| Latency (ms/frame) | 629.1 | 10.9 | **58x lower** |
| Power (Watts) | 4.35 | 8.72 | 2x more |
| FPS/Watt | 0.37 | 10.56 | **29x more efficient** |

## Notes
- Power measured via INA260 sensor at `/sys/class/hwmon/hwmon2/power1_input`
- CPU uses ONNX Runtime 1.23.2 with CPUExecutionProvider
- DPU uses pynq-dpu with B512 bitstream (dpu.bit from Kria-PYNQ package)
- Same model architecture, different runtime/hardware
- CPU ran 20 frames (fewer to avoid overheating), DPU ran 100 frames

## How to Reproduce

### Prerequisites
1. Kria-PYNQ installed on KV260 (see `../SETUP.md`)
2. Run `bash ../setup_all.sh` to copy models and install onnxruntime

### Run via Jupyter (recommended — step by step)
Open in browser: `http://<board-ip>:9090/lab` password: `xilinx`
- DPU: open `dpu_bench.ipynb` → Run All Cells
- CPU: open `cpu_bench.ipynb` → Run All Cells

### Run via script
```bash
# DPU (from Jupyter terminal — pynq venv required)
source /etc/profile.d/pynq_venv.sh
python3 /home/ubuntu/dpu_benchmark/resnet50/dpu_bench.py

# CPU (from any terminal)
python3 /home/ubuntu/dpu_benchmark/resnet50/cpu_bench.py
```

### Files needed
- `models/resnet50-v1-7.onnx` (98MB) — CPU model ✅ included
- `models/dpu_resnet50.xmodel` (25MB) — DPU model ✅ included
- `../shared/dpu.bit` (7MB) — FPGA bitstream ✅ included

---

## Gotchas

### 1. CPU overheats at high frame counts
ResNet50 on ARM CPU runs at 100% load — keep `N_BENCHMARK=20` max.
The board crashed once when we tried 50 frames with simultaneous model download.
**Always download the model separately first, then benchmark.**

### 2. DPU must run from Jupyter, not bare terminal
Python 3.10 mmap differences cause a silent infinite hang in bare terminal.
Always run DPU notebooks from `http://<board-ip>:9090/lab`.

### 3. Check CMA before running DPU
```bash
cat /proc/meminfo | grep Cma   # CmaFree must be >500MB
```
If low — reboot. Each failed DPU load leaks CMA; after ~5 failures it hangs forever.

### 4. pynq venv required for DPU
```bash
source /etc/profile.d/pynq_venv.sh   # required before running DPU scripts
```
System Python has NumPy 2.x which conflicts with pynq compiled modules.
