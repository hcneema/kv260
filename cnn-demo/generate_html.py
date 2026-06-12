"""
Generate HTML slides with embedded fish image.
Run on Kria: ~/vitis-env/bin/python3 generate_html.py
"""
import base64, os

with open("fish.jpg", "rb") as f:
    fish_b64 = base64.b64encode(f.read()).decode()

fish_img = f'data:image/jpeg;base64,{fish_b64}'

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Kria KV260 — Bring-up & CNN Inference</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f0f1a;color:#fff;overflow:hidden}}
.slide{{display:none;position:absolute;inset:0;padding:55px 75px;animation:fadeIn 0.35s ease;flex-direction:column;justify-content:center}}
.slide.active{{display:flex}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
h1{{font-size:2.8em;font-weight:700;margin-bottom:10px}}
h2{{font-size:1.9em;font-weight:600;margin-bottom:20px;border-left:5px solid #e8391d;padding-left:14px}}
h3{{font-size:1.05em;color:#e8391d;margin-bottom:6px;margin-top:18px;text-transform:uppercase;letter-spacing:1px}}
p{{font-size:1.05em;line-height:1.7;color:#ccc}}
ul{{list-style:none;margin-top:6px}}
ul li{{font-size:1em;color:#ccc;padding:5px 0 5px 22px;position:relative;line-height:1.5}}
ul li::before{{content:"▸";position:absolute;left:0;color:#e8391d}}
.subtitle{{font-size:1.2em;color:#aaa;margin-bottom:6px}}
.date{{font-size:.9em;color:#555;margin-top:18px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:14px}}
.grid-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-top:14px}}
.card{{background:#1a1a2e;border:1px solid #333;border-radius:10px;padding:20px}}
.card.good{{border-color:#4caf5044}}
.stat-box{{background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid #e8391d44;border-radius:10px;padding:22px;text-align:center}}
.stat-box .number{{font-size:2.5em;font-weight:700;color:#e8391d}}
.stat-box .label{{font-size:.8em;color:#888;margin-top:3px;text-transform:uppercase;letter-spacing:1px}}
code{{background:#1e1e2e;border:1px solid #333;border-radius:5px;padding:1px 7px;font-family:'Cascadia Code','Courier New',monospace;font-size:.88em;color:#7ec8e3}}
pre{{background:#1e1e2e;border:1px solid #333;border-radius:9px;padding:18px;font-family:'Cascadia Code','Courier New',monospace;font-size:.82em;color:#7ec8e3;line-height:1.6;overflow:auto;margin-top:10px}}
pre .cmd{{color:#4caf50}}pre .cmt{{color:#555}}
.badge{{display:inline-block;background:#e8391d22;border:1px solid #e8391d88;color:#e8391d;border-radius:20px;padding:3px 13px;font-size:.82em;margin:3px 3px 3px 0}}
.badge.green{{background:#4caf5022;border-color:#4caf5088;color:#4caf50}}
.badge.yellow{{background:#ffc10722;border-color:#ffc10788;color:#ffc107}}
.badge.blue{{background:#2196f322;border-color:#2196f388;color:#2196f3}}
.result-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #222;font-size:.95em}}
.result-row:last-child{{border-bottom:none}}
.result-row .key{{color:#888}}.result-row .val{{color:#fff;font-weight:600}}.result-row .val.good{{color:#4caf50}}
.roadmap-phase{{background:#1a1a2e;border-left:4px solid #e8391d;border-radius:0 9px 9px 0;padding:14px 18px;margin-bottom:12px}}
.roadmap-phase.done{{border-color:#4caf50}}.roadmap-phase.next{{border-color:#ffc107}}.roadmap-phase.future{{border-color:#2196f3}}.roadmap-phase.hls{{border-color:#9c27b0}}
.roadmap-phase h4{{margin-bottom:3px;font-size:.95em}}.roadmap-phase p{{font-size:.84em;color:#888}}
.warning{{background:#ffc10711;border:1px solid #ffc10744;border-radius:7px;padding:10px 14px;margin-top:10px;font-size:.88em;color:#ffc107}}
#nav{{position:fixed;bottom:24px;right:36px;display:flex;align-items:center;gap:14px;z-index:100}}
#nav button{{background:#1a1a2e;border:1px solid #444;color:#fff;padding:8px 20px;border-radius:7px;cursor:pointer;font-size:.9em;transition:background .2s}}
#nav button:hover{{background:#e8391d;border-color:#e8391d}}
#counter{{color:#555;font-size:.85em}}
#logo{{position:fixed;top:20px;right:36px;font-size:.9em;color:#2a2a3a;font-weight:700;letter-spacing:2px}}
.title-slide{{background:radial-gradient(ellipse at 70% 50%,#1a0a0a 0%,#0f0f1a 60%)}}
</style>
</head>
<body>
<div id="logo">AMD · XILINX</div>

<!-- S1: Title -->
<div class="slide active title-slide">
  <p class="subtitle">Session Report · 2026-06-07</p>
  <h1>Kria <span style="color:#e8391d">KV260</span> Bring-up<br>&amp; CNN Inference</h1>
  <p style="margin-top:16px;max-width:620px;color:#aaa">End-to-end setup of the Xilinx AMD Kria KV260 Vision AI Starter Kit — from zero network access to running MobileNetV2 inference on-board.</p>
  <div style="margin-top:32px">
    <span class="badge green">SSH Connected</span>
    <span class="badge green">CNN Running</span>
    <span class="badge yellow">DPU — Next</span>
    <span class="badge blue">YOLO — Planned</span>
  </div>
  <p class="date">hemn · AMD Engineering</p>
</div>

<!-- S2: Board Overview -->
<div class="slide">
  <h2>Board Overview</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Hardware</h3>
      <ul>
        <li>Kria <strong>KV260</strong> Vision AI Starter Kit</li>
        <li>SoC: Zynq UltraScale+ MPSoC</li>
        <li>CPU: Quad-core ARM Cortex-A53 @ 1.3 GHz</li>
        <li>FPGA: PL fabric + AI Engine</li>
        <li>RAM: 4 GB LPDDR4 · Storage: 29 GB eMMC</li>
      </ul>
    </div>
    <div class="card">
      <h3>Software</h3>
      <ul>
        <li>Ubuntu <strong>24.04.4 LTS</strong> (Noble Numbat)</li>
        <li>Kernel: 6.8.0-1024-xilinx (aarch64)</li>
        <li>Python 3.12.3</li>
        <li>xmutil + dfx-mgr (overlay management)</li>
        <li>fpga-manager-xlnx · libxaiengine 2024.2</li>
      </ul>
    </div>
  </div>
  <div class="warning">⚠ Ubuntu 24.04 is cutting-edge for Kria — Vitis AI apt packages officially target Ubuntu 22.04 and below.</div>
</div>

<!-- S3: Network Discovery -->
<div class="slide">
  <h2>Challenge 1 — Network Discovery</h2>
  <div class="grid-2">
    <div>
      <h3>Problems</h3>
      <ul>
        <li>Host PC and Kria on <strong>different WiFi networks</strong></li>
        <li>SSH (port 22) disabled by default</li>
        <li>mDNS <code>kria.local</code> didn't resolve</li>
        <li>Hostname <code>xsjkria02x</code> not in DNS</li>
        <li>Port scan: no open TCP ports found</li>
      </ul>
      <h3 style="margin-top:20px">Resolution</h3>
      <ul>
        <li>Physical access: opened terminal on board</li>
        <li>Connected both to <strong>same WiFi network</strong></li>
        <li>Board IP confirmed: <code>192.168.68.60</code></li>
        <li>TTL=64 on ping → Linux confirmed</li>
      </ul>
    </div>
    <div class="card">
      <h3>ARP Discovery</h3>
      <pre><span class="cmd">arp -a</span>
<span class="cmt"># Wrong subnet initially:</span>
192.168.1.116  64-ff-0a-85-f8-d2

<span class="cmt"># After switching WiFi:</span>
<span class="cmd">ping 192.168.68.60</span>
Reply: time=4ms TTL=64
<span class="cmt"># TTL=64 means Linux device</span>

<span class="cmd">sudo systemctl enable --now ssh
ip addr show</span>  <span class="cmt"># 192.168.68.60</span></pre>
    </div>
  </div>
</div>

<!-- S4: SSH Setup -->
<div class="slide">
  <h2>SSH Key Authentication Setup</h2>
  <div class="grid-2">
    <div>
      <h3>Steps</h3>
      <ul>
        <li>Enabled SSH on board via physical terminal</li>
        <li>Generated ED25519 key pair on host PC</li>
        <li>Copied public key to board authorized_keys</li>
        <li>Verified passwordless login</li>
      </ul>
      <div style="margin-top:20px">
        <span class="badge green">No password needed</span><br><br>
        <span class="badge green">Automated remote iteration enabled</span>
      </div>
    </div>
    <div class="card">
      <h3>Commands</h3>
      <pre><span class="cmt"># Enable SSH on Kria (physical terminal)</span>
<span class="cmd">sudo systemctl enable --now ssh</span>

<span class="cmt"># Host PC (PowerShell)</span>
<span class="cmd">ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519</span>

<span class="cmd">type ~/.ssh/id_ed25519.pub | ssh
  ubuntu@192.168.68.60
  "mkdir -p ~/.ssh &amp;&amp;
   cat >> ~/.ssh/authorized_keys"</span>

<span class="cmt"># Verify passwordless</span>
<span class="cmd">ssh ubuntu@192.168.68.60 "echo ok"</span>
connected successfully</pre>
    </div>
  </div>
</div>

<!-- S5: Software Stack -->
<div class="slide">
  <h2>Software Stack Decision</h2>
  <div class="grid-3">
    <div class="card">
      <h3 style="color:#e8391d">Vitis AI (apt)</h3>
      <ul>
        <li>Not available for Ubuntu 24.04</li>
        <li>Targets Ubuntu 20.04/22.04</li>
        <li>No matching apt package found</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="color:#e8391d">PYNQ</h3>
      <ul>
        <li>pip install failed</li>
        <li>Build error on Python 3.12/aarch64</li>
        <li>Requires older Python version</li>
      </ul>
    </div>
    <div class="card good">
      <h3 style="color:#4caf50">ONNX Runtime</h3>
      <ul>
        <li>Available for aarch64</li>
        <li>Supports Python 3.12</li>
        <li>Runs MobileNet/YOLO/ResNet</li>
        <li>Extensible to DPU EP later</li>
      </ul>
    </div>
  </div>
  <div style="margin-top:20px">
    <h3>Installation</h3>
    <pre><span class="cmd">python3 -m venv ~/vitis-env
~/vitis-env/bin/pip install onnxruntime numpy pillow</span>
<span class="cmt"># onnxruntime-1.26.0  numpy-2.4.6  pillow-12.2.0</span></pre>
  </div>
</div>

<!-- S6: CNN Pipeline -->
<div class="slide">
  <h2>CNN Inference Pipeline</h2>
  <div class="grid-2">
    <div>
      <h3>Model</h3>
      <ul>
        <li><strong>MobileNetV2</strong> — ImageNet (1000 classes)</li>
        <li>Format: ONNX · Size: 14 MB</li>
        <li>Input: 224x224 RGB</li>
        <li>Source: ONNX Model Zoo (official)</li>
      </ul>
      <h3 style="margin-top:18px">Pipeline Steps</h3>
      <ul>
        <li>Load image, resize to 224x224</li>
        <li>Normalize using ImageNet mean/std</li>
        <li>HWC to CHW, add batch dimension</li>
        <li>Run ONNX Runtime session (CPU EP)</li>
        <li>Softmax, return Top-5 predictions</li>
      </ul>
    </div>
    <div class="card">
      <h3>Code</h3>
      <pre><span class="cmd">session = ort.InferenceSession(
    "mobilenet.onnx",
    providers=["CPUExecutionProvider"])</span>

<span class="cmt"># Preprocess image</span>
img = Image.open("fish.jpg").resize((224,224))
x = np.array(img, dtype=np.float32)
x = (x/255.0 - mean) / std
<span class="cmt"># HWC to CHW, add batch</span>
x = x.transpose(2,0,1)[None]

<span class="cmt"># Run inference</span>
out = session.run(None, {{"input": x}})
top5 = np.argsort(out[0][0])[::-1][:5]</pre>
    </div>
  </div>
</div>

<!-- S7: Results -->
<div class="slide">
  <h2>Results — MobileNetV2 on Kria KV260</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:14px;margin-bottom:18px">
    <div class="stat-box"><div class="number">87.5<span style="font-size:.45em">ms</span></div><div class="label">Inference Time</div></div>
    <div class="stat-box"><div class="number">14<span style="font-size:.45em">MB</span></div><div class="label">Model Size</div></div>
    <div class="stat-box"><div class="number">1000</div><div class="label">Classes</div></div>
    <div class="stat-box" style="border-color:#4caf5044"><div class="number" style="color:#4caf50">TENCH</div><div class="label">Top-1 Correct</div></div>
  </div>
  <div style="display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:18px;align-items:start">
    <div class="card">
      <h3>Run Details</h3>
      <div class="result-row"><span class="key">Model</span><span class="val">MobileNetV2-12 (ONNX)</span></div>
      <div class="result-row"><span class="key">Runtime</span><span class="val">ONNX Runtime 1.26.0</span></div>
      <div class="result-row"><span class="key">Device</span><span class="val">ARM Cortex-A53</span></div>
      <div class="result-row"><span class="key">Inference</span><span class="val good">87.5 ms</span></div>
      <div class="result-row"><span class="key">Top-1</span><span class="val good">tench (correct!)</span></div>
      <div class="result-row"><span class="key">Status</span><span class="val good">Working end-to-end</span></div>
    </div>
    <div style="text-align:center">
      <img src="{fish_img}" style="width:100%;max-height:220px;object-fit:cover;border-radius:8px;border:1px solid #333">
      <span style="font-size:.8em;color:#666;margin-top:6px;display:block">Input: tench fish (ImageNet sample)</span>
    </div>
    <div class="card">
      <h3>Top-5 Predictions</h3>
      <div class="result-row"><span class="val good">1. tench</span><span style="color:#4caf50">17.54</span></div>
      <div class="result-row"><span class="key">2. snoek</span><span class="key">11.21</span></div>
      <div class="result-row"><span class="key">3. coho salmon</span><span class="key">10.44</span></div>
      <div class="result-row"><span class="key">4. bolete</span><span class="key">10.28</span></div>
      <div class="result-row"><span class="key">5. goldfish</span><span class="key">9.78</span></div>
    </div>
  </div>
</div>

<!-- S8: Roadmap -->
<div class="slide">
  <h2>Roadmap</h2>
  <div class="roadmap-phase done">
    <h4>Phase 1 — Board Bring-up &amp; CPU Inference <span style="float:right;color:#4caf50;font-size:.82em">DONE</span></h4>
    <p>SSH setup · ONNX Runtime · MobileNetV2 · 87.5ms on ARM Cortex-A53 · tench correctly identified</p>
  </div>
  <div class="roadmap-phase next">
    <h4>Phase 2 — DPU Acceleration <span style="float:right;color:#ffc107;font-size:.82em">NEXT</span></h4>
    <p>Load DPU overlay via xmutil · ONNX DPU Execution Provider · Target: ~5-10ms (8-17x speedup)</p>
  </div>
  <div class="roadmap-phase future">
    <h4>Phase 3 — YOLO Object Detection <span style="float:right;color:#2196f3;font-size:.82em">PLANNED</span></h4>
    <p>Quantize YOLOv8 INT8 with Vitis AI · Deploy on DPU · Live camera inference (CSI / USB)</p>
  </div>
  <div class="roadmap-phase hls">
    <h4>Phase 4 — Custom HLS CNN <span style="float:right;color:#9c27b0;font-size:.82em">FUTURE</span></h4>
    <p>hls4ml: Keras model to HLS C++ to bitstream · Custom accelerator synthesis with Vitis HLS</p>
  </div>
</div>

<!-- S9: Key Learnings -->
<div class="slide">
  <h2>Key Learnings</h2>
  <div class="grid-2">
    <div>
      <h3>Technical</h3>
      <ul>
        <li>Ubuntu 24.04 is cutting-edge — Vitis AI apt packages not yet available for Noble</li>
        <li>ONNX Runtime is a solid fallback for aarch64 without full Vitis AI stack</li>
        <li>xmutil + dfx-mgr is the right path for DPU overlay management</li>
        <li>TTL=64 on ping quickly confirms a Linux target</li>
      </ul>
    </div>
    <div>
      <h3>Process</h3>
      <ul>
        <li>Always verify host and target are on the <strong>same subnet</strong></li>
        <li>SSH key auth is essential for automated remote iteration</li>
        <li>Physical board access saved significant time for initial setup</li>
        <li>Watch disk: eMMC at 64% before Docker or model installs</li>
      </ul>
    </div>
  </div>
  <div style="margin-top:22px;padding:14px 20px;background:#1a1a2e;border-radius:9px;border:1px solid #333">
    <p><strong style="color:#e8391d">Bottom line:</strong> Full CNN inference pipeline working on Kria KV260 in a single session. Top-1 = tench correctly at 87.5ms on ARM CPU. Next milestone: DPU acceleration to under 10ms, then YOLO.</p>
  </div>
</div>

<div id="nav">
  <button onclick="go(-1)">Prev</button>
  <span id="counter">1 / 9</span>
  <button onclick="go(1)">Next</button>
</div>
<script>
const slides=document.querySelectorAll('.slide');let cur=0;
function show(n){{slides[cur].classList.remove('active');cur=(n+slides.length)%slides.length;slides[cur].classList.add('active');document.getElementById('counter').textContent=(cur+1)+' / '+slides.length;}}
function go(d){{show(cur+d);}}
document.addEventListener('keydown',e=>{{if(e.key==='ArrowRight'||e.key==='ArrowDown')go(1);if(e.key==='ArrowLeft'||e.key==='ArrowUp')go(-1);}});
</script>
</body>
</html>"""

with open("kria-kv260-slides.html", "w") as f:
    f.write(html)
print("Saved: kria-kv260-slides.html")
