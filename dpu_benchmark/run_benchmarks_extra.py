#!/usr/bin/env python3
"""
KV260 Extra Benchmarks — MNIST and Image Resizer
Appends results to existing RESULTS.md.

Run order:
  Phase 1 — MNIST DPU + CPU  (10 rounds, DPU overlay)
  Phase 2 — Resizer FPGA + CPU (10 rounds, resizer.bit overlay)

Usage:
  sudo -E bash -c 'source /etc/profile.d/pynq_venv.sh && \
      python3 run_benchmarks_extra.py'          # all 10 rounds
  sudo -E bash -c '... python3 run_benchmarks_extra.py 3'  # 3 rounds
"""

import sys, os, time, threading, csv, subprocess
import numpy as np
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
N_ROUNDS             = int(sys.argv[1]) if len(sys.argv) > 1 else 10
N_FRAMES             = 100
N_WARMUP_DPU         = 10
N_WARMUP_CPU         = 5
N_ORT_THREADS        = 4
PAUSE_BETWEEN_RUNS   = 60
PAUSE_BETWEEN_ROUNDS = 300
IDLE_POWER_DURATION  = 10
POWER_PATH           = "/sys/class/hwmon/hwmon2/power1_input"
SCRIPT_DIR           = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE         = os.path.join(SCRIPT_DIR, "RESULTS.md")
RAW_DIR              = os.path.join(SCRIPT_DIR, "raw_latencies")
RAW_POWER_DIR        = os.path.join(SCRIPT_DIR, "raw_power")
DATA_DIR             = "/home/ubuntu/mnist_data"
MNIST_XMODEL         = os.path.join(SCRIPT_DIR, "mnist/models/dpu_mnist_classifier.xmodel")
MNIST_ONNX           = os.path.join(SCRIPT_DIR, "mnist/models/mnist-12.onnx")
RESIZER_BIT          = "/root/jupyter_notebooks/pynq-resizer/resizer.bit"
IN_W,  IN_H          = 3840, 2160   # 4K input
OUT_W, OUT_H         = 1920, 1080   # 1080p output
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(RAW_POWER_DIR, exist_ok=True)

# ── Sensor helpers (same as run_benchmarks.py) ────────────────────────────────
def read_power_uw():
    try:
        with open(POWER_PATH) as f:
            return float(f.read().strip())
    except Exception:
        return 0.0

def read_temp_c():
    paths = ["/sys/class/hwmon/hwmon0/temp1_input",
             "/sys/class/hwmon/hwmon0/temp2_input",
             "/sys/class/thermal/thermal_zone0/temp"]
    for p in paths:
        try:
            with open(p) as f:
                val = float(f.read().strip())
                if val <= 0: continue
                return val / 1000.0 if val > 1000 else val
        except Exception:
            continue
    return None

def read_cma_free_kb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "CmaFree" in line:
                    return int(line.split()[1])
    except Exception:
        pass
    return None

def read_cpu_freq_mhz():
    try:
        total, count = 0, 0
        for cpu in range(4):
            p = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq"
            if os.path.exists(p):
                with open(p) as f:
                    total += int(f.read().strip())
                    count += 1
        return round(total / count / 1000, 1) if count else None
    except Exception:
        return None

# ── Power sampler ─────────────────────────────────────────────────────────────
class PowerSampler:
    def __init__(self):
        self.samples = []   # (elapsed_s, power_uw)
        self._stop = threading.Event()
        self._thread = None
        self._t0 = None

    def start(self):
        self.samples = []
        self._stop.clear()
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join()
        return self.samples

    def _run(self):
        while not self._stop.is_set():
            elapsed = time.perf_counter() - self._t0
            self.samples.append((elapsed, read_power_uw()))
            self._stop.wait(0.2)

class FreqSampler:
    def __init__(self):
        self.samples = []
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self.samples = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join()
        return float(np.mean(self.samples)) if self.samples else None

    def _run(self):
        while not self._stop.is_set():
            f = read_cpu_freq_mhz()
            if f: self.samples.append(f)
            self._stop.wait(1.0)

def measure_idle_power():
    print(f"  Measuring idle power ({IDLE_POWER_DURATION}s)...", flush=True)
    samples = []
    t_end = time.time() + IDLE_POWER_DURATION
    while time.time() < t_end:
        samples.append(read_power_uw())
        time.sleep(0.2)
    return float(np.mean(samples)) / 1e6 if samples else 0.0

