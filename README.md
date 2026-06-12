# KV260 AI Projects

AMD Kria KV260 Vision AI Starter Kit — robotics and edge AI benchmarking projects.

## Contents

| Directory | Description |
|---|---|
| `dpu_benchmark/` | CPU vs DPU energy efficiency benchmark (ResNet50, YOLOv3, InceptionV1) |
| `robotics/` | Robot vision project — KV260 + Elegoo Mega 2560, servo control, face detection |
| `cnn-demo/` | MobileNetV2 ONNX inference demo (CPU baseline) |

## Key Results

**DPU is 29-50x more energy efficient than ARM CPU for CNN inference:**

| Model | CPU FPS/W | DPU FPS/W | Advantage |
|---|---|---|---|
| ResNet50 | 0.37 | 10.56 | **29x** |
| YOLOv3 | 0.03 | 1.51 | **50x** |
| InceptionV1 | 0.92 | 27.44 | **30x** |

## Hardware
- **Board**: AMD Kria KV260 revB
- **OS**: Ubuntu 22.04.4 LTS
- **DPU**: DPUCZDX8G B512 (via Kria-PYNQ)

## Setup
See `dpu_benchmark/SETUP.md` for full board setup guide (~45 min).
See `dpu_benchmark/README.md` for benchmark details and how to reproduce.
