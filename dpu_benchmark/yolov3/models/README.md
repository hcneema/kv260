# YOLOv3 Models

## CPU Model
- **File**: `yolov3-10.onnx` (237MB) ✅ included
- **MD5**: `ab2add3cf1200ffb912e5d25c5bbdd29` (verify after download)
- **Source**: ONNX Model Zoo
- **Download** (if missing): https://github.com/onnx/models/blob/main/validated/vision/object_detection_segmentation/yolov3/model/yolov3-10.onnx
  (click "Download raw file" button in browser — wget fails due to GitHub LFS)

## DPU Model
- **File**: `tf_yolov3_voc.xmodel` (61MB) ✅ included
- **Source**: Kria-PYNQ package (pynq-dpu 2.5.1), originally at:
  `/root/jupyter_notebooks/pynq-dpu/tf_yolov3_voc.xmodel`
- **Architecture**: DPUCZDX8G B512, trained on VOC dataset
