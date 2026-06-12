# InceptionV1 Models

## CPU Model
- **File**: `inception-v1-9.onnx` (27MB) ✅ included
- **Source**: Downloaded from GitHub ONNX model zoo via browser (click "Download raw file")
  https://github.com/onnx/models/blob/main/validated/vision/classification/inception_and_googlenet/inception_v1/model/inception-v1-9.onnx
- **Note**: wget fails on this file (GitHub LFS) — must use browser download

## DPU Model
- **File**: `dpu_tf_inceptionv1.xmodel` (6MB) ✅ included
- **Source**: Kria-PYNQ package (pynq-dpu 2.5.1), originally at:
  `/root/jupyter_notebooks/pynq-dpu/dpu_tf_inceptionv1.xmodel`
- **Architecture**: DPUCZDX8G B512, TensorFlow InceptionV1
