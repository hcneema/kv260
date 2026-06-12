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
