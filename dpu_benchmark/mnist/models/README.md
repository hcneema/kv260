# MNIST Models

## CPU Model
- **File**: `mnist-12.onnx` (26KB) ✅ included
- **Source**: ONNX Model Zoo
- **Input**: `(1, 1, 28, 28)` float32 — channel first
- **Output**: `(1, 10)` — logits for digits 0-9

## DPU Model
- **File**: `dpu_mnist_classifier.xmodel` (759KB) ✅ included
- **Source**: Kria-PYNQ package (pynq-dpu 2.5.1)
- **Input**: `(1, 28, 28, 1)` float32 — channel last
- **Output**: `(1, 10)` — scores for digits 0-9
- **Architecture**: DPUCZDX8G B512

## MNIST Dataset
Not included (too large for git). Downloaded automatically by `setup.sh`.
- Source: Google storage mirror (official Yann LeCun URL is dead — 404)
- Location on board: `/home/ubuntu/mnist_data/`
- Files: t10k-images + t10k-labels (test set, 10,000 images)