# ── Stats ─────────────────────────────────────────────────────────────────────
def compute_stats(latencies_ms, power_samples, idle_power_w, cpu_freq_mhz,
                  temp_before, temp_after, cma_kb, accuracy_pct=None):
    power_uw = [s[1] for s in power_samples]
    n = len(latencies_ms)
    total_time_s = sum(latencies_ms) / 1000.0
    fps = n / total_time_s

    pw = [v / 1e6 for v in power_uw]
    power_avg = float(np.mean(pw))
    power_std = float(np.std(pw))
    power_min = float(np.min(pw))
    power_max = float(np.max(pw))
    n_power   = len(pw)
    delta_power = max(power_avg - idle_power_w, 0.0)

    fps_per_w_total    = fps / power_avg   if power_avg   > 0 else 0.0
    fps_per_w_delta    = fps / delta_power if delta_power > 0 else 0.0
    mj_per_frame       = (power_avg    * 1000) / fps if fps > 0 else 0.0
    mj_per_frame_delta = (delta_power  * 1000) / fps if fps > 0 and delta_power > 0 else 0.0

    return dict(
        fps=fps,
        mean_lat=float(np.mean(latencies_ms)),
        std_lat=float(np.std(latencies_ms)),
        min_lat=float(np.min(latencies_ms)),
        max_lat=float(np.max(latencies_ms)),
        p95_lat=float(np.percentile(latencies_ms, 95)),
        p99_lat=float(np.percentile(latencies_ms, 99)),
        power_avg=power_avg, power_std=power_std,
        power_min=power_min, power_max=power_max,
        n_power=n_power,
        idle_power=idle_power_w,
        delta_power=delta_power,
        fps_per_w_total=fps_per_w_total,
        fps_per_w_delta=fps_per_w_delta,
        mj_per_frame=mj_per_frame,
        mj_per_frame_delta=mj_per_frame_delta,
        cpu_freq_mhz=cpu_freq_mhz,
        temp_before=temp_before,
        temp_after=temp_after,
        cma_kb=cma_kb,
        n_frames=n,
        accuracy_pct=accuracy_pct,
    )

# ── CSV savers ────────────────────────────────────────────────────────────────
def save_latencies_csv(tag, runtime, round_num, latencies_ms):
    fname = os.path.join(RAW_DIR, f"{tag}_{runtime}.csv")
    file_exists = os.path.exists(fname)
    with open(fname, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["round", "frame", "latency_ms"])
        for i, lat in enumerate(latencies_ms):
            writer.writerow([round_num, i, f"{lat:.4f}"])

