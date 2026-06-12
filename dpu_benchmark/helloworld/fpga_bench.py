"""
Helloworld FPGA Benchmark: Image Resizer
Measures FPS and power on KV260 FPGA fabric (PL — Programmable Logic)
Task: Resize 4K (3840x2160) -> 1080p (1920x1080) using FPGA resize IP

IMPORTANT:
1. Run with pynq venv AND sudo:
    source /etc/profile.d/pynq_venv.sh
    sudo python3 fpga_bench.py

2. Uses resizer.bit from pynq-helloworld (not DPU — different overlay!)
   Location: /root/jupyter_notebooks/pynq-helloworld/resizer.bit

3. After running this, reload DPU if you need CNN benchmarks:
    sudo bash /home/ubuntu/setup_dpu.sh

KNOWN ISSUE: Direct DMA in Python adds ~10ms overhead vs notebook timeit.
Use notebook results (pynq-helloworld/resizer_pl.ipynb) for published timing.
This script is useful for power measurement only.
"""
import time
import numpy as np

POWER_SENSOR  = "/sys/class/hwmon/hwmon2/power1_input"
OVERLAY_PATH  = "/root/jupyter_notebooks/pynq-helloworld/resizer.bit"
N_WARMUP = 3
N_RUNS = 7

IN_W, IN_H   = 3840, 2160   # 4K
OUT_W, OUT_H = 1920, 1080   # 1080p

def read_power_mw():
    with open(POWER_SENSOR) as f:
        return int(f.read().strip()) / 1000

def run():
    from pynq import Overlay, allocate

    print(f"Loading FPGA resizer overlay...", flush=True)
    print(f"  {OVERLAY_PATH}", flush=True)
    ol = Overlay(OVERLAY_PATH)
    resize_ip = ol.resize_accel_0
    dma = ol.axi_dma_0
    print(f"Overlay loaded! IPs: {list(ol.ip_dict.keys())}", flush=True)

    # Allocate contiguous DMA buffers
    in_buf  = allocate(shape=(IN_H, IN_W, 3), dtype=np.uint8)
    out_buf = allocate(shape=(OUT_H, OUT_W, 3), dtype=np.uint8)
    in_buf[:] = np.random.randint(0, 255, (IN_H, IN_W, 3), dtype=np.uint8)
    print(f"DMA buffers allocated: in={in_buf.shape}, out={out_buf.shape}", flush=True)

    # Configure resize IP registers
    resize_ip.write(0x10, IN_W)
    resize_ip.write(0x18, IN_H)
    resize_ip.write(0x20, OUT_W)
    resize_ip.write(0x28, OUT_H)

    def resize_frame():
        resize_ip.write(0x00, 1)          # start
        dma.sendchannel.transfer(in_buf)
        dma.recvchannel.transfer(out_buf)
        dma.sendchannel.wait()
        dma.recvchannel.wait()

    # Warmup
    print(f"\nWarmup ({N_WARMUP} runs)...", flush=True)
    for _ in range(N_WARMUP):
        resize_frame()
    print("Warmup done!", flush=True)

    # Benchmark with power
    print(f"\nBenchmarking ({N_RUNS} runs)...", flush=True)
    times_ms = []
    power_samples = []
    for i in range(N_RUNS):
        p_before = read_power_mw()
        t0 = time.time()
        resize_frame()
        t1 = time.time()
        p_after = read_power_mw()
        times_ms.append((t1 - t0) * 1000)
        power_samples.append((p_before + p_after) / 2)

    avg_ms = sum(times_ms) / len(times_ms)
    avg_power_w = sum(power_samples) / len(power_samples) / 1000
    fps = 1000 / avg_ms
    fps_per_watt = fps / avg_power_w

    print("\n" + "=" * 40)
    print("FPGA RESIZER BENCHMARK RESULTS")
    print("=" * 40)
    print(f"Platform:    KV260 FPGA (PL) via pynq-helloworld")
    print(f"Task:        4K -> 1080p resize (FPGA resize IP + AXI DMA)")
    print(f"Time/frame:  {avg_ms:.1f} ms  (note: +~10ms DMA overhead vs notebook)")
    print(f"FPS:         {fps:.2f}")
    print(f"Power:       {avg_power_w:.2f} W")
    print(f"FPS/Watt:    {fps_per_watt:.2f}")
    print("=" * 40)
    print(f"Notebook:    ~66.8ms, ~14.97 FPS, ~3.51W, ~4.27 FPS/Watt")
    print(f"(Use notebook timing for published results)")

    del in_buf, out_buf
    return avg_ms, fps, avg_power_w, fps_per_watt

if __name__ == "__main__":
    run()
