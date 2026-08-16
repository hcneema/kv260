*********** 1 run result *************

TensorFlow version: 2.20.0
GPU available: 1 physical, 1 logical

Loading ResNet50 (ImageNet weights, 1000 classes)...
Downloading data from https://storage.googleapis.com/tensorflow/keras-applications/resnet/resnet50_weights_tf_dim_ordering_tf_kernels.h5
102967424/102967424 ━━━━━━━━━━━━━━━━━━━━ 6s 0us/step
Model loaded. Parameters: 25,636,712

Measuring idle GPU power (10s)...
  Idle power: 27.33 W

Warmup (10 frames)...
Warmup done.

Benchmarking (100 frames)...

============================================================
RESNET50 GPU BENCHMARK RESULTS
============================================================
Platform:       Google Colab — Tesla T4
GPU memory:     15360 MB
Driver:         580.82.07
TensorFlow:     2.20.0
Model:          ResNet50 (Keras, ImageNet weights, 1000 classes)
Frames:         100
------------------------------------------------------------
FPS:            4.0
Latency mean:   252.14 ms
Latency std:    54.86 ms
Latency min:    215.17 ms
Latency max:    476.69 ms
Latency p95:    371.41 ms
Latency p99:    428.03 ms
------------------------------------------------------------
Idle power:     27.33 W
Active power:   28.31 ± 0.46 W
Delta power:    0.98 W  (active − idle)
FPS/W (total):  0.14
FPS/W (delta):  4.04   ← primary efficiency metric
mJ/frame:       7138.42
mJ/frame delta: 247.68
------------------------------------------------------------
KV260 DPU ref:  84.4 FPS | 8.16W active | 28.65 FPS/W_delta
KV260 CPU ref:   1.6 FPS | 6.01W active |  1.33 FPS/W_delta
============================================================

******** 10 run result (CPU fallback — invalid, script bug) ********
NOTE: FPS=4.0 run above was CPU fallback (TF2 eager mode + numpy input).
Discarded. Fixed with @tf.function + tf.constant + tf.device('/GPU:0').

======== 10 run result (GPU confirmed — VALID) ========
TensorFlow version: 2.20.0
GPU available: 1 physical, 1 logical

Loading ResNet50 (ImageNet weights, 1000 classes)...
Downloading data from https://storage.googleapis.com/tensorflow/keras-applications/resnet/resnet50_weights_tf_dim_ordering_tf_kernels.h5
102967424/102967424 ━━━━━━━━━━━━━━━━━━━━ 6s 0us/step
Model loaded. Parameters: 25,636,712

Measuring idle GPU power (10s)...
  Idle power: 26.68 W

Warmup (10 frames)...
Warmup done.

 Rnd      FPS   Lat_mean   Lat_p95   ActiveW   DeltaW   FPS/W_d
--------------------------------------------------------------------
   1    135.0       7.40     10.25     68.66    41.98      3.22
   2     90.3      11.06     17.05     56.35    29.66      3.05
   3     80.0      12.49     18.87     56.63    29.95      2.67
   4    129.5       7.72     11.16     64.69    38.01      3.41
   5    122.8       8.13     11.71     60.55    33.87      3.63
   6    123.0       8.13     11.48     58.59    31.90      3.85
   7    134.8       7.41     10.33     61.23    34.54      3.90
   8    130.4       7.66     11.29     58.77    32.09      4.06
   9    122.2       8.17     11.72     62.58    35.90      3.41
  10    128.6       7.77     11.01     59.51    32.83      3.92

NOTE: Rounds 2-3 dip (80-90 FPS) — Colab shared GPU scheduler preemption.
KV260 DPU shows ±0.05 FPS across 10 rounds vs T4 ±17.94 FPS (360x more stable).

============================================================
RESNET50 GPU BENCHMARK RESULTS (10 rounds × 100 frames) — FINAL
============================================================
Platform:       Google Colab — Tesla T4
GPU memory:     15360 MB
Driver:         580.82.07
TensorFlow:     2.20.0
Model:          ResNet50 (Keras, ImageNet weights, 1000 classes)
Script:         resnet50_gpu_bench.py (@tf.function + /GPU:0)
------------------------------------------------------------
FPS:            119.67 ± 17.94
Latency mean:   8.59 ms
Latency p95:    12.49 ms
Latency p99:    14.66 ms
------------------------------------------------------------
Idle power:     26.68 W
Active power:   60.76 ± 3.58 W
Delta power:    34.07 W  (active − idle)
FPS/W (delta):  3.51 ± 0.42   ← primary efficiency metric
mJ/frame:       507.71
mJ/frame delta: 284.72
------------------------------------------------------------
KV260 DPU ref:  84.38 ± 0.05 FPS | 8.16W active | 28.65 ± 0.79 FPS/W_delta
KV260 CPU ref:   1.58 ± 0.04 FPS | 6.01W active |  1.33 ± 0.03 FPS/W_delta
============================================================

