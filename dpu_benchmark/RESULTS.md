# KV260 CPU vs DPU Benchmark — Raw Results

Generated: 2026-08-12 06:13:19  
Frames per run: 100  

## Platform

- **Board**: AMD Kria KV260 revB
- **OS**: Ubuntu 22.04.4 LTS
- **Kernel**: 5.15.0-1027-xilinx-zynqmp
- **CPU**: ARM Cortex-A53 quad-core @ 1.3 GHz
- **DPU**: DPUCZDX8G B512
- **XRT**: 2.13.479-0ubuntu2
- **PYNQ**: 3.0.1
- **pynq-dpu**: 2.5.0
- **ONNX Runtime**: 1.23.2
- **Power sensor**: INA260 @ /sys/class/hwmon/hwmon2/power1_input
- **Power sampling**: ~200 ms interval, averaged over run
- **Frames per run**: 100
- **DPU warmup frames**: 10
- **CPU warmup frames**: 3

## Model Info

| Model | Runtime | Input shape | Precision | Model size |
|-------|---------|-------------|-----------|------------|
| resnet50 | DPU | (1, 224, 224, 3) (NHWC) | INT8 | 26597 KB |
| resnet50 | CPU | (1, 3, 224, 224) (NCHW) | FP32 | 100179 KB |
| inceptionv1 | DPU | (1, 224, 224, 3) (NHWC) | INT8 | 7162 KB |
| inceptionv1 | CPU | (1, 3, 224, 224) (NCHW) | FP32 | 27363 KB |
| yolov3 | DPU | (1, 416, 416, 3) (NHWC) | INT8 | 62531 KB |
| yolov3 | CPU | (1, 3, 416, 416) (NCHW) | FP32 | 242098 KB |

## Raw Results

### resnet50

| Round | Runtime | FPS | Lat_mean_ms | Lat_std_ms | Lat_min_ms | Lat_max_ms | Power_W | FPS_per_W | mJ_per_frame |
|-------|---------|-----|-------------|------------|------------|------------|---------|-----------|-------------|
| 1 | DPU | 84.35 | 11.86 | 0.25 | 11.74 | 14.27 | 7.817 | 10.791 | 92.671 |
| 1 | CPU | 1.59 | 630.89 | 5.32 | 624.24 | 664.76 | 5.988 | 0.265 | 3777.540 |
| 2 | DPU | 84.37 | 11.85 | 0.05 | 11.77 | 12.12 | 7.775 | 10.851 | 92.157 |
| 2 | CPU | 1.59 | 627.68 | 5.32 | 621.80 | 659.63 | 5.988 | 0.266 | 3758.775 |

### inceptionv1

| Round | Runtime | FPS | Lat_mean_ms | Lat_std_ms | Lat_min_ms | Lat_max_ms | Power_W | FPS_per_W | mJ_per_frame |
|-------|---------|-----|-------------|------------|------------|------------|---------|-----------|-------------|
| 1 | DPU | 165.77 | 6.03 | 0.06 | 5.96 | 6.25 | 7.450 | 22.251 | 44.942 |
| 1 | CPU | 3.53 | 283.13 | 91.37 | 256.85 | 848.20 | 5.948 | 0.594 | 1684.087 |
| 2 | DPU | 165.33 | 6.05 | 0.05 | 5.96 | 6.22 | 7.442 | 22.215 | 45.016 |
| 2 | CPU | 3.84 | 260.09 | 4.92 | 256.10 | 294.34 | 5.975 | 0.643 | 1554.070 |

### yolov3

| Round | Runtime | FPS | Lat_mean_ms | Lat_std_ms | Lat_min_ms | Lat_max_ms | Power_W | FPS_per_W | mJ_per_frame |
|-------|---------|-----|-------------|------------|------------|------------|---------|-----------|-------------|
| 1 | DPU | 13.23 | 75.56 | 0.13 | 75.40 | 76.55 | 8.962 | 1.477 | 677.133 |
| 1 | CPU | 0.21 | 4652.66 | 12.53 | 4634.61 | 4694.48 | 6.094 | 0.035 | 28353.318 |
| 2 | DPU | 13.23 | 75.59 | 0.05 | 75.48 | 75.82 | 9.043 | 1.463 | 683.494 |
| 2 | CPU | 0.22 | 4644.10 | 13.48 | 4617.39 | 4685.65 | 6.096 | 0.035 | 28308.754 |
