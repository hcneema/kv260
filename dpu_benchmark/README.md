# Edge AI Benchmark: CPU vs DPU
## KV260 Energy Efficiency Study

---

## Summary — Confirmed Results (measured 2026-08-12, 10 rounds each)

**Key finding: FPGA/DPU is 18–21x more energy efficient than ARM CPU across all CNN workloads**

| Task | CPU FPS | DPU FPS | Speedup | CPU FPS/W† | DPU FPS/W† | Efficiency gain |
|---|---|---|---|---|---|---|
| ResNet50 (classification) | 1.58±0.04 | 84.38±0.05 | **53.4x** | 1.33±0.03 | 28.65±0.79 | **21.5x** |
| InceptionV1 (classification) | 3.86±0.01 | 165.75±0.33 | **42.9x** | 3.35±0.04 | 64.73±3.84 | **19.3x** |
| YOLOv3 (object detection) | 0.22±0.00 | 13.23±0.02 | **60.1x** | 0.17±0.01 | 3.09±0.10 | **18.2x** |
| MNIST (digit classification) | 2415±18 | 3642±34 | **1.5x** | — | — | — |

> †FPS/W_delta = FPS ÷ (active power − idle power), removing fixed OS overhead (~4.83 W idle on KV260, ~26.7 W idle on T4). This is the primary efficiency metric — see RESULTS.md for full detail.
>
> MNIST note: Both CPU and DPU complete in <0.5ms/frame. DPU advantage is small for tiny models — the DPU shines on larger CNNs.

---

## Three-Way Comparison: KV260 DPU vs ARM CPU vs T4 GPU (ResNet50, batch=1)

> GPU results measured on Google Colab Tesla T4, 10 rounds × 100 frames, 2026-08-16.
> See `colab_gpu_bench/` for scripts and raw results.

| Platform | FPS | Active Power | Delta Power | FPS/W_delta | vs DPU efficiency |
|---|---|---|---|---|---|
| T4 GPU (Colab) | 119.67 ± 17.94 | 60.76 W | 34.07 W | 3.51 ± 0.42 | 0.12x |
| **KV260 DPU** | **84.38 ± 0.05** | **8.16 W** | **3.33 W** | **28.65 ± 0.79** | **1.0x (baseline)** |
| KV260 CPU | 1.58 ± 0.04 | 6.01 W | 1.18 W | 1.33 ± 0.03 | 0.05x |

**Key findings (batch=1 inference):**
- KV260 DPU is **8.2x more energy efficient** than T4 GPU, while being only 1.4x slower in raw FPS
- T4 GPU idle power alone (26.7 W) is **3.3x the KV260's entire active power** (8.16 W)
- KV260 DPU FPS variance: ±0.05 FPS. T4 GPU: ±17.94 FPS (Colab shared GPU scheduler) — **360x more stable**
- T4 GPU is a datacenter card optimised for large batches; at batch=1 it burns 61 W to be 1.4x faster than an 8 W edge board

> GPU benchmarks for InceptionV1 and YOLOv3 in progress — see `colab_gpu_bench/`.

---

## Platform

- **Board**: AMD Kria KV260 revB
- **OS**: Ubuntu 22.04.4 LTS, kernel 5.15.0-1027-xilinx-zynqmp
- **CPU**: ARM Cortex-A53 quad-core @ 1333 MHz (userspace governor, fixed)
- **DPU**: DPUCZDX8G B512 (via pynq-dpu 2.5.0, `dpu.bit`)
- **RAM**: 3911 MB total, 1000 MB CMA
- **Power sensor**: INA260 at `/sys/class/hwmon/hwmon2/power1_input` (~200ms sampling)
- **CPU runtime**: ONNX Runtime 1.23.2 (intra=4 threads, ORT_ENABLE_ALL)
- **DPU runtime**: pynq-dpu 2.5.0 (Kria-PYNQ 3.0)
- **DRAM bandwidth**: 2099.5 MB/s (measured, numpy 128 MB sequential read)
- **Idle power**: 4.832 W

---

## Why FPS/Watt Matters

Raw FPS is not the whole story. For battery-powered robots and always-on vision systems, **energy efficiency** determines real-world feasibility.

