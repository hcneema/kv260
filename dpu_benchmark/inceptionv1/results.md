# InceptionV1 (GoogLeNet) Benchmark Results

## Platform: KV260 (Ubuntu 22.04, kernel 5.15.0-1027)
## Model: InceptionV1 / GoogLeNet (image classification, 1000 classes, input 224x224)

| Metric | CPU (ARM Cortex-A53) | DPU (B512) | Speedup |
|---|---|---|---|
| FPS | 3.86 | 217.7 | **56x faster** |
| Latency (ms/frame) | 259.1 | 4.6 | **56x lower** |
| Power (Watts) | 4.21 | 7.93 | 1.9x more |
| FPS/Watt | 0.92 | 27.44 | **30x more efficient** |

## Notes
- Power measured via INA260 sensor at `/sys/class/hwmon/hwmon2/power1_input`
- CPU uses ONNX Runtime 1.23.2 with CPUExecutionProvider
- DPU uses pynq-dpu with B512 bitstream (dpu.bit from Kria-PYNQ)
- DPU xmodel: `dpu_tf_inceptionv1.xmodel` (TensorFlow InceptionV1)
- CPU ONNX: `inception-v1-9.onnx` downloaded from GitHub ONNX model zoo
- DPU is fastest of all three models tested at 217.7 FPS (4.6ms latency)

## How to Reproduce

### Prerequisites
1. Kria-PYNQ installed on KV260 (see `../SETUP.md`)
2. Run `bash ../setup_all.sh` to copy models and install onnxruntime

### Run via Jupyter (recommended)
Open in browser: `http://<board-ip>:9090/lab` password: `xilinx`
- DPU: open `dpu_bench.ipynb` → Run All Cells
- CPU: open `cpu_bench.ipynb` → Run All Cells

### Files needed
- `models/inception-v1-9.onnx` (27MB) — CPU model ✅ included
- `models/dpu_tf_inceptionv1.xmodel` (6MB) — DPU model ✅ included
- `../shared/dpu.bit` (7MB) — FPGA bitstream ✅ included
