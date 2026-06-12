# Edge AI Benchmark: CPU vs DPU
## KV260 Energy Efficiency Study

---

## Summary — Confirmed Results (measured 2026-06-12)

**Key finding: DPU is 29-50x more energy efficient than ARM CPU**

| Model | Task | CPU FPS | CPU W | CPU FPS/W | DPU FPS | DPU W | DPU FPS/W | DPU advantage |
|---|---|---|---|---|---|---|---|---|
| ResNet50 | Classification | 1.59 | 4.35 | 0.37 | 92.1 | 8.72 | 10.56 | **29x** |
| YOLOv3 | Detection | 0.22 | 6.25 | 0.03 | 14.7 | 9.75 | 1.51 | **50x** |
| InceptionV1 | Classification | 3.86 | 4.21 | 0.92 | 217.7 | 7.93 | 27.44 | **30x** |

---

## Platform
- **Board**: AMD Kria KV260 revB
- **OS**: Ubuntu 22.04.4 LTS, kernel 5.15.0-1027-xilinx-zynqmp
- **CPU**: ARM Cortex-A53 quad-core @ 1.3GHz
- **DPU**: DPUCZDX8G B512 (via pynq-dpu, `dpu.bit`)
- **Power sensor**: INA260 at `/sys/class/hwmon/hwmon2/power1_input`
- **CPU runtime**: ONNX Runtime 1.23.2
- **DPU runtime**: pynq-dpu 2.5.1 (Kria-PYNQ 3.0)

---

## Why FPS/Watt Matters
Raw FPS is not the whole story. For battery-powered robots and always-on vision systems, **energy efficiency** determines real-world feasibility.

The DPU uses ~2x more power than idle CPU, but delivers 14-217x more FPS — making it 29-50x more efficient per watt.

---

## Test Cases

| Folder | CPU model | DPU model | Self-contained? |
|---|---|---|---|
| `resnet50/` | `resnet50-v1-7.onnx` (98MB) ✅ | `dpu_resnet50.xmodel` (25MB) ✅ | **Yes** |
| `yolov3/` | `yolov3-10.onnx` (237MB) ✅ | `tf_yolov3_voc.xmodel` (61MB) ✅ | **Yes** |
| `inceptionv1/` | `inception-v1-9.onnx` (27MB) ✅ | `dpu_tf_inceptionv1.xmodel` (6MB) ✅ | **Yes** |

Shared: `shared/dpu.bit` (7MB) + `shared/dpu.hwh` (760KB) — same for all models.

---

## How to Run on a Fresh Board

> **See `SETUP.md` for the full step-by-step board setup guide** including all the gotchas we hit during our 7+ hour first-time setup.

```bash
# 1. Install Kria-PYNQ (see SETUP.md — takes ~45 min)

# 2. Copy this entire dpu_benchmark/ folder to the board
scp -r dpu_benchmark/ ubuntu@<board-ip>:/home/ubuntu/

# 3. SSH into board and run setup
ssh ubuntu@<board-ip>
cd /home/ubuntu/dpu_benchmark
bash setup_all.sh

# 4. Open Jupyter at http://<board-ip>:9090/lab  password: xilinx

# 5. Run notebooks in order:
#    resnet50/dpu_bench.ipynb    -> DPU (~92 FPS expected)
#    resnet50/cpu_bench.ipynb    -> CPU (~1.6 FPS expected)
#    yolov3/dpu_bench.ipynb      -> DPU (~14.7 FPS expected)
#    yolov3/cpu_bench.ipynb      -> CPU (~0.22 FPS, slow! ~46s total)
#    inceptionv1/dpu_bench.ipynb -> DPU (~217 FPS expected)
#    inceptionv1/cpu_bench.ipynb -> CPU (~3.86 FPS expected)
```

---

## Future Work
- Add Jetson Nano GPU results for three-way comparison
- Test newer models: YOLOv8, MobileNetV3 (requires Vitis AI Docker on x86 to compile)
- Add helloworld FPGA vs CPU comparison (resizer: 381ms CPU vs 67ms FPGA, 5.7x speedup)