The DPU consumes ~2–4 W above idle while delivering 43–60x more throughput — making it 18–21x more efficient per watt of inference power. This advantage is measured conservatively using only the power delta above idle, excluding fixed OS overhead.

---

## Test Cases

| Folder | CPU model | DPU model | Rounds |
|---|---|---|---|
| `resnet50/` | `resnet50-v1-7.onnx` (98MB) | `dpu_resnet50.xmodel` (25MB) | 10 |
| `yolov3/` | `yolov3-10.onnx` (237MB) | `tf_yolov3_voc.xmodel` (61MB) | 10 |
| `inceptionv1/` | `inception-v1-9.onnx` (27MB) | `dpu_tf_inceptionv1.xmodel` (6MB) | 10 |
| `mnist/` | `mnist-12.onnx` (26KB) | `dpu_mnist_classifier.xmodel` (759KB) | 10 |

All DPU models are compiled for DPUCZDX8G B512 (INT8 fixed-point). CPU models run in FP32 via ONNX Runtime.

Shared: `dpu.bit` + `dpu.hwh` are bundled inside the pynq-dpu package (not in this repo). `shared/dpu.xclbin` is in this repo — required by DpuOverlay alongside the bitstream.

---

## How to Run on a Fresh Board

> **See `DPU_setup.md` for the full step-by-step board setup guide** including all the gotchas we hit during our 7+ hour first-time setup.

Key things that aren't obvious:
- **SSH is not enabled by default** — requires monitor + keyboard on first boot to run `sudo systemctl enable ssh && sudo systemctl start ssh`
- **Lock XRT immediately** — `sudo apt-mark hold xrt` before any apt operations. Upgrading XRT breaks the DPU and requires a full SD card reflash
- **Kria-PYNQ install must use interactive sudo** — run `sudo bash install.sh -b KV260` from an interactive SSH session, not via piped password

```bash
# 1. Flash SD card, enable SSH via monitor (see DPU_setup.md Steps 1-3)

# 2. Lock XRT before anything else
sudo apt-mark hold xrt

# 3. Install Kria-PYNQ (interactive SSH session — see DPU_setup.md Step 6, ~25 min)
git clone https://github.com/hcneema/Kria-PYNQ /home/ubuntu/Kria-PYNQ
cd /home/ubuntu/Kria-PYNQ && sudo bash install.sh -b KV260

# 4. Copy this entire dpu_benchmark/ folder to the board
scp -r dpu_benchmark/ ubuntu@<board-ip>:/home/ubuntu/

# 5. SSH into board and run setup (handles everything else automatically)
ssh ubuntu@<board-ip>
cd /home/ubuntu/dpu_benchmark
bash setup_all.sh

# 6. Run the main CNN benchmark (ResNet50, InceptionV1, YOLOv3 — DPU + CPU, 10 rounds)
nohup sudo bash -c 'source /etc/profile.d/pynq_venv.sh && \
    /usr/local/share/pynq-venv/bin/python3 run_benchmarks.py 10' \
    > bench_run.log 2>&1 &

# 7. Run the MNIST benchmark (DPU + CPU, 10 rounds, writes to RESULTS_extra.md)
nohup sudo bash -c 'source /etc/profile.d/pynq_venv.sh && \
    /usr/local/share/pynq-venv/bin/python3 run_benchmarks_extra.py' \
    > bench_extra.log 2>&1 &
```

---

## Results Files

| File | Contents |
|---|---|
| `RESULTS.md` | Full 10-round data for ResNet50, InceptionV1, YOLOv3 — per-round FPS, latency (p95/p99), power, FPS/W, temperature, CMA, XIR model metadata, DRAM bandwidth |
| `RESULTS_extra.md` | Full 10-round data for MNIST DPU + CPU |
| `raw_latencies/` | Per-frame latency CSVs for all runs |
| `raw_power/` | Timestamped power waveform CSVs for all DPU runs |
| `colab_gpu_bench/` | T4 GPU benchmark scripts and raw results (one script + results file per model) |

---

## Future Work

- Add Jetson Nano GPU results for three-way comparison
- Test newer models: YOLOv8, MobileNetV3 (requires Vitis AI Docker on x86 to compile)
- Resizer FPGA benchmark (pynq-helloworld unsupported on KV260/Ubuntu 22.04 — needs custom bitstream)
