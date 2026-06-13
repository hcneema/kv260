# KV260 AI Projects

AMD Kria KV260 Vision AI Starter Kit — robotics and edge AI benchmarking projects.

## Contents

| Directory | Description |
|---|---|
| `dpu_benchmark/` | CPU vs DPU/FPGA energy efficiency benchmark suite |
| `robotics/` | Robot vision project — KV260 + Elegoo Mega 2560, servo control, face detection |
| `cnn-demo/` | MobileNetV2 ONNX inference demo (CPU baseline) |

---

## Key Results (measured on KV260 revB, Ubuntu 22.04)

### CNN Inference: CPU vs DPU (FPGA neural network accelerator)

**DPU is 29-50x more energy efficient than ARM CPU:**

| Model | Task | CPU FPS/W | DPU FPS/W | Advantage |
|---|---|---|---|---|
| ResNet50 | Classification | 0.37 | 10.56 | **29x** |
| YOLOv3 | Detection | 0.03 | 1.51 | **50x** |
| InceptionV1 | Classification | 0.92 | 27.44 | **30x** |

### Image Processing: CPU vs FPGA (non-CNN task)

**FPGA is 5.4x more energy efficient at same power draw:**

| Task | CPU FPS/W | FPGA FPS/W | Advantage |
|---|---|---|---|
| MNIST digit classification | 370.1 | DPU B512 | 510.5 | **1.4x** |
| 4K→1080p resize | 0.79 | 4.27 | **5.4x** |

> FPGA efficiency is not limited to AI — even general image processing benefits significantly.

---

## Hardware
- **Board**: AMD Kria KV260 revB
- **OS**: Ubuntu 22.04.4 LTS, kernel 5.15.0-1027-xilinx-zynqmp
- **CPU**: ARM Cortex-A53 quad-core @ 1.3GHz
- **DPU**: DPUCZDX8G B512 (via Kria-PYNQ)
- **Power sensor**: INA260 onboard

---

## Setup
See `dpu_benchmark/SETUP.md` for full board setup guide (~45 min).
See `dpu_benchmark/README.md` for benchmark results and how to reproduce.

> **Large model files** (`.onnx`, `.xmodel`, `.bit`) tracked via Git LFS.
