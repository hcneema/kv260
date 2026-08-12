#!/usr/bin/env python3
"""
KV260 CPU vs DPU Interleaved Benchmark — Comprehensive Data Collection
Runs N_ROUNDS of: ResNet50 DPU/CPU, InceptionV1 DPU/CPU, YOLOv3 DPU/CPU
100 frames per run. Collects performance, power, thermal, and system state.

Output:
  RESULTS.md          — performance + system state tables, updated after each run
  raw_latencies/      — per-frame latency CSV for every run (appended across rounds)
  raw_power/          — timestamped power waveform CSV per run per round

Usage:
  sudo -E python3 run_benchmarks.py             # all 10 rounds
  sudo -E python3 run_benchmarks.py 2           # 2 rounds only
  sudo -E python3 run_benchmarks.py 8 3         # 8 rounds starting at round 3
"""

import sys, os, time, threading, csv, subprocess, platform
import numpy as np
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
N_ROUNDS            = int(sys.argv[1]) if len(sys.argv) > 1 else 10
START_ROUND         = int(sys.argv[2]) if len(sys.argv) > 2 else 1
N_FRAMES            = 100
N_WARMUP_DPU        = 10
N_WARMUP_CPU        = 3
N_ORT_THREADS       = 4    # explicit — match physical CPU count, important for reproducibility
PAUSE_BETWEEN_RUNS  = 60   # seconds — cooling between each individual run
PAUSE_BETWEEN_ROUNDS= 300  # seconds — longer cool-down between rounds
IDLE_POWER_DURATION = 10   # seconds — baseline power measured before each run
POWER_PATH          = "/sys/class/hwmon/hwmon2/power1_input"
SCRIPT_DIR          = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE        = os.path.join(SCRIPT_DIR, "RESULTS.md")
RAW_DIR             = os.path.join(SCRIPT_DIR, "raw_latencies")
RAW_POWER_DIR       = os.path.join(SCRIPT_DIR, "raw_power")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(RAW_POWER_DIR, exist_ok=True)

MODELS = {
    "resnet50": {
        "dpu_xmodel": os.path.join(SCRIPT_DIR, "resnet50/models/dpu_resnet50.xmodel"),
        "cpu_onnx":   os.path.join(SCRIPT_DIR, "resnet50/models/resnet50-v1-7.onnx"),
        "dpu_input":  (1, 224, 224, 3),
        "cpu_inputs": {"data": (1, 3, 224, 224)},
    },
    "inceptionv1": {
        "dpu_xmodel": os.path.join(SCRIPT_DIR, "inceptionv1/models/dpu_tf_inceptionv1.xmodel"),
        "cpu_onnx":   os.path.join(SCRIPT_DIR, "inceptionv1/models/inception-v1-9.onnx"),
        "dpu_input":  (1, 224, 224, 3),
        "cpu_inputs": {"data_0": (1, 3, 224, 224)},
    },
    "yolov3": {
        "dpu_xmodel": os.path.join(SCRIPT_DIR, "yolov3/models/tf_yolov3_voc.xmodel"),
        "cpu_onnx":   os.path.join(SCRIPT_DIR, "yolov3/models/yolov3-10.onnx"),
        "dpu_input":  (1, 416, 416, 3),
        "cpu_inputs": {"input_1": (1, 3, 416, 416), "image_shape": (1, 2)},
    },
}

RUN_ORDER = [
    ("resnet50",    "dpu"),
    ("resnet50",    "cpu"),
    ("inceptionv1", "dpu"),
    ("inceptionv1", "cpu"),
    ("yolov3",      "dpu"),
    ("yolov3",      "cpu"),
]

# ── Sensor readers ────────────────────────────────────────────────────────────
def read_power_uw():
    try:
        with open(POWER_PATH) as f:
            return float(f.read().strip())
    except Exception:
        return 0.0

def read_temp_c():
    paths = [
        "/sys/class/hwmon/hwmon0/temp1_input",
        "/sys/class/hwmon/hwmon0/temp2_input",
        "/sys/class/hwmon/hwmon1/temp1_input",
        "/sys/bus/iio/devices/iio:device0/in_temp0_ps_temp_raw",
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
    ]
    for p in paths:
        try:
            with open(p) as f:
                val = float(f.read().strip())
                if val <= 0:
                    continue
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

