# YOLOv3 Benchmark Results

## Platform: KV260 (Ubuntu 22.04, kernel 5.15.0-1027)
## Model: YOLOv3 (object detection, VOC dataset, input 416x416)

| Metric | CPU (ARM Cortex-A53) | DPU (B512) | Speedup |
|---|---|---|---|
| FPS | 0.22 | 14.7 | **67x faster** |
| Latency (ms/frame) | 4643.8 | 67.9 | **68x lower** |
| Power (Watts) | 6.25 | 9.75 | 1.6x more |
| FPS/Watt | 0.03 | 1.51 | **50x more efficient** |

## Notes
- Power measured via INA260 sensor at `/sys/class/hwmon/hwmon2/power1_input`
- CPU uses ONNX Runtime with CPUExecutionProvider
- DPU uses pynq-dpu with B512 bitstream (dpu.bit from Kria-PYNQ)
- DPU xmodel: `tf_yolov3_voc.xmodel` (TensorFlow VOC)
- CPU ONNX: `yolov3-10.onnx` from ONNX model zoo
- CPU frames kept low (10) — YOLOv3 is very slow on ARM, avoid overheating

## How to Reproduce

### Prerequisites
1. Kria-PYNQ installed on KV260 (see `../SETUP.md`)
2. Run `bash ../setup_all.sh` to copy models and install onnxruntime

### Run via Jupyter (recommended)
Open in browser: `http://<board-ip>:9090/lab` password: `xilinx`
- DPU: open `dpu_bench.ipynb` → Run All Cells
- CPU: open `cpu_bench.ipynb` → Run All Cells (**Warning: ~46 seconds, board runs hot**)

### Files needed
- `models/yolov3-10.onnx` (237MB) — CPU model ✅ included
- `models/tf_yolov3_voc.xmodel` (61MB) — DPU model ✅ included
- `../shared/dpu.bit` (7MB) — FPGA bitstream ✅ included

---

## Gotchas

### 1. YOLOv3 CPU is extremely slow — board runs hot
Each frame takes ~4.6 seconds on ARM. Keep `N_BENCHMARK=10` (46s total).
Fan runs hard — let board cool between CPU and DPU runs. We had one crash.

### 2. YOLOv3 ONNX model cannot be downloaded via wget
GitHub LFS blocks wget — you get a 0-byte file.
**Must download via browser**: click "Download raw file" on GitHub.
Verify: `md5sum yolov3-10.onnx` should be `ab2add3cf1200ffb912e5d25c5bbdd29`

### 3. YOLOv3 ONNX has TWO inputs (unlike ResNet50)
```python
inputs = {
    session.get_inputs()[0].name: input_image,   # (1, 3, 416, 416)
    session.get_inputs()[1].name: input_shape,   # [[416, 416]]
}
```
Passing only one input fails with a cryptic error.

### 4. DPU must run from Jupyter, not bare terminal
Python 3.10 mmap differences cause silent hang in bare terminal.
Always use `http://<board-ip>:9090/lab`.

### 5. Check CMA before running DPU
```bash
cat /proc/meminfo | grep Cma   # CmaFree must be >500MB
```
If low — reboot. Each failed DPU load leaks CMA.
