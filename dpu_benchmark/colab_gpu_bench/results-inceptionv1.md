# InceptionV3 GPU Benchmark Results — Google Colab T4

> Model: InceptionV3 (Keras, 299x299, ~24M params)
> KV260 used InceptionV1 (224x224, ~6M params) — FPS not directly comparable; FPS/W_delta efficiency ratio is informative.
> Script: inceptionv1_gpu_bench.py

---

TensorFlow version: 2.20.0
GPU available: 1 physical, 1 logical

Loading InceptionV3 (ImageNet weights, 1000 classes)...
Downloading data from https://storage.googleapis.com/tensorflow/keras-applications/inception_v3/inception_v3_weights_tf_dim_ordering_tf_kernels.h5
96112376/96112376 ━━━━━━━━━━━━━━━━━━━━ 1s 0us/step
Model loaded. Parameters: 23,851,784

Measuring idle GPU power (10s)...
  Idle power: 29.14 W

Warmup (10 frames)...
Warmup done.

 Rnd      FPS   Lat_mean   Lat_p95   ActiveW   DeltaW   FPS/W_d
--------------------------------------------------------------------
   1     86.2      11.59     16.10     63.53    34.39      2.51
   2     85.1      11.75     16.22     64.27    35.13      2.42
   3     62.7      15.95     26.19     60.11    30.98      2.02
   4     82.7      12.08     16.86     65.14    36.00      2.30
   5     88.1      11.34     15.75     62.42    33.29      2.65
   6     82.6      12.10     17.34     67.58    38.44      2.15
   7     73.2      13.66     20.39     59.58    30.45      2.40
   8     54.1      18.47     27.02     57.80    28.66      1.89
   9     83.9      11.91     17.16     64.58    35.45      2.37
  10     85.3      11.71     16.90     61.32    32.19      2.65

============================================================
INCEPTIONV3 GPU BENCHMARK RESULTS (10 rounds × 100 frames)
============================================================
Platform:       Google Colab — Tesla T4
GPU memory:     15360 MB
Driver:         580.82.07
TensorFlow:     2.20.0
Model:          InceptionV3 (Keras, ImageNet weights, 299x299, 1000 classes)
NOTE:           KV260 used InceptionV1 (6M params, 224x224) — not directly
                comparable in FPS; FPS/W_delta efficiency ratio is informative.
------------------------------------------------------------
FPS:            78.40 ± 10.86
Latency mean:   13.06 ms
Latency p95:    18.99 ms
Latency p99:    22.19 ms
------------------------------------------------------------
Idle power:     29.14 W
Active power:   62.63 ± 2.81 W
Delta power:    33.50 W  (active − idle)
FPS/W (delta):  2.34 ± 0.24   ← primary efficiency metric
mJ/frame:       798.94
mJ/frame delta: 427.27
------------------------------------------------------------
KV260 DPU ref (InceptionV1): 165.75 ± 0.33 FPS | 64.73 ± 3.84 FPS/W_delta
KV260 CPU ref (InceptionV1):   3.86 ± 0.01 FPS |  3.35 ± 0.04 FPS/W_delta
============================================================

