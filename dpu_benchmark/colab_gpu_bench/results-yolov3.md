# YOLOv3 GPU Benchmark Results — Google Colab T4

> Model: YOLOv3u (Ultralytics auto-upgraded from yolov3.pt → yolov3u.pt, 103M params, PyTorch, COCO, 640×640)
> KV260 DPU used tf_yolov3_voc.xmodel (standard YOLOv3, ~62M params, VOC, INT8, 416×416)
> KV260 CPU used yolov3-10.onnx (standard YOLOv3, ~62M params, COCO, FP32, 416×416)
>
> Caveats: model variant (YOLOv3u vs YOLOv3), framework (PyTorch vs ONNX RT), input size (640 vs 416), training data (COCO vs VOC on DPU).
> YOLOv3u is heavier than standard YOLOv3 — T4 FPS/W_delta is a conservative (lower-bound) GPU estimate.
> Script: yolov3_gpu_bench.py

---
Creating new Ultralytics Settings v0.0.7 file ✅ 
View Ultralytics Settings with 'yolo settings' or at '/root/.config/Ultralytics/settings.json'
Update Settings with 'yolo settings key=value', i.e. 'yolo settings runs_dir=path/to/dir'. For help see https://docs.ultralytics.com/quickstart/#ultralytics-settings.
PyTorch version: 2.11.0+cu128
GPU: Tesla T4

Loading YOLOv3 (Ultralytics, COCO weights)...
PRO TIP 💡 Replace 'model=yolov3.pt' with new 'model=yolov3u.pt'.
YOLOv5 'u' models are trained with https://github.com/ultralytics/ultralytics and feature improved performance vs standard YOLOv5 models trained with https://github.com/ultralytics/yolov5.
Downloading https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov3u.pt to 'yolov3u.pt': 100% ━━━━━━━━━━━━ 198.3MB 87.1MB/s 2.3s
Model loaded. Parameters: 103,754,144

Measuring idle GPU power (10s)...
  Idle power: 25.97 W

Warmup (10 frames)...
Warmup done.

 Rnd      FPS   Lat_mean   Lat_p95   ActiveW   DeltaW   FPS/W_d
--------------------------------------------------------------------
   1     16.0      62.51     63.66     69.37    43.39      0.37
   2     15.8      63.08     64.01     67.64    41.67      0.38
   3     15.7      63.63     64.48     67.15    41.18      0.38
   4     15.6      64.09     65.04     67.56    41.58      0.37
   5     15.5      64.51     65.58     68.80    42.82      0.36
   6     15.4      65.04     65.84     67.13    41.16      0.37
   7     15.2      65.68     66.77     66.98    41.00      0.37
   8     15.1      66.13     66.99     66.90    40.93      0.37
   9     14.9      66.93     68.00     67.36    41.39      0.36
  10     14.8      67.43     68.44     66.52    40.54      0.37

============================================================
YOLOV3 GPU BENCHMARK RESULTS (10 rounds × 100 frames)
============================================================
Platform:       Google Colab — Tesla T4
GPU memory:     15360 MB
Driver:         580.82.07
PyTorch:        2.11.0+cu128
Model:          YOLOv3 (Ultralytics, COCO weights, 640×640)
Caveats:        PyTorch/FP32 vs ONNX RT (CPU) / pynq-dpu INT8 (DPU)
                640×640 input (T4) vs 416×416 (KV260)
                COCO training (T4) vs VOC training (KV260 DPU)
------------------------------------------------------------
FPS:            15.40 ± 0.37
Latency mean:   64.90 ms
Latency p95:    65.88 ms
Latency p99:    66.60 ms
------------------------------------------------------------
Idle power:     25.97 W
Active power:   67.54 ± 0.84 W
Delta power:    41.57 W  (active − idle)
FPS/W (delta):  0.37 ± 0.01   ← primary efficiency metric
mJ/frame:       4385.81
mJ/frame delta: 2699.15
------------------------------------------------------------
KV260 DPU ref (YOLOv3, 416×416, VOC): 13.23 ± 0.02 FPS | 3.09 ± 0.10 FPS/W_delta
KV260 CPU ref (YOLOv3, 416×416, COCO): 0.22 ± 0.00 FPS | 0.17 ± 0.01 FPS/W_delta
============================================================


