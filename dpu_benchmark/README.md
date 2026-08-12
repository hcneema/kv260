# Edge AI Benchmark: CPU vs DPU
## KV260 Energy Efficiency Study

---

## Summary — Confirmed Results (measured 2026-06-12)

**Key finding: FPGA/DPU is 5-50x more energy efficient than ARM CPU across all workloads**

| Task | CPU FPS/W | Accelerator | Accel FPS/W | Advantage |
|---|---|---|---|---|
| ResNet50 (classification) | 0.37 | DPU B512 | 10.56–11.74 | **29–32x** |
| YOLOv3 (detection) | 0.03 | DPU B512 | 1.51 | **50x** |
| InceptionV1 (classification) | 0.92 | DPU B512 | 27.44 | **30x** |
| MNIST (digit classification) | 370.1 | DPU B512 | 510.5 | **1.4x** |
| 4K→1080p image resize | 0.79 | FPGA (PL) | 4.27 | **5.4x** |

> MNIST note: Both CPU and DPU are fast (0.3-0.5ms/frame) — DPU advantage is smaller for tiny models. DPU shines on larger CNNs (ResNet50, YOLOv3).

> DPU = DPUCZDX8G B512 neural network accelerator (CNN inference)
> FPGA (PL) = Custom resize IP via pynq-helloworld (general image processing)

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

| Folder | CPU model | Accelerator model | Self-contained? |
|---|---|---|---|
| `resnet50/` | `resnet50-v1-7.onnx` (98MB) ✅ | `dpu_resnet50.xmodel` (25MB) ✅ | **Yes** |
| `yolov3/` | `yolov3-10.onnx` (237MB) ✅ | `tf_yolov3_voc.xmodel` (61MB) ✅ | **Yes** |
| `inceptionv1/` | `inception-v1-9.onnx` (27MB) ✅ | `dpu_tf_inceptionv1.xmodel` (6MB) ✅ | **Yes** |
| `mnist/` | `mnist-12.onnx` (26KB) ✅ | `dpu_mnist_classifier.xmodel` (759KB) ✅ | **Yes*** |
| `resizer/` | PIL/numpy (built-in) | `resizer.bit` (pre-installed by Kria-PYNQ) | **Yes** |

> *MNIST: models included, dataset downloaded by setup.sh (~12MB from Google)

Shared: `dpu.bit` + `dpu.hwh` are bundled inside the pynq-dpu package (not in this repo). `shared/dpu.xclbin` is in this repo — required by DpuOverlay alongside the bitstream.

---

## How to Run on a Fresh Board

> **See `SETUP.md` for the full step-by-step board setup guide** including all the gotchas we hit during our 7+ hour first-time setup.

Key things that aren't obvious:
- **SSH is not enabled by default** — requires monitor + keyboard on first boot to run `sudo systemctl enable ssh && sudo systemctl start ssh`
- **Lock XRT immediately** — `sudo apt-mark hold xrt` before any apt operations. Upgrading XRT breaks the DPU and requires a full SD card reflash
- **Kria-PYNQ install must use interactive sudo** — run `sudo bash install.sh -b KV260` from an interactive SSH session, not via piped password

```bash
# 1. Flash SD card, enable SSH via monitor (see SETUP.md Steps 1-3)

# 2. Lock XRT before anything else
sudo apt-mark hold xrt

# 3. Install Kria-PYNQ (interactive SSH session — see SETUP.md Step 5, ~25 min)
git clone https://github.com/hcneema/Kria-PYNQ /home/ubuntu/Kria-PYNQ
cd /home/ubuntu/Kria-PYNQ && sudo bash install.sh -b KV260

# 4. Copy this entire dpu_benchmark/ folder to the board
scp -r dpu_benchmark/ ubuntu@<board-ip>:/home/ubuntu/

# 5. SSH into board and run setup (handles everything else automatically)
ssh ubuntu@<board-ip>
cd /home/ubuntu/dpu_benchmark
bash setup_all.sh

# 6. Open Jupyter at http://<board-ip>:9090/lab  password: xilinx
#    Or run directly from SSH (no Jupyter needed):
#    source /etc/profile.d/pynq_venv.sh
#    sudo -E /usr/local/share/pynq-venv/bin/python3 resnet50/dpu_bench.py

# 7. Run notebooks in order:
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
- MNIST DPU vs CPU benchmark (model pre-installed with Kria-PYNQ)
