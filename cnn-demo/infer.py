import onnxruntime as ort
import numpy as np
from PIL import Image
import json
import time
import urllib.request

# Download ImageNet labels
labels_url = "https://raw.githubusercontent.com/anishathalye/imagenet-simple-labels/master/imagenet-simple-labels.json"
try:
    urllib.request.urlretrieve(labels_url, "labels.json")
    with open("labels.json") as f:
        labels = json.load(f)
except:
    labels = [f"class_{i}" for i in range(1000)]

# Load real test image (fish - ImageNet tench class)
print("Loading fish.jpg (real ImageNet sample)...")
img = Image.open("fish.jpg").convert("RGB")

# Preprocess
img = img.resize((224, 224))
img_array = np.array(img).astype(np.float32)
mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
img_array = (img_array / 255.0 - mean) / std
img_array = img_array.transpose(2, 0, 1)   # HWC -> CHW
img_array = np.expand_dims(img_array, 0)   # add batch dim

# Load model and run
print("Loading MobileNetV2 model...")
session = ort.InferenceSession("mobilenet.onnx", providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name

print("Running inference on Kria KV260 (CPU/ARM)...")
start = time.time()
outputs = session.run(None, {input_name: img_array})
elapsed = time.time() - start

scores = outputs[0][0]
top5 = np.argsort(scores)[::-1][:5]

print(f"\n=== Results ===")
print(f"Inference time : {elapsed*1000:.1f} ms")
print(f"Device         : Kria KV260 ARM Cortex-A53")
print(f"\nTop-5 predictions (random image, labels won't be meaningful):")
for i, idx in enumerate(top5):
    print(f"  {i+1}. {labels[idx]:30s}  score: {scores[idx]:.4f}")
print("\nPipeline working! Ready for real images and DPU acceleration.")