def read_dpu_cu_usage():
    """Read the DPU compute unit invocation counter from xbutil examine."""
    try:
        out = subprocess.check_output(["xbutil", "examine"], text=True,
                                      stderr=subprocess.DEVNULL, timeout=10)
        for line in out.splitlines():
            if "DPUCZDX8G" in line:
                parts = line.split()
                # Format: Index  Name  Base_Address  Usage  Status
                # e.g.:   0  DPUCZDX8G:DPUCZDX8G_1  0x80010000  2071  (DONE|IDLE)
                return int(parts[3])
    except Exception:
        return None
    return None

# ── Power sampler (background thread, records timestamps) ─────────────────────
class PowerSampler:
    def __init__(self):
        self.samples = []   # list of (elapsed_s, power_uw)
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
        return self.samples  # list of (elapsed_s, power_uw)

    def _run(self):
        while not self._stop.is_set():
            elapsed = time.perf_counter() - self._t0
            self.samples.append((elapsed, read_power_uw()))
            self._stop.wait(0.2)

def measure_idle_power():
    """Sample power for IDLE_POWER_DURATION seconds, return avg W."""
    print(f"  Measuring idle power ({IDLE_POWER_DURATION}s)...", flush=True)
    samples = []
    t_end = time.time() + IDLE_POWER_DURATION
    while time.time() < t_end:
        samples.append(read_power_uw())
        time.sleep(0.2)
    return float(np.mean(samples)) / 1e6 if samples else 0.0

# ── CPU freq sampler (background thread during run) ───────────────────────────
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

# ── Stats from raw data ───────────────────────────────────────────────────────
def compute_stats(latencies_ms, power_samples, idle_power_w, cpu_freq_mhz,
                  temp_before, temp_after, cma_kb, cu_usage_delta=None):
    # power_samples is list of (elapsed_s, power_uw)
    power_uw = [s[1] for s in power_samples]

    n = len(latencies_ms)
    total_time_s = sum(latencies_ms) / 1000.0
    fps = n / total_time_s

    power_w_samples = [v / 1e6 for v in power_uw]
    power_avg = float(np.mean(power_w_samples))
    power_std = float(np.std(power_w_samples))
    power_min = float(np.min(power_w_samples))
    power_max = float(np.max(power_w_samples))
    n_power   = len(power_w_samples)

    delta_power = max(power_avg - idle_power_w, 0.0)

    fps_per_w_total    = fps / power_avg  if power_avg   > 0 else 0.0
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
        power_avg=power_avg,
        power_std=power_std,
        power_min=power_min,
        power_max=power_max,
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
        cu_usage_delta=cu_usage_delta,
    )

# ── Save per-frame latencies to CSV ──────────────────────────────────────────
def save_latencies_csv(model_name, runtime, round_num, latencies_ms):
    fname = os.path.join(RAW_DIR, f"{model_name}_{runtime}.csv")
    file_exists = os.path.exists(fname)
    with open(fname, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["round", "frame", "latency_ms"])
        for i, lat in enumerate(latencies_ms):
            writer.writerow([round_num, i, f"{lat:.4f}"])

