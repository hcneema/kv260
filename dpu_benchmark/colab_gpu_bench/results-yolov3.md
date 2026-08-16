# YOLOv3 GPU Benchmark Results — Google Colab T4

> Model: YOLOv3 (Ultralytics, PyTorch, COCO weights, 640×640)
> KV260 DPU used tf_yolov3_voc.xmodel (VOC, INT8, 416×416)
> KV260 CPU used yolov3-10.onnx (COCO, FP32, 416×416)
>
> Caveats: framework (PyTorch vs ONNX RT), input size (640 vs 416), training data (COCO vs VOC on DPU).
> FPS/W_delta efficiency ratio is indicative.
> Script: yolov3_gpu_bench.py

---

<!-- Paste 10-round results here -->
