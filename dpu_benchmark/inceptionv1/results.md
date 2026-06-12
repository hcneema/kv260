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

---

## Gotchas

### 1. InceptionV1 ONNX model cannot be downloaded via wget
GitHub LFS and HuggingFace both blocked programmatic download.
**Must download via browser**: https://github.com/onnx/models/blob/main/validated/vision/classification/inception_and_googlenet/inception_v1/model/inception-v1-9.onnx
→ click "Download raw file"

### 2. DPU is extremely fast — CMA must be healthy
At 217 FPS, InceptionV1 is the fastest model we benchmarked.
But if CMA is exhausted, `DpuOverlay()` hangs silently.
```bash
cat /proc/meminfo | grep Cma   # CmaFree must be >500MB before running
```

### 3. DPU must run from Jupyter, not bare terminal
Python 3.10 mmap differences cause silent infinite hang in bare terminal.
Always use `http://<board-ip>:9090/lab`.

### 4. pynq venv required
```bash
source /etc/profile.d/pynq_venv.sh
```
System Python has NumPy 2.x which conflicts with pynq compiled modules.
