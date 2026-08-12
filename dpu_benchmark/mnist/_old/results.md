# MNIST Benchmark Results

## Platform: KV260 (Ubuntu 22.04, kernel 5.15.0-1027)
## Model: MNIST Digit Classifier (input 28x28 grayscale, output 10 digit classes)

| Metric | CPU (ARM Cortex-A53) | DPU (B512) | Speedup |
|---|---|---|---|
| FPS | 2060.0 | 2863.8 | **1.4x faster** |
| Latency (ms/frame) | 0.49 | 0.35 | 1.4x lower |
| Accuracy | 98.0% | 99.0% | DPU slightly better |
| Power (Watts) | 5.57 | 5.61 | ~same |
| **FPS/Watt** | **370.10** | **510.48** | **1.4x more efficient** |

## Key insight
MNIST is a tiny model (28x28 input, simple CNN). Both CPU and DPU are fast enough
that the difference is small (~1.4x). For tiny models like this, the DPU overhead
(loading, DMA) reduces the relative advantage. The DPU shines on larger models
(ResNet50: 29x, YOLOv3: 50x).

**MNIST is interesting because it shows DPU accuracy (99%) ≥ CPU (98%)** — the
INT8 quantization used by the DPU xmodel doesn't hurt accuracy on this task.

## Notes
- CPU uses ONNX Runtime 1.23.2 with CPUExecutionProvider
- DPU uses pynq-dpu with B512 bitstream (dpu.bit from Kria-PYNQ)
- MNIST test set: 10,000 images — benchmarked on first 100
- MNIST data downloaded from Google storage mirror (official source dead)

## How to Reproduce
```bash
# 1. Run setup to download MNIST data and copy models
bash setup.sh

# 2. DPU benchmark (from Jupyter terminal)
source /etc/profile.d/pynq_venv.sh
cd /root/jupyter_notebooks/pynq-dpu
python3 /path/to/mnist/dpu_bench.py

# 3. CPU benchmark
python3 /path/to/mnist/cpu_bench.py
```

## Gotchas

### 1. Official MNIST download URL is dead
The `mnist` Python package tries to download from Yann LeCun's website — gets 404.
**Fix**: Download from Google's mirror instead:
```python
base = "https://storage.googleapis.com/cvdf-datasets/mnist/"
```
Our `setup.sh` handles this automatically.

### 2. mnist package requires write access to its install directory
The `mnist` package tries to cache data next to its `.py` file in the pynq venv
(`/usr/local/share/pynq-venv/...`) — permission denied.
**Fix**: Download to `/home/ubuntu/mnist_data/` and load manually with gzip+numpy.

### 3. DPU input needs channel dimension
MNIST images are 28x28. The DPU xmodel expects `(1, 28, 28, 1)` — need to add
the channel dimension: `data = images[:, :, :, np.newaxis]`

### 4. CPU ONNX model expects different shape
The MNIST ONNX model expects `(1, 1, 28, 28)` — channel first:
`data = images[:, np.newaxis, :, :]`

### Files needed
- `models/mnist-12.onnx` (26KB) ✅ included
- `models/dpu_mnist_classifier.xmodel` (759KB) ✅ included
- `../shared/dpu.bit` (7MB) ✅ in shared/
- MNIST data — downloaded by `setup.sh` to `/home/ubuntu/mnist_data/`
