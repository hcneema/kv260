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


---

## Three-Way Comparison: Inception Family (batch=1)

> ⚠️ **Model mismatch**: T4 runs InceptionV3 (Keras, 24M params, 299×299); KV260 runs InceptionV1 (6M params, 224×224). InceptionV1 is not available in `tf.keras.applications`. FPS numbers are **not directly comparable** — InceptionV3 is ~4x more compute-intensive. FPS/W_delta is indicative: InceptionV1 on T4 would likely show higher FPS/W_delta, but GPU scaling at batch=1 is sub-linear so the DPU efficiency gap would remain large.

| Platform | Model | FPS | Active Power | Delta Power | FPS/W_delta |
|---|---|---|---|---|---|
| T4 GPU (Colab) | InceptionV3 | 78.40 ± 10.86 | 62.63 W | 33.50 W | 2.34 ± 0.24 |
| **KV260 DPU** | **InceptionV1** | **165.75 ± 0.33** | **—** | **—** | **64.73 ± 3.84** |
| KV260 CPU | InceptionV1 | 3.86 ± 0.01 | — | — | 3.35 ± 0.04 |

**Per-round T4 results (InceptionV3):**

| Rnd | FPS | Lat mean | Lat p95 | Active W | Delta W | FPS/W_d |
|---|---|---|---|---|---|---|
| 1 | 86.2 | 11.59 | 16.10 | 63.53 | 34.39 | 2.51 |
| 2 | 85.1 | 11.75 | 16.22 | 64.27 | 35.13 | 2.42 |
| 3 | 62.7 | 15.95 | 26.19 | 60.11 | 30.98 | 2.02 |
| 4 | 82.7 | 12.08 | 16.86 | 65.14 | 36.00 | 2.30 |
| 5 | 88.1 | 11.34 | 15.75 | 62.42 | 33.29 | 2.65 |
| 6 | 82.6 | 12.10 | 17.34 | 67.58 | 38.44 | 2.15 |
| 7 | 73.2 | 13.66 | 20.39 | 59.58 | 30.45 | 2.40 |
| 8 | 54.1 | 18.47 | 27.02 | 57.80 | 28.66 | 1.89 |
| 9 | 83.9 | 11.91 | 17.16 | 64.58 | 35.45 | 2.37 |
| 10 | 85.3 | 11.71 | 16.90 | 61.32 | 32.19 | 2.65 |

Idle power: 29.14 W. Rounds 3 and 8 show Colab scheduler preemption (same pattern as ResNet50 run).

**Key findings (with model-mismatch caveat):**
- KV260 DPU FPS/W_delta (64.73) vs T4 GPU (2.34) = **27.7x** — overstated due to model mismatch (InceptionV3 is ~4x harder than InceptionV1); true same-model advantage would be lower but remains large given sub-linear GPU scaling at batch=1
- T4 active power (62.63 W) is **7.7x the KV260's entire active power** for the Inception workload
- High FPS variance on T4 (±10.86) vs near-zero on KV260 DPU (±0.33) — scheduler preemption on shared cloud GPU

---

## Three-Way Comparison: YOLOv3 / Object Detection (batch=1)

> ⚠️ **Model mismatches** (all documented — T4 result is a conservative lower-bound GPU estimate):
> - Ultralytics auto-upgraded `yolov3.pt` → `yolov3u.pt` (103M params vs standard YOLOv3 ~62M). Standard YOLOv3 on T4 would be faster and more efficient.
> - Input: 640×640 (T4 native) vs 416×416 (KV260)
> - Framework: PyTorch FP32 (T4) vs ONNX Runtime FP32 (CPU) vs pynq-dpu INT8 (DPU)
> - Training data: COCO (T4) vs VOC (KV260 DPU)

| Platform | Model | FPS | Active Power | Delta Power | FPS/W_delta |
|---|---|---|---|---|---|
| T4 GPU (Colab) | YOLOv3u, 640×640, COCO | 15.40 ± 0.37 | 67.54 W | 41.57 W | 0.37 ± 0.01 |
| **KV260 DPU** | **YOLOv3, 416×416, VOC, INT8** | **13.23 ± 0.02** | **—** | **—** | **3.09 ± 0.10** |
| KV260 CPU | YOLOv3, 416×416, COCO, FP32 | 0.22 ± 0.00 | — | — | 0.17 ± 0.01 |

**Key findings:**
- KV260 DPU is **8.4x more energy efficient** than T4 GPU — consistent with ResNet50 result (8.2x)
- T4 running a larger model at higher resolution is only **1.16x faster** in raw FPS
- T4 run was very stable (±0.37 FPS) — YOLOv3u is compute-heavy enough to fully saturate the GPU, eliminating scheduler preemption seen in lighter models

**Per-round T4 results (YOLOv3u, 640×640):**

| Rnd | FPS | Lat mean | Lat p95 | Active W | Delta W | FPS/W_d |
|---|---|---|---|---|---|---|
| 1 | 16.0 | 62.51 | 63.66 | 69.37 | 43.39 | 0.37 |
| 2 | 15.8 | 63.08 | 64.01 | 67.64 | 41.67 | 0.38 |
| 3 | 15.7 | 63.63 | 64.48 | 67.15 | 41.18 | 0.38 |
| 4 | 15.6 | 64.09 | 65.04 | 67.56 | 41.58 | 0.37 |
| 5 | 15.5 | 64.51 | 65.58 | 68.80 | 42.82 | 0.36 |
| 6 | 15.4 | 65.04 | 65.84 | 67.13 | 41.16 | 0.37 |
| 7 | 15.2 | 65.68 | 66.77 | 66.98 | 41.00 | 0.37 |
| 8 | 15.1 | 66.13 | 66.99 | 66.90 | 40.93 | 0.37 |
| 9 | 14.9 | 66.93 | 68.00 | 67.36 | 41.39 | 0.36 |
| 10 | 14.8 | 67.43 | 68.44 | 66.52 | 40.54 | 0.37 |

Idle power: 25.97 W.

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