def save_power_csv(tag, runtime, round_num, power_samples):
    fname = os.path.join(RAW_POWER_DIR, f"{tag}_{runtime}_r{round_num:02d}.csv")
    with open(fname, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_s", "power_uw"])
        for elapsed, uw in power_samples:
            writer.writerow([f"{elapsed:.3f}", f"{uw:.0f}"])

# ── MNIST data loader ─────────────────────────────────────────────────────────
def load_mnist():
    import gzip
    def load_images(path):
        with gzip.open(path, 'rb') as f:
            f.read(16)
            return np.frombuffer(f.read(), dtype=np.uint8).reshape(-1, 28, 28)
    def load_labels(path):
        with gzip.open(path, 'rb') as f:
            f.read(8)
            return np.frombuffer(f.read(), dtype=np.uint8)
    images = load_images(f"{DATA_DIR}/t10k-images-idx3-ubyte.gz")
    labels = load_labels(f"{DATA_DIR}/t10k-labels-idx1-ubyte.gz")
    return images, labels

# ── MNIST DPU benchmark ───────────────────────────────────────────────────────
def run_mnist_dpu(round_num, ol, images, labels):
    print(f"  Loading MNIST xmodel...", flush=True)
    ol.load_model(MNIST_XMODEL)
    dpu = ol.runner
    in_t  = dpu.get_input_tensors()
    out_t = dpu.get_output_tensors()

    # DPU expects (1,28,28,1) float32, normalised
    dpu_images = (images.astype(np.float32) / 255.0)[:, :, :, np.newaxis]
    in_d  = [np.zeros(t.dims, dtype=np.float32) for t in in_t]
    out_d = [np.zeros(t.dims, dtype=np.float32) for t in out_t]

    temp_before = read_temp_c()
    cma_kb      = read_cma_free_kb()
    idle_power  = measure_idle_power()

    print(f"  Warmup ({N_WARMUP_DPU} frames)...", flush=True)
    for i in range(N_WARMUP_DPU):
        in_d[0][0] = dpu_images[i]
        dpu.wait(dpu.execute_async(in_d, out_d))

    print(f"  Benchmarking ({N_FRAMES} frames)...", flush=True)
    power_sampler = PowerSampler()
    freq_sampler  = FreqSampler()
    latencies, correct = [], 0
    power_sampler.start()
    freq_sampler.start()
    for i in range(N_FRAMES):
        in_d[0][0] = dpu_images[i % len(dpu_images)]
        t0 = time.perf_counter()
        dpu.wait(dpu.execute_async(in_d, out_d))
        latencies.append((time.perf_counter() - t0) * 1000)
        if int(np.argmax(out_d[0][0])) == int(labels[i % len(labels)]):
            correct += 1
    power_samples = power_sampler.stop()
    cpu_freq      = freq_sampler.stop()
    temp_after    = read_temp_c()
    accuracy_pct  = correct / N_FRAMES * 100

    save_latencies_csv("mnist", "dpu", round_num, latencies)
    save_power_csv("mnist", "dpu", round_num, power_samples)
    return compute_stats(latencies, power_samples, idle_power, cpu_freq,
                         temp_before, temp_after, cma_kb, accuracy_pct=accuracy_pct)

# ── MNIST CPU benchmark ───────────────────────────────────────────────────────
def run_mnist_cpu(round_num, images, labels):
    import onnxruntime as ort
    print(f"  Loading MNIST ONNX model...", flush=True)
    sess_opts = ort.SessionOptions()
    sess_opts.intra_op_num_threads = N_ORT_THREADS
    sess_opts.inter_op_num_threads = 1
    sess = ort.InferenceSession(MNIST_ONNX, sess_options=sess_opts,
                                providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    # CPU ONNX model expects (1,1,28,28) float32
    cpu_images = images.astype(np.float32)[:, np.newaxis, :, :] / 255.0

    temp_before = read_temp_c()
    cma_kb      = read_cma_free_kb()
    idle_power  = measure_idle_power()

    print(f"  Warmup ({N_WARMUP_CPU} frames)...", flush=True)
    for i in range(N_WARMUP_CPU):
        sess.run(None, {input_name: cpu_images[i:i+1]})

    print(f"  Benchmarking ({N_FRAMES} frames)...", flush=True)
    power_sampler = PowerSampler()
    freq_sampler  = FreqSampler()
    latencies, correct = [], 0
    power_sampler.start()
    freq_sampler.start()
    for i in range(N_FRAMES):
        t0 = time.perf_counter()
        result = sess.run(None, {input_name: cpu_images[i % len(cpu_images):i % len(cpu_images)+1]})
        latencies.append((time.perf_counter() - t0) * 1000)
        if int(np.argmax(result[0])) == int(labels[i % len(labels)]):
            correct += 1
    power_samples = power_sampler.stop()
    cpu_freq      = freq_sampler.stop()
    temp_after    = read_temp_c()
    accuracy_pct  = correct / N_FRAMES * 100

    save_latencies_csv("mnist", "cpu", round_num, latencies)
    save_power_csv("mnist", "cpu", round_num, power_samples)
    return compute_stats(latencies, power_samples, idle_power, cpu_freq,
                         temp_before, temp_after, cma_kb, accuracy_pct=accuracy_pct)

# ── Resizer FPGA benchmark ────────────────────────────────────────────────────
def run_resizer_fpga(round_num, ol_resizer):
    from pynq import allocate
    resize_ip = ol_resizer.resize_accel_0
    dma       = ol_resizer.axi_dma_0

    in_buf  = allocate(shape=(IN_H, IN_W, 3), dtype=np.uint8)
    out_buf = allocate(shape=(OUT_H, OUT_W, 3), dtype=np.uint8)
    in_buf[:] = np.random.randint(0, 255, (IN_H, IN_W, 3), dtype=np.uint8)

    resize_ip.write(0x10, IN_W);  resize_ip.write(0x18, IN_H)
    resize_ip.write(0x20, OUT_W); resize_ip.write(0x28, OUT_H)

    def resize_frame():
        resize_ip.write(0x00, 1)
        dma.sendchannel.transfer(in_buf)
        dma.recvchannel.transfer(out_buf)
        dma.sendchannel.wait()
        dma.recvchannel.wait()

    temp_before = read_temp_c()
    cma_kb      = read_cma_free_kb()
    idle_power  = measure_idle_power()

    print(f"  Warmup ({N_WARMUP_CPU} frames)...", flush=True)
    for _ in range(N_WARMUP_CPU):
        resize_frame()

    print(f"  Benchmarking ({N_FRAMES} frames)...", flush=True)
    power_sampler = PowerSampler()
    freq_sampler  = FreqSampler()
    latencies = []
    power_sampler.start()
    freq_sampler.start()
    for _ in range(N_FRAMES):
        t0 = time.perf_counter()
        resize_frame()
        latencies.append((time.perf_counter() - t0) * 1000)
    power_samples = power_sampler.stop()
    cpu_freq      = freq_sampler.stop()
    temp_after    = read_temp_c()

    del in_buf, out_buf
    save_latencies_csv("resizer", "fpga", round_num, latencies)
    save_power_csv("resizer", "fpga", round_num, power_samples)
    return compute_stats(latencies, power_samples, idle_power, cpu_freq,
                         temp_before, temp_after, cma_kb)

# ── Resizer CPU benchmark ─────────────────────────────────────────────────────
def run_resizer_cpu(round_num):
    from PIL import Image
    img = Image.fromarray(
        np.random.randint(0, 255, (IN_H, IN_W, 3), dtype=np.uint8))
    out_size = (OUT_W, OUT_H)

    temp_before = read_temp_c()
    cma_kb      = read_cma_free_kb()
    idle_power  = measure_idle_power()

    print(f"  Warmup ({N_WARMUP_CPU} frames)...", flush=True)
    for _ in range(N_WARMUP_CPU):
        img.resize(out_size, Image.BICUBIC)

    print(f"  Benchmarking ({N_FRAMES} frames)...", flush=True)
    power_sampler = PowerSampler()
    freq_sampler  = FreqSampler()
    latencies = []
    power_sampler.start()
    freq_sampler.start()
    for _ in range(N_FRAMES):
        t0 = time.perf_counter()
        img.resize(out_size, Image.BICUBIC)
        latencies.append((time.perf_counter() - t0) * 1000)
    power_samples = power_sampler.stop()
    cpu_freq      = freq_sampler.stop()
    temp_after    = read_temp_c()

    save_latencies_csv("resizer", "cpu", round_num, latencies)
    save_power_csv("resizer", "cpu", round_num, power_samples)
    return compute_stats(latencies, power_samples, idle_power, cpu_freq,
                         temp_before, temp_after, cma_kb)

# ── RESULTS.md helpers ────────────────────────────────────────────────────────
def fmt(v, d=3):
    if v is None: return "N/A"
    return f"{v:.{d}f}"

MNIST_PERF_HEADER = (
    "| Round | Runtime | FPS | Accuracy_pct | Lat_mean_ms | Lat_std_ms | "
    "Lat_min_ms | Lat_max_ms | Lat_p95_ms | Lat_p99_ms | "
    "Power_avg_W | Power_std_W | Idle_W | Delta_W | "
    "FPS/W_total | FPS/W_delta | mJ/frame | mJ/frame_delta |\n"
    "|-------|---------|-----|--------------|-------------|------------|"
    "------------|------------|------------|------------|"
    "------------|------------|--------|---------|"
    "------------|------------|---------|----------------|"
)

RESIZER_PERF_HEADER = (
    "| Round | Runtime | FPS | Lat_mean_ms | Lat_std_ms | "
    "Lat_min_ms | Lat_max_ms | Lat_p95_ms | Lat_p99_ms | "
    "Power_avg_W | Power_std_W | Idle_W | Delta_W | "
    "FPS/W_total | FPS/W_delta | mJ/frame | mJ/frame_delta |\n"
    "|-------|---------|-----|-------------|------------|"
    "------------|------------|------------|------------|"
    "------------|------------|--------|---------|"
    "------------|------------|---------|----------------|"
)

SYS_HEADER = (
    "| Round | Runtime | Temp_before_C | Temp_after_C | CMA_free_kB | CPU_freq_MHz |\n"
    "|-------|---------|---------------|--------------|------------|-------------|"
)

def mnist_perf_row(round_num, runtime, r):
    return (f"| {round_num} | {runtime.upper()} | {fmt(r['fps'],2)} | "
            f"{fmt(r['accuracy_pct'],1)} | "
            f"{fmt(r['mean_lat'],3)} | {fmt(r['std_lat'],3)} | "
            f"{fmt(r['min_lat'],3)} | {fmt(r['max_lat'],3)} | "
            f"{fmt(r['p95_lat'],3)} | {fmt(r['p99_lat'],3)} | "
            f"{fmt(r['power_avg'],3)} | {fmt(r['power_std'],3)} | "
            f"{fmt(r['idle_power'],3)} | {fmt(r['delta_power'],3)} | "
            f"{fmt(r['fps_per_w_total'],3)} | {fmt(r['fps_per_w_delta'],3)} | "
            f"{fmt(r['mj_per_frame'],3)} | {fmt(r['mj_per_frame_delta'],3)} |")

def resizer_perf_row(round_num, runtime, r):
    return (f"| {round_num} | {runtime.upper()} | {fmt(r['fps'],2)} | "
            f"{fmt(r['mean_lat'],2)} | {fmt(r['std_lat'],2)} | "
            f"{fmt(r['min_lat'],2)} | {fmt(r['max_lat'],2)} | "
            f"{fmt(r['p95_lat'],2)} | {fmt(r['p99_lat'],2)} | "
            f"{fmt(r['power_avg'],3)} | {fmt(r['power_std'],3)} | "
            f"{fmt(r['idle_power'],3)} | {fmt(r['delta_power'],3)} | "
            f"{fmt(r['fps_per_w_total'],3)} | {fmt(r['fps_per_w_delta'],3)} | "
            f"{fmt(r['mj_per_frame'],3)} | {fmt(r['mj_per_frame_delta'],3)} |")

def sys_row(round_num, runtime, r):
    return (f"| {round_num} | {runtime.upper()} | "
            f"{fmt(r['temp_before'],1)} | {fmt(r['temp_after'],1)} | "
            f"{r['cma_kb'] if r['cma_kb'] else 'N/A'} | "
            f"{fmt(r['cpu_freq_mhz'],1)} |")

def append_to_results(section_marker, perf_row_str, sys_row_str):
    """Insert rows under the correct section markers in RESULTS.md."""
    with open(RESULTS_FILE, "r") as f:
        content = f.read()

    def insert_row(content, marker, row):
        idx = content.find(marker)
        if idx == -1:
            return content
        markers = [content.find("\n### ", idx+1), content.find("\n## ", idx+1)]
        insert_at = min(x for x in markers if x > idx) if any(x > idx for x in markers) else len(content)
        before = content[:insert_at].rstrip("\n")
        return before + "\n" + row + "\n" + content[insert_at:]

    content = insert_row(content, f"### {section_marker} — performance", perf_row_str)
    content = insert_row(content, f"### {section_marker} — system",      sys_row_str)

    with open(RESULTS_FILE, "w") as f:
        f.write(content)

def write_section_header(title, perf_header, sys_header, note=""):
    with open(RESULTS_FILE, "a") as f:
        f.write(f"\n---\n\n## {title}\n\n")
        if note:
            f.write(f"> {note}\n\n")
        model_name = title.split()[0].lower()
        f.write(f"### {model_name} — performance\n\n")
        f.write(perf_header + "\n")
        f.write(f"\n### {model_name} — system\n\n")
        f.write(sys_header + "\n")

def write_summary_section(title, model_name, all_results):
    with open(RESULTS_FILE, "a") as f:
        f.write(f"\n### {title} — Summary (Mean ± Std Dev)\n\n")
        if model_name == "mnist":
            f.write("| Runtime | FPS | Accuracy_pct | Lat_mean_ms | Power_avg_W | "
                    "Delta_W | FPS/W_total | FPS/W_delta | mJ/frame |\n")
            f.write("|---------|-----|--------------|-------------|------------|"
                    "---------|------------|------------|----------|\n")
        else:
            f.write("| Runtime | FPS | Lat_mean_ms | Power_avg_W | "
                    "Delta_W | FPS/W_total | FPS/W_delta | mJ/frame |\n")
            f.write("|---------|-----|-------------|------------|"
                    "---------|------------|------------|----------|\n")

        for runtime in (["dpu", "cpu"] if model_name == "mnist" else ["fpga", "cpu"]):
            runs = all_results.get(runtime, [])
            if not runs: continue
            def m(k): return float(np.mean([r[k] for r in runs]))
            def s(k): return float(np.std([r[k]  for r in runs]))
            rt = runtime.upper()
            if model_name == "mnist":
                f.write(f"| {rt} | {m('fps'):.2f}±{s('fps'):.2f} | "
                        f"{m('accuracy_pct'):.1f}±{s('accuracy_pct'):.1f} | "
                        f"{m('mean_lat'):.3f}±{s('mean_lat'):.3f} | "
                        f"{m('power_avg'):.3f}±{s('power_avg'):.3f} | "
                        f"{m('delta_power'):.3f}±{s('delta_power'):.3f} | "
                        f"{m('fps_per_w_total'):.3f}±{s('fps_per_w_total'):.3f} | "
                        f"{m('fps_per_w_delta'):.3f}±{s('fps_per_w_delta'):.3f} | "
                        f"{m('mj_per_frame'):.3f}±{s('mj_per_frame'):.3f} |\n")
            else:
                f.write(f"| {rt} | {m('fps'):.2f}±{s('fps'):.2f} | "
                        f"{m('mean_lat'):.2f}±{s('mean_lat'):.2f} | "
                        f"{m('power_avg'):.3f}±{s('power_avg'):.3f} | "
                        f"{m('delta_power'):.3f}±{s('delta_power'):.3f} | "
                        f"{m('fps_per_w_total'):.3f}±{s('fps_per_w_total'):.3f} | "
                        f"{m('fps_per_w_delta'):.3f}±{s('fps_per_w_delta'):.3f} | "
                        f"{m('mj_per_frame'):.3f}±{s('mj_per_frame'):.3f} |\n")
        n = len(list(all_results.values())[0]) if all_results else 0
        f.write(f"\n_Summary from {n} rounds._\n")

def pause(seconds, reason):
    print(f"\n  [{reason}] cooling down {seconds}s...", flush=True)
    for remaining in range(seconds, 0, -30):
        print(f"    {remaining}s remaining...", flush=True)
        time.sleep(min(30, remaining))
    print(f"  Done cooling.", flush=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    from pynq_dpu import DpuOverlay

    print(f"\nKV260 Extra Benchmarks — MNIST + Resizer", flush=True)
    print(f"Rounds: {N_ROUNDS} | Frames: {N_FRAMES} | "
          f"Run pause: {PAUSE_BETWEEN_RUNS}s | Round pause: {PAUSE_BETWEEN_ROUNDS}s", flush=True)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", flush=True)

    # ── PHASE 1: MNIST ────────────────────────────────────────────────────────
    print("Loading MNIST test data...", flush=True)
    images, labels = load_mnist()
    print(f"  {len(images)} test images loaded.\n", flush=True)

    print("Loading DPU overlay for MNIST...", flush=True)
    ol_dpu = DpuOverlay("dpu.bit")
    print("DPU overlay loaded.\n", flush=True)

    write_section_header(
        "MNIST Results",
        MNIST_PERF_HEADER, SYS_HEADER,
        note="MNIST digit classifier. DPU: dpu_mnist_classifier.xmodel (INT8). "
             "CPU: mnist-12.onnx (FP32, ORT 4 threads). "
             "Real MNIST test-set images used (not random). Accuracy measured per round."
    )

    mnist_results = {"dpu": [], "cpu": []}
    for round_num in range(1, N_ROUNDS + 1):
        print(f"\n{'='*60}", flush=True)
        print(f"MNIST ROUND {round_num}/{N_ROUNDS}  [{datetime.now().strftime('%H:%M:%S')}]", flush=True)
        print(f"{'='*60}", flush=True)

        for i, (runtime, bench_fn) in enumerate([
            ("dpu", lambda rn: run_mnist_dpu(rn, ol_dpu, images, labels)),
            ("cpu", lambda rn: run_mnist_cpu(rn, images, labels)),
        ]):
            print(f"\n── MNIST {runtime.upper()}  round {round_num} "
                  f"[{datetime.now().strftime('%H:%M:%S')}]", flush=True)
            try:
                r = bench_fn(round_num)
                mnist_results[runtime].append(r)
                append_to_results("mnist",
                                  mnist_perf_row(round_num, runtime, r),
                                  sys_row(round_num, runtime, r))
                print(f"  ✓ FPS:{r['fps']:.1f}  Acc:{fmt(r['accuracy_pct'],1)}%  "
                      f"Lat:{r['mean_lat']:.3f}±{r['std_lat']:.3f}ms  "
                      f"Power:{r['power_avg']:.2f}W(Δ:{r['delta_power']:.2f}W)  "
                      f"FPS/W:{r['fps_per_w_total']:.2f}(Δ:{r['fps_per_w_delta']:.2f})  "
                      f"Temp:{fmt(r['temp_before'],1)}→{fmt(r['temp_after'],1)}°C", flush=True)
                if i == 0:  # pause between DPU and CPU
                    pause(PAUSE_BETWEEN_RUNS, "mnist dpu→cpu")
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                import traceback; traceback.print_exc()

        print(f"\nMNIST Round {round_num} complete. [{datetime.now().strftime('%H:%M:%S')}]", flush=True)
        if round_num < N_ROUNDS:
            pause(PAUSE_BETWEEN_ROUNDS, f"end of MNIST round {round_num}")

    write_summary_section("MNIST", "mnist", mnist_results)
    del ol_dpu
    print("\nDPU overlay released.\n", flush=True)

    # ── PHASE 2: RESIZER ──────────────────────────────────────────────────────
    if not os.path.exists(RESIZER_BIT):
        print(f"WARNING: resizer.bit not found at {RESIZER_BIT} — skipping resizer benchmarks.", flush=True)
    else:
        from pynq import Overlay

        pause(PAUSE_BETWEEN_ROUNDS, "MNIST→Resizer transition")

        print("Loading resizer overlay...", flush=True)
        ol_resizer = Overlay(RESIZER_BIT)
        print("Resizer overlay loaded.\n", flush=True)

        write_section_header(
            "Resizer Results",
            RESIZER_PERF_HEADER, SYS_HEADER,
            note="Image resize 4K (3840x2160) → 1080p (1920x1080). "
                 "FPGA: custom resize IP via AXI DMA (resizer.bit from pynq-helloworld). "
                 "CPU: PIL BICUBIC. "
                 "Note: FPGA latency includes ~10ms Python DMA overhead not present in Jupyter notebook timing."
        )

        resizer_results = {"fpga": [], "cpu": []}
        for round_num in range(1, N_ROUNDS + 1):
            print(f"\n{'='*60}", flush=True)
            print(f"RESIZER ROUND {round_num}/{N_ROUNDS}  [{datetime.now().strftime('%H:%M:%S')}]", flush=True)
            print(f"{'='*60}", flush=True)

            for i, (runtime, bench_fn) in enumerate([
                ("fpga", lambda rn: run_resizer_fpga(rn, ol_resizer)),
                ("cpu",  lambda rn: run_resizer_cpu(rn)),
            ]):
                print(f"\n── RESIZER {runtime.upper()}  round {round_num} "
                      f"[{datetime.now().strftime('%H:%M:%S')}]", flush=True)
                try:
                    r = bench_fn(round_num)
                    resizer_results[runtime].append(r)
                    append_to_results("resizer",
                                      resizer_perf_row(round_num, runtime, r),
                                      sys_row(round_num, runtime, r))
                    print(f"  ✓ FPS:{r['fps']:.2f}  "
                          f"Lat:{r['mean_lat']:.1f}±{r['std_lat']:.1f}ms  "
                          f"Power:{r['power_avg']:.2f}W(Δ:{r['delta_power']:.2f}W)  "
                          f"FPS/W:{r['fps_per_w_total']:.3f}(Δ:{r['fps_per_w_delta']:.3f})  "
                          f"Temp:{fmt(r['temp_before'],1)}→{fmt(r['temp_after'],1)}°C", flush=True)
                    if i == 0:
                        pause(PAUSE_BETWEEN_RUNS, "resizer fpga→cpu")
                except Exception as e:
                    print(f"  ERROR: {e}", flush=True)
                    import traceback; traceback.print_exc()

            print(f"\nResizer Round {round_num} complete. [{datetime.now().strftime('%H:%M:%S')}]", flush=True)
            if round_num < N_ROUNDS:
                pause(PAUSE_BETWEEN_ROUNDS, f"end of Resizer round {round_num}")

        write_summary_section("Resizer", "resizer", resizer_results)

    print(f"\n{'='*60}", flush=True)
    print(f"ALL DONE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Results appended to: {RESULTS_FILE}", flush=True)

if __name__ == "__main__":
    main()