# ── Save timestamped power waveform to CSV ────────────────────────────────────
def save_power_csv(model_name, runtime, round_num, power_samples):
    # power_samples: list of (elapsed_s, power_uw)
    fname = os.path.join(RAW_POWER_DIR, f"{model_name}_{runtime}_r{round_num:02d}.csv")
    with open(fname, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_s", "power_uw"])
        for elapsed, uw in power_samples:
            writer.writerow([f"{elapsed:.3f}", f"{uw:.0f}"])

# ── DPU benchmark ─────────────────────────────────────────────────────────────
def run_dpu(model_name, round_num, ol):
    cfg = MODELS[model_name]
    print(f"  Loading xmodel...", flush=True)
    ol.load_model(cfg["dpu_xmodel"])
    dpu = ol.runner
    inp = [np.random.randn(*t.dims).astype(np.float32) for t in dpu.get_input_tensors()]
    out = [np.zeros(t.dims, dtype=np.float32) for t in dpu.get_output_tensors()]

    temp_before   = read_temp_c()
    cma_kb        = read_cma_free_kb()
    idle_power    = measure_idle_power()
    cu_before     = read_dpu_cu_usage()

    print(f"  Warmup ({N_WARMUP_DPU} frames)...", flush=True)
    for _ in range(N_WARMUP_DPU):
        dpu.wait(dpu.execute_async(inp, out))

    print(f"  Benchmarking ({N_FRAMES} frames)...", flush=True)
    power_sampler = PowerSampler()
    freq_sampler  = FreqSampler()
    latencies = []
    power_sampler.start()
    freq_sampler.start()
    for _ in range(N_FRAMES):
        t0 = time.perf_counter()
        dpu.wait(dpu.execute_async(inp, out))
        latencies.append((time.perf_counter() - t0) * 1000)
    power_samples = power_sampler.stop()
    cpu_freq      = freq_sampler.stop()
    temp_after    = read_temp_c()
    cu_after      = read_dpu_cu_usage()

    cu_delta = (cu_after - cu_before) if (cu_before is not None and cu_after is not None) else None

    save_latencies_csv(model_name, "dpu", round_num, latencies)
    save_power_csv(model_name, "dpu", round_num, power_samples)

    return compute_stats(latencies, power_samples, idle_power, cpu_freq,
                         temp_before, temp_after, cma_kb, cu_usage_delta=cu_delta)

# ── CPU benchmark ─────────────────────────────────────────────────────────────
def run_cpu(model_name, round_num):
    import onnxruntime as ort
    cfg = MODELS[model_name]
    print(f"  Loading ONNX model...", flush=True)

    sess_opts = ort.SessionOptions()
    sess_opts.intra_op_num_threads = N_ORT_THREADS
    sess_opts.inter_op_num_threads = 1
    sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    sess = ort.InferenceSession(cfg["cpu_onnx"], sess_options=sess_opts,
                                providers=["CPUExecutionProvider"])
    session_inputs = [i.name for i in sess.get_inputs()]

    # Build feed dict
    feed = {}
    for name, shape in cfg["cpu_inputs"].items():
        key = name if name in session_inputs else session_inputs[min(len(feed), len(session_inputs)-1)]
        if shape == (1, 2) or "shape" in name.lower():
            feed[key] = np.array([[416, 416]], dtype=np.float32)
        else:
            feed[key] = np.random.randn(*shape).astype(np.float32)
    for sname in session_inputs:
        if sname not in feed:
            feed[sname] = np.array([[416, 416]], dtype=np.float32)

    temp_before = read_temp_c()
    cma_kb      = read_cma_free_kb()
    idle_power  = measure_idle_power()

    print(f"  Warmup ({N_WARMUP_CPU} frames)...", flush=True)
    for _ in range(N_WARMUP_CPU):
        sess.run(None, feed)

    print(f"  Benchmarking ({N_FRAMES} frames)...", flush=True)
    power_sampler = PowerSampler()
    freq_sampler  = FreqSampler()
    latencies = []
    power_sampler.start()
    freq_sampler.start()
    for _ in range(N_FRAMES):
        t0 = time.perf_counter()
        sess.run(None, feed)
        latencies.append((time.perf_counter() - t0) * 1000)
    power_samples = power_sampler.stop()
    cpu_freq      = freq_sampler.stop()
    temp_after    = read_temp_c()

    save_latencies_csv(model_name, "cpu", round_num, latencies)
    save_power_csv(model_name, "cpu", round_num, power_samples)

    return compute_stats(latencies, power_samples, idle_power, cpu_freq,
                         temp_before, temp_after, cma_kb, cu_usage_delta=None)

# ── Model graph metadata (one-time, after overlay loaded) ────────────────────
def collect_model_metadata(ol):
    """Load each xmodel and extract op breakdown + quantization info from XIR graph."""
    meta = {}
    for model_name, cfg in MODELS.items():
        xmodel = cfg["dpu_xmodel"]
        if not os.path.exists(xmodel):
            meta[model_name] = {"error": "xmodel not found"}
            continue
        try:
            ol.load_model(xmodel)
            g = ol.graph
            all_ops = list(g.get_ops())
            op_counts = {}
            for op in all_ops:
                t = op.get_type()
                op_counts[t] = op_counts.get(t, 0) + 1

            # Input tensor quantization attributes
            inp_tensors = ol.runner.get_input_tensors()
            out_tensors = ol.runner.get_output_tensors()
            quant_info = []
            for t in inp_tensors:
                try:
                    attrs = t.get_attrs()
                    quant_info.append({
                        "tensor": t.name,
                        "role": "input",
                        "dims": list(t.dims),
                        "dtype": str(t.dtype),
                        "bit_width": attrs.get("bit_width"),
                        "if_signed": attrs.get("if_signed"),
                        "fix_point": attrs.get("fix_point"),
                        "round_mode": attrs.get("round_mode"),
                    })
                except Exception:
                    quant_info.append({"tensor": t.name, "role": "input", "dims": list(t.dims)})
            for t in out_tensors:
                try:
                    attrs = t.get_attrs()
                    quant_info.append({
                        "tensor": t.name,
                        "role": "output",
                        "dims": list(t.dims),
                        "dtype": str(t.dtype),
                        "bit_width": attrs.get("bit_width"),
                        "if_signed": attrs.get("if_signed"),
                        "fix_point": attrs.get("fix_point"),
                    })
                except Exception:
                    quant_info.append({"tensor": t.name, "role": "output", "dims": list(t.dims)})

            meta[model_name] = {
                "total_ops": len(all_ops),
                "op_counts": op_counts,
                "quant_info": quant_info,
            }
            print(f"  {model_name}: {len(all_ops)} ops, "
                  f"{op_counts.get('conv2d-fix',0)} conv2d-fix", flush=True)
        except Exception as e:
            meta[model_name] = {"error": str(e)}
    return meta

def get_mem_bandwidth_mb_s():
    """Estimate sequential DRAM read bandwidth using numpy (128 MB array sum)."""
    try:
        arr = np.zeros(128 * 1024 * 1024 // 8, dtype=np.float64)  # 128 MB
        t0 = time.perf_counter()
        _ = np.sum(arr)
        elapsed = time.perf_counter() - t0
        return round(128.0 / elapsed, 1)
    except Exception:
        return None

# ── RESULTS.md helpers ────────────────────────────────────────────────────────
PERF_HEADER = ("| Round | Runtime | FPS | Lat_mean_ms | Lat_std_ms | "
               "Lat_min_ms | Lat_max_ms | Lat_p95_ms | Lat_p99_ms | "
               "Power_avg_W | Power_std_W | Power_min_W | Power_max_W | "
               "Idle_W | Delta_W | FPS/W_total | FPS/W_delta | "
               "mJ/frame | mJ/frame_delta | n_power | DPU_CU_delta |\n"
               "|-------|---------|-----|-------------|------------|"
               "------------|------------|------------|------------|"
               "------------|------------|------------|------------|"
               "--------|---------|------------|------------|"
               "---------|---------------|---------|-------------|")

SYS_HEADER = ("| Round | Runtime | Temp_before_C | Temp_after_C | "
              "CMA_free_kB | CPU_freq_MHz |\n"
              "|-------|---------|---------------|--------------|"
              "------------|-------------|")

def fmt(v, decimals=3):
    if v is None: return "N/A"
    return f"{v:.{decimals}f}"

def perf_row(round_num, runtime, r):
    cu = str(r['cu_usage_delta']) if r['cu_usage_delta'] is not None else "N/A"
    return (f"| {round_num} | {runtime.upper()} | {fmt(r['fps'],2)} | "
            f"{fmt(r['mean_lat'],2)} | {fmt(r['std_lat'],2)} | "
            f"{fmt(r['min_lat'],2)} | {fmt(r['max_lat'],2)} | "
            f"{fmt(r['p95_lat'],2)} | {fmt(r['p99_lat'],2)} | "
            f"{fmt(r['power_avg'],3)} | {fmt(r['power_std'],3)} | "
            f"{fmt(r['power_min'],3)} | {fmt(r['power_max'],3)} | "
            f"{fmt(r['idle_power'],3)} | {fmt(r['delta_power'],3)} | "
            f"{fmt(r['fps_per_w_total'],3)} | {fmt(r['fps_per_w_delta'],3)} | "
            f"{fmt(r['mj_per_frame'],3)} | {fmt(r['mj_per_frame_delta'],3)} | "
            f"{r['n_power']} | {cu} |")

def sys_row(round_num, runtime, r):
    return (f"| {round_num} | {runtime.upper()} | "
            f"{fmt(r['temp_before'],1)} | {fmt(r['temp_after'],1)} | "
            f"{r['cma_kb'] if r['cma_kb'] else 'N/A'} | "
            f"{fmt(r['cpu_freq_mhz'],1)} |")

def get_board_info():
    """Collect one-time board hardware info."""
    def sh(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:
            return "N/A"

    return {
        "kernel":           platform.release(),
        "xrt":              sh("dpkg-query -W -f='${Version}' xrt"),
        "pynq":             sh("/usr/local/share/pynq-venv/bin/python3 -c 'import pynq; print(pynq.__version__)'"),
        "pynq_dpu":         sh("/usr/local/share/pynq-venv/bin/python3 -c 'import pynq_dpu; print(pynq_dpu.__version__)'"),
        "ort":              sh("/usr/local/share/pynq-venv/bin/python3 -c 'import onnxruntime; print(onnxruntime.__version__)'"),
        "cpu_governor":     sh("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "cpu_max_mhz":      sh("cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq | awk '{printf \"%.0f\", $1/1000}'"),
        "cpu_min_mhz":      sh("cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq | awk '{printf \"%.0f\", $1/1000}'"),
        "ram_mb":           sh("grep MemTotal /proc/meminfo | awk '{printf \"%.0f\", $2/1024}'"),
        "cma_total_mb":     sh("grep CmaTotal /proc/meminfo | awk '{printf \"%.0f\", $2/1024}'"),
        "xbutil":           sh("xbutil examine 2>/dev/null | grep -A3 'Devices present'"),
        "dpu_arch":         sh("cat /sys/bus/platform/devices/*/ip_layout 2>/dev/null | strings | grep DPUCZDX8G | head -1"),
        "sd_model":         sh("cat /sys/block/mmcblk0/device/name 2>/dev/null"),
        "ort_intra_threads": str(N_ORT_THREADS),
        "ort_inter_threads": "1",
        "ort_exec_mode":    "ORT_SEQUENTIAL",
        "ort_graph_opt":    "ORT_ENABLE_ALL",
        "idle_power_w":     f"{measure_idle_power():.3f}",
        "idle_temp_c":      fmt(read_temp_c(), 1),
        # SD card sequential read speed (hdparm -t reads ~128MB from raw device)
        "sd_read_mb_s":     sh("hdparm -t /dev/mmcblk0 2>/dev/null | grep -oP '[0-9.]+ MB/sec' | head -1"),
        # DRAM sequential read bandwidth via numpy
        "dram_bw_mb_s":     str(get_mem_bandwidth_mb_s()),
    }

def write_header(f, info, start_round, end_round, model_meta=None):
    f.write("# KV260 CPU vs DPU Benchmark — Raw Results\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
    f.write(f"Rounds: {start_round}–{end_round}  \n")
    f.write(f"Frames per run: {N_FRAMES}  \n")
    f.write(f"Pause between runs: {PAUSE_BETWEEN_RUNS}s  \n")
    f.write(f"Pause between rounds: {PAUSE_BETWEEN_ROUNDS}s  \n\n")

    f.write("## Platform\n\n")
    f.write(f"- **Board**: AMD Kria KV260 revB\n")
    f.write(f"- **OS**: Ubuntu 22.04.4 LTS\n")
    f.write(f"- **Kernel**: {info['kernel']}\n")
    f.write(f"- **CPU**: ARM Cortex-A53 quad-core, max {info['cpu_max_mhz']} MHz, "
            f"min {info['cpu_min_mhz']} MHz, governor: {info['cpu_governor']}\n")
    f.write(f"- **DPU**: DPUCZDX8G B512\n")
    f.write(f"- **DPU arch string**: {info['dpu_arch']}\n")
    f.write(f"- **RAM**: {info['ram_mb']} MB total\n")
    f.write(f"- **CMA**: {info['cma_total_mb']} MB total allocation\n")
    f.write(f"- **XRT**: {info['xrt']}\n")
    f.write(f"- **PYNQ**: {info['pynq']}\n")
    f.write(f"- **pynq-dpu**: {info['pynq_dpu']}\n")
    f.write(f"- **ONNX Runtime**: {info['ort']}\n")
    f.write(f"- **ORT CPU threads**: intra={info['ort_intra_threads']}, inter={info['ort_inter_threads']}\n")
    f.write(f"- **ORT execution mode**: {info['ort_exec_mode']}\n")
    f.write(f"- **ORT graph optimization**: {info['ort_graph_opt']}\n")
    f.write(f"- **SD card**: {info['sd_model']}\n")
    f.write(f"- **SD card sequential read**: {info['sd_read_mb_s']}\n")
    f.write(f"- **DRAM sequential read bandwidth**: {info['dram_bw_mb_s']} MB/s (numpy 128 MB sum)\n")
    f.write(f"- **Power sensor**: INA260 @ /sys/class/hwmon/hwmon2/power1_input\n")
    f.write(f"- **Power sampling interval**: ~200 ms\n")
    f.write(f"- **Idle power at start**: {info['idle_power_w']} W\n")
    f.write(f"- **Idle temp at start**: {info['idle_temp_c']} °C\n")
    f.write(f"- **DPU warmup frames**: {N_WARMUP_DPU}\n")
    f.write(f"- **CPU warmup frames**: {N_WARMUP_CPU}\n")
    f.write(f"- **Raw power waveforms**: raw_power/{{model}}_{{runtime}}_r{{round:02d}}.csv\n")
    f.write(f"- **Raw latencies**: raw_latencies/{{model}}_{{runtime}}.csv\n\n")

    f.write("## Model Info\n\n")
    f.write("| Model | Runtime | Input shape | Precision | Model size |\n")
    f.write("|-------|---------|-------------|-----------|------------|\n")
    for name, cfg in MODELS.items():
        dpu_sz = f"{os.path.getsize(cfg['dpu_xmodel'])//1024} KB" if os.path.exists(cfg['dpu_xmodel']) else "?"
        cpu_sz = f"{os.path.getsize(cfg['cpu_onnx'])//1024} KB"   if os.path.exists(cfg['cpu_onnx'])   else "?"
        f.write(f"| {name} | DPU | {cfg['dpu_input']} NHWC | INT8 | {dpu_sz} |\n")
        f.write(f"| {name} | CPU | {list(cfg['cpu_inputs'].values())[0]} NCHW | FP32 | {cpu_sz} |\n")
    f.write("\n")

    if model_meta:
        f.write("## Model Graph Metadata (XIR)\n\n")
        f.write("> Extracted from compiled xmodel via XIR graph API. "
                "Quantization uses DPU fixed-point (INT8, DPU_ROUND mode).\n\n")
        for model_name in ["resnet50", "inceptionv1", "yolov3"]:
            m = model_meta.get(model_name, {})
            f.write(f"### {model_name}\n\n")
            if "error" in m:
                f.write(f"Error: {m['error']}\n\n")
                continue
            f.write(f"- **Total XIR ops**: {m['total_ops']}\n")
            f.write(f"- **Op breakdown**:\n")
            for op_type, count in sorted(m['op_counts'].items(), key=lambda x: -x[1]):
                f.write(f"  - `{op_type}`: {count}\n")
            f.write(f"- **Tensor quantization**:\n")
            for t in m['quant_info']:
                bits = t.get('bit_width', 'N/A')
                signed = t.get('if_signed', 'N/A')
                fp = t.get('fix_point', 'N/A')
                rmode = t.get('round_mode', 'N/A')
                dtype = t.get('dtype', 'N/A')
                f.write(f"  - `{t['tensor']}` ({t['role']}) dims={t['dims']} "
                        f"dtype={dtype} bit_width={bits} signed={signed} "
                        f"fix_point={fp} round_mode={rmode}\n")
            f.write("\n")

    f.write("## Performance Results\n\n")
    f.write("> FPS/W_total uses total active power. FPS/W_delta uses (active − idle) power — "
            "the power attributable to inference only.\n")
    f.write("> DPU_CU_delta: DPU compute unit invocation count during benchmark frames "
            "(from xbutil; N/A for CPU runs).\n\n")
    for name in ["resnet50", "inceptionv1", "yolov3"]:
        f.write(f"### {name} — performance\n\n")
        f.write(PERF_HEADER + "\n")

    f.write("\n## System State Results\n\n")
    f.write("> Temperature, CMA free memory, and CPU frequency sampled per run.\n\n")
    for name in ["resnet50", "inceptionv1", "yolov3"]:
        f.write(f"### {name} — system\n\n")
        f.write(SYS_HEADER + "\n")

def append_result(model_name, round_num, runtime, r):
    with open(RESULTS_FILE, "r") as f:
        content = f.read()

    def insert_row(content, section_marker, row):
        idx = content.find(section_marker)
        if idx == -1:
            return content
        markers = [content.find(f"\n### ", idx+1),
                   content.find(f"\n## ", idx+1)]
        insert_at = min(x for x in markers if x > idx) if any(x > idx for x in markers) else len(content)
        before = content[:insert_at].rstrip("\n")
        return before + "\n" + row + "\n" + content[insert_at:]

    content = insert_row(content, f"### {model_name} — performance",
                         perf_row(round_num, runtime, r))
    content = insert_row(content, f"### {model_name} — system",
                         sys_row(round_num, runtime, r))

    with open(RESULTS_FILE, "w") as f:
        f.write(content)

def write_summary(all_results):
    with open(RESULTS_FILE, "a") as f:
        f.write("\n## Summary — Mean ± Std Dev\n\n")
        f.write("| Model | Runtime | FPS | Lat_mean_ms | Lat_std_ms | "
                "Power_avg_W | Delta_W | FPS/W_total | FPS/W_delta | "
                "mJ/frame | mJ/frame_delta |\n")
        f.write("|-------|---------|-----|-------------|------------|"
                "------------|---------|------------|------------|"
                "---------|---------------|\n")
        for model_name in ["resnet50", "inceptionv1", "yolov3"]:
            for runtime in ["dpu", "cpu"]:
                runs = all_results.get((model_name, runtime), [])
                if not runs: continue
                def m(k): return float(np.mean([r[k] for r in runs]))
                def s(k): return float(np.std([r[k]  for r in runs]))
                f.write(f"| {model_name} | {runtime.upper()} | "
                        f"{m('fps'):.2f}±{s('fps'):.2f} | "
                        f"{m('mean_lat'):.2f}±{s('mean_lat'):.2f} | "
                        f"{m('std_lat'):.2f}±{s('std_lat'):.2f} | "
                        f"{m('power_avg'):.3f}±{s('power_avg'):.3f} | "
                        f"{m('delta_power'):.3f}±{s('delta_power'):.3f} | "
                        f"{m('fps_per_w_total'):.3f}±{s('fps_per_w_total'):.3f} | "
                        f"{m('fps_per_w_delta'):.3f}±{s('fps_per_w_delta'):.3f} | "
                        f"{m('mj_per_frame'):.3f}±{s('mj_per_frame'):.3f} | "
                        f"{m('mj_per_frame_delta'):.3f}±{s('mj_per_frame_delta'):.3f} |\n")
        n = len(list(all_results.values())[0]) if all_results else 0
        f.write(f"\n_Summary from {n} rounds. Raw per-frame latencies in `raw_latencies/`. "
                f"Power waveforms in `raw_power/`._\n")

# ── Pause with countdown ──────────────────────────────────────────────────────
def pause(seconds, reason):
    print(f"\n  [{reason}] cooling down {seconds}s...", flush=True)
    for remaining in range(seconds, 0, -30):
        print(f"    {remaining}s remaining...", flush=True)
        time.sleep(min(30, remaining))
    print(f"  Done cooling.", flush=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    from pynq_dpu import DpuOverlay

    end_round = START_ROUND + N_ROUNDS - 1
    print(f"\nKV260 Benchmark — rounds {START_ROUND}–{end_round}", flush=True)
    print(f"Frames: {N_FRAMES} | Run pause: {PAUSE_BETWEEN_RUNS}s | Round pause: {PAUSE_BETWEEN_ROUNDS}s", flush=True)
    print(f"ORT threads: intra={N_ORT_THREADS} inter=1", flush=True)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", flush=True)

    if START_ROUND == 1:
        print("Collecting board info...", flush=True)
        info = get_board_info()
        print("Board info collected.\n", flush=True)
    else:
        info = {}
        print(f"Appending to existing {RESULTS_FILE}\n", flush=True)

    print("Loading DPU overlay...", flush=True)
    ol = DpuOverlay("dpu.bit")
    print("DPU overlay loaded.\n", flush=True)

    if START_ROUND == 1:
        print("Collecting model graph metadata...", flush=True)
        model_meta = collect_model_metadata(ol)
        # Write full header including model metadata
        with open(RESULTS_FILE, "w") as f:
            write_header(f, info, START_ROUND, end_round, model_meta=model_meta)
        print("Model metadata written.\n", flush=True)
    else:
        model_meta = None

    all_results = {(m, r): [] for m, r in RUN_ORDER}

    for round_num in range(START_ROUND, START_ROUND + N_ROUNDS):
        print(f"\n{'='*60}", flush=True)
        print(f"ROUND {round_num}/{end_round}  [{datetime.now().strftime('%H:%M:%S')}]", flush=True)
        print(f"{'='*60}", flush=True)

        cma = read_cma_free_kb()
        temp = read_temp_c()
        print(f"CMA free: {cma} kB {'✓' if cma and cma > 500000 else '⚠ LOW'}  |  "
              f"Temp: {fmt(temp,1)}°C", flush=True)

        for i, (model_name, runtime) in enumerate(RUN_ORDER):
            print(f"\n── {model_name.upper()} {runtime.upper()}  round {round_num} "
                  f"[{datetime.now().strftime('%H:%M:%S')}]", flush=True)
            try:
                if runtime == "dpu":
                    r = run_dpu(model_name, round_num, ol)
                else:
                    r = run_cpu(model_name, round_num)

                all_results[(model_name, runtime)].append(r)
                append_result(model_name, round_num, runtime, r)

                cu_str = f"  CU_delta:{r['cu_usage_delta']}" if r['cu_usage_delta'] is not None else ""
                print(f"  ✓ FPS:{r['fps']:.2f}  Lat:{r['mean_lat']:.1f}±{r['std_lat']:.1f}ms  "
                      f"p99:{r['p99_lat']:.1f}ms  "
                      f"Power:{r['power_avg']:.2f}W(idle:{r['idle_power']:.2f}W "
                      f"Δ:{r['delta_power']:.2f}W)  "
                      f"FPS/W:{r['fps_per_w_total']:.3f}(Δ:{r['fps_per_w_delta']:.3f})  "
                      f"Temp:{fmt(r['temp_before'],1)}→{fmt(r['temp_after'],1)}°C"
                      f"{cu_str}", flush=True)

                # Pause between runs (skip after last run in round)
                is_last_run = (i == len(RUN_ORDER) - 1)
                if not is_last_run:
                    pause(PAUSE_BETWEEN_RUNS, f"after {model_name} {runtime}")

            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                import traceback; traceback.print_exc()

        print(f"\nRound {round_num} complete. [{datetime.now().strftime('%H:%M:%S')}]", flush=True)

        # Pause between rounds (skip after last round)
        is_last_round = (round_num == START_ROUND + N_ROUNDS - 1)
        if not is_last_round:
            pause(PAUSE_BETWEEN_ROUNDS, f"end of round {round_num}")

    write_summary(all_results)
    print(f"\n{'='*60}", flush=True)
    print(f"ALL DONE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Results: {RESULTS_FILE}", flush=True)
    print(f"Raw latencies: {RAW_DIR}/", flush=True)
    print(f"Power waveforms: {RAW_POWER_DIR}/", flush=True)

if __name__ == "__main__":
    main()
