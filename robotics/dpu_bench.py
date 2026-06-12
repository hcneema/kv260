import os, time, numpy as np

os.chdir('/home/ubuntu/kv260-ubuntu-test/yolox-test')

from pynq_dpu import DpuOverlay

print("Loading overlay (download=False - xmutil already loaded DPU)...", flush=True)
overlay = DpuOverlay("dpu.xclbin", download=False)
print("Overlay loaded!", flush=True)

overlay.load_model("b512_2_5_yolox_nano_pt.xmodel")
print("Model loaded!", flush=True)

dpu = overlay.runner
in_t  = dpu.get_input_tensors()
out_t = dpu.get_output_tensors()
print(f"Input shape: {in_t[0].dims}", flush=True)

in_d  = [np.zeros(t.dims, dtype=np.float32) for t in in_t]
out_d = [np.zeros(t.dims, dtype=np.float32) for t in out_t]

# Warmup
job = dpu.execute_async(in_d, out_d)
dpu.wait(job)
print("Warmup done!", flush=True)

N = 50
start = time.time()
for i in range(N):
    job = dpu.execute_async(in_d, out_d)
    dpu.wait(job)
elapsed = time.time() - start

print()
print("=== DPU BENCHMARK RESULT ===")
print(f"Model:   YOLOX-nano B512")
print(f"Frames:  {N}")
print(f"Total:   {elapsed:.2f}s")
print(f"FPS:     {N/elapsed:.1f}")
print(f"Latency: {elapsed/N*1000:.1f} ms/frame")
print("============================")

del overlay
