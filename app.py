import os
import requests
import json
import base64
import io
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from history_logger import HistoryLogger
from model_manager import ModelManager
from text_engine import TextEngine
from evaluation import Evaluator

app = Flask(__name__)

hf_token = os.environ.get("HF_TOKEN", "")
replicate_token = os.environ.get("REPLICATE_TOKEN", "")
HF_SPACE_URL = "https://shef370-ai-content-generator.hf.space"

try:
    manager = ModelManager()
    text_engine = TextEngine(hf_token)
    logger = HistoryLogger()
    evaluator = Evaluator()
    print("Engines initialized")
except Exception as e:
    print(f"Init error: {e}")
    raise

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AICIG - AI Content & Image Generator</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
  header { background: linear-gradient(135deg, #1e3a5f, #7c3aed); padding: 24px 40px; }
  header h1 { font-size: 1.8rem; font-weight: 700; }
  header p { opacity: 0.8; margin-top: 4px; }
  .tabs { display: flex; background: #1e293b; padding: 0 40px; border-bottom: 1px solid #334155; }
  .tab { padding: 14px 24px; cursor: pointer; border-bottom: 3px solid transparent; color: #94a3b8; font-weight: 500; transition: all 0.2s; }
  .tab.active { border-bottom-color: #7c3aed; color: #fff; }
  .tab:hover { color: #fff; }
  .content { padding: 32px 40px; max-width: 1200px; }
  .panel { display: none; }
  .panel.active { display: block; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .card { background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; }
  label { display: block; font-size: 0.85rem; color: #94a3b8; margin-bottom: 6px; font-weight: 500; }
  textarea, select, input[type=range] { width: 100%; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; padding: 10px 14px; font-size: 0.95rem; resize: vertical; }
  textarea { min-height: 100px; }
  select { padding: 10px 14px; cursor: pointer; }
  .row { display: flex; gap: 16px; margin-top: 16px; }
  .row > div { flex: 1; }
  button { background: #7c3aed; color: white; border: none; border-radius: 8px; padding: 12px 28px; font-size: 1rem; font-weight: 600; cursor: pointer; width: 100%; margin-top: 16px; transition: background 0.2s; }
  button:hover { background: #6d28d9; }
  button:disabled { background: #4c1d95; cursor: wait; }
  .output { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 16px; min-height: 120px; white-space: pre-wrap; font-size: 0.9rem; line-height: 1.6; color: #cbd5e1; margin-top: 16px; }
  .meta { font-size: 0.8rem; color: #64748b; margin-top: 8px; }
  img#gen-image { max-width: 100%; border-radius: 8px; margin-top: 16px; display: none; }
  .spinner { display: none; text-align: center; padding: 20px; color: #7c3aed; }
  .error { color: #f87171; }
  .success { color: #4ade80; }
  h2 { font-size: 1.2rem; margin-bottom: 20px; color: #c4b5fd; }
  .slider-row { display: flex; align-items: center; gap: 10px; }
  .slider-val { color: #c4b5fd; font-weight: 600; min-width: 40px; text-align: right; }
</style>
</head>
<body>
<header>
  <h1>🤖 AICIG — AI Content & Image Generator</h1>
  <p>Final Year Project | Shefat Mazibar (W1967304) | University of Westminster</p>
</header>
<div class="tabs">
  <div class="tab active" onclick="showTab('text')">📝 Text Generation</div>
  <div class="tab" onclick="showTab('image')">🖼️ Image Generation</div>
  <div class="tab" onclick="showTab('both')">🔀 Generate Both</div>
  <div class="tab" onclick="showTab('history')">📊 History</div>
</div>
<div class="content">

  <!-- TEXT TAB -->
  <div class="panel active" id="tab-text">
    <div class="grid">
      <div class="card">
        <h2>Text Settings</h2>
        <label>Prompt</label>
        <textarea id="t-prompt" placeholder="Write a blog post about AI..."></textarea>
        <div class="row">
          <div>
            <label>Model</label>
            <select id="t-model">
              <option value="qwen-7b">Qwen 2.5 7B</option>
              <option value="llama-8b">Llama 3.1 8B</option>
              <option value="deepseek">DeepSeek R1 7B</option>
            </select>
          </div>
          <div>
            <label>Profile</label>
            <select id="t-profile">
              <option value="balanced">Balanced</option>
              <option value="creative">Creative</option>
              <option value="precise">Precise</option>
              <option value="fast">Fast</option>
            </select>
          </div>
        </div>
        <div class="row">
          <div>
            <label>Max Tokens: <span id="t-tokens-val">300</span></label>
            <div class="slider-row"><input type="range" id="t-tokens" min="50" max="500" value="300" step="10" oninput="document.getElementById('t-tokens-val').textContent=this.value"></div>
          </div>
          <div>
            <label>Temperature: <span id="t-temp-val">0.7</span></label>
            <div class="slider-row"><input type="range" id="t-temp" min="0.1" max="2.0" value="0.7" step="0.1" oninput="document.getElementById('t-temp-val').textContent=parseFloat(this.value).toFixed(1)"></div>
          </div>
        </div>
        <button onclick="generateText()" id="t-btn">Generate Text</button>
      </div>
      <div class="card">
        <h2>Output</h2>
        <div class="spinner" id="t-spinner">⏳ Generating...</div>
        <div class="output" id="t-output">Your generated text will appear here...</div>
        <div class="meta" id="t-meta"></div>
      </div>
    </div>
  </div>

  <!-- IMAGE TAB -->
  <div class="panel" id="tab-image">
    <div class="grid">
      <div class="card">
        <h2>Image Settings</h2>
        <label>Prompt</label>
        <textarea id="i-prompt" placeholder="A futuristic city at sunset..."></textarea>
        <label style="margin-top:16px">Model</label>
        <select id="i-model">
          <option value="stable-diffusion-v1-5">Stable Diffusion v1.5</option>
          <option value="sdxl-base">Stable Diffusion XL</option>
        </select>
        <div class="row">
          <div>
            <label>Width: <span id="i-width-val">384</span></label>
            <input type="range" id="i-width" min="256" max="512" value="384" step="64" oninput="document.getElementById('i-width-val').textContent=this.value">
          </div>
          <div>
            <label>Height: <span id="i-height-val">384</span></label>
            <input type="range" id="i-height" min="256" max="512" value="384" step="64" oninput="document.getElementById('i-height-val').textContent=this.value">
          </div>
          <div>
            <label>Steps: <span id="i-steps-val">15</span></label>
            <input type="range" id="i-steps" min="10" max="25" value="15" step="5" oninput="document.getElementById('i-steps-val').textContent=this.value">
          </div>
        </div>
        <button onclick="generateImage()" id="i-btn">Generate Image</button>
      </div>
      <div class="card">
        <h2>Output</h2>
        <div class="spinner" id="i-spinner">⏳ Generating image (2-3 min on CPU)...</div>
        <img id="gen-image" alt="Generated image">
        <div class="meta" id="i-meta">Image will appear here after generation.</div>
      </div>
    </div>
  </div>

  <!-- BOTH TAB -->
  <div class="panel" id="tab-both">
    <div class="grid">
      <div class="card">
        <h2>Settings</h2>
        <label>Prompt (used for both text and image)</label>
        <textarea id="b-prompt" placeholder="A futuristic city with flying cars..."></textarea>
        <div class="row">
          <div>
            <label>Text Model</label>
            <select id="b-tmodel">
              <option value="qwen-7b">Qwen 2.5 7B</option>
              <option value="llama-8b">Llama 3.1 8B</option>
              <option value="deepseek">DeepSeek R1 7B</option>
            </select>
          </div>
          <div>
            <label>Profile</label>
            <select id="b-profile">
              <option value="balanced">Balanced</option>
              <option value="creative">Creative</option>
              <option value="precise">Precise</option>
              <option value="fast">Fast</option>
            </select>
          </div>
        </div>
        <button onclick="generateBoth()" id="b-btn">Generate Both</button>
      </div>
      <div class="card">
        <h2>Output</h2>
        <div class="spinner" id="b-spinner">⏳ Generating...</div>
        <div class="output" id="b-text-output">Text output will appear here...</div>
        <div class="meta" id="b-text-meta"></div>
        <img id="b-image" alt="Generated image" style="max-width:100%;border-radius:8px;margin-top:16px;display:none">
        <div class="meta" id="b-image-meta" style="margin-top:8px"></div>
      </div>
    </div>
  </div>

  <!-- HISTORY TAB -->
  <div class="panel" id="tab-history">
    <div class="card">
      <h2>Generation History</h2>
      <button onclick="loadHistory()" style="width:auto;padding:10px 20px">Refresh History</button>
      <div class="output" id="history-out" style="margin-top:16px">Click Refresh to load history.</div>
    </div>
  </div>

</div>
<script>
function showTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  event.target.classList.add('active');
}

async function generateText() {
  const prompt = document.getElementById('t-prompt').value.trim();
  if (!prompt) { alert('Please enter a prompt'); return; }
  const btn = document.getElementById('t-btn');
  btn.disabled = true; btn.textContent = 'Generating...';
  document.getElementById('t-spinner').style.display = 'block';
  document.getElementById('t-output').textContent = '';
  try {
    const res = await fetch('/generate_text', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        prompt, model_key: document.getElementById('t-model').value,
        profile: document.getElementById('t-profile').value,
        max_tokens: parseInt(document.getElementById('t-tokens').value),
        temperature: parseFloat(document.getElementById('t-temp').value)
      })
    });
    const data = await res.json();
    document.getElementById('t-output').textContent = data.text || data.error || 'No output';
    document.getElementById('t-meta').textContent = data.meta || '';
    if (data.error) document.getElementById('t-output').classList.add('error');
    else document.getElementById('t-output').classList.remove('error');
  } catch(e) {
    document.getElementById('t-output').textContent = 'Network error: ' + e.message;
  }
  btn.disabled = false; btn.textContent = 'Generate Text';
  document.getElementById('t-spinner').style.display = 'none';
}

async function generateImage() {
  const prompt = document.getElementById('i-prompt').value.trim();
  if (!prompt) { alert('Please enter a prompt'); return; }
  const btn = document.getElementById('i-btn');
  btn.disabled = true; btn.textContent = 'Generating (2-3 min)...';
  document.getElementById('i-spinner').style.display = 'block';
  document.getElementById('gen-image').style.display = 'none';
  document.getElementById('i-meta').textContent = 'Calling HF Space... please wait';
  try {
    const res = await fetch('/generate_image', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        prompt,
        width: parseInt(document.getElementById('i-width').value),
        height: parseInt(document.getElementById('i-height').value),
        steps: parseInt(document.getElementById('i-steps').value)
      })
    });
    const data = await res.json();
    if (data.image_b64) {
      const img = document.getElementById('gen-image');
      img.src = 'data:image/png;base64,' + data.image_b64;
      img.style.display = 'block';
      document.getElementById('i-meta').textContent = data.meta || '';
    } else {
      document.getElementById('i-meta').textContent = 'Error: ' + (data.error || 'Unknown error');
    }
  } catch(e) {
    document.getElementById('i-meta').textContent = 'Network error: ' + e.message;
  }
  btn.disabled = false; btn.textContent = 'Generate Image';
  document.getElementById('i-spinner').style.display = 'none';
}

async function generateBoth() {
  const prompt = document.getElementById('b-prompt').value.trim();
  if (!prompt) { alert('Please enter a prompt'); return; }
  const btn = document.getElementById('b-btn');
  btn.disabled = true; btn.textContent = 'Generating...';
  document.getElementById('b-spinner').style.display = 'block';
  try {
    const [tr, ir] = await Promise.all([
      fetch('/generate_text', {method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({prompt,model_key:document.getElementById('b-tmodel').value,
          profile:document.getElementById('b-profile').value,max_tokens:300,temperature:0.7})}),
      fetch('/generate_image', {method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({prompt,width:384,height:384,steps:15})})
    ]);
    const td = await tr.json();
    const id = await ir.json();
    document.getElementById('b-text-output').textContent = td.text || td.error || 'No text output';
    document.getElementById('b-text-meta').textContent = td.meta || '';
    if (id.image_b64) {
      const img = document.getElementById('b-image');
      img.src = 'data:image/png;base64,' + id.image_b64;
      img.style.display = 'block';
      document.getElementById('b-image-meta').textContent = id.meta || '';
    }
  } catch(e) {
    document.getElementById('b-text-output').textContent = 'Error: ' + e.message;
  }
  btn.disabled = false; btn.textContent = 'Generate Both';
  document.getElementById('b-spinner').style.display = 'none';
}

async function loadHistory() {
  const res = await fetch('/history');
  const data = await res.json();
  const out = document.getElementById('history-out');
  if (!data.entries || data.entries.length === 0) { out.textContent = 'No history yet.'; return; }
  out.textContent = data.entries.map(e =>
    `[${e.type.toUpperCase()}] ${e.timestamp.slice(0,19)} | ${e.model}\n> ${e.prompt.slice(0,100)}...`
  ).join('\n\n');
}
</script>
</body>
</html>"""

@app.route("/")
def index():
    return HTML

@app.route("/generate_text", methods=["POST"])
def api_generate_text():
    try:
        data = request.json
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return jsonify({"error": "No prompt provided"})
        if not hf_token:
            return jsonify({"error": "HF_TOKEN not configured"})

        model_key = data.get("model_key", "qwen-7b")
        profile = data.get("profile", "balanced")
        max_tokens = int(data.get("max_tokens", 300))
        temperature = float(data.get("temperature", 0.7))

        config = manager.get_model_config(model_key)
        params = manager.get_profile(profile)
        params.update({"max_tokens": max_tokens, "temperature": temperature})

        text, elapsed = text_engine.generate(prompt, config["model_id"], **params)
        if text.startswith("Error:"):
            return jsonify({"error": text})

        bleu = evaluator.bleu_score(prompt, text)
        logger.log("text", prompt, text, model_key, params, {"bleu": bleu, "time": elapsed})

        return jsonify({
            "text": text,
            "meta": f"BLEU: {bleu:.4f} | Time: {elapsed:.2f}s | Model: {config['model_id']}"
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/generate_image", methods=["POST"])
def api_generate_image():
    try:
        data = request.json
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return jsonify({"error": "No prompt provided"})

        width = int(data.get("width", 384))
        height = int(data.get("height", 384))
        steps = int(data.get("steps", 15))

        enhanced = prompt + ", highly detailed, high quality, sharp focus"
        start = time.time()

        api_url = f"{HF_SPACE_URL}/api/predict"
        payload = {
            "fn_index": 0,
            "data": [enhanced, width, height, steps],
            "session_hash": "aicig"
        }

        resp = requests.post(api_url, json=payload, timeout=300)
        elapsed = time.time() - start

        if resp.status_code == 200:
            result = resp.json()
            if "data" in result and result["data"] and result["data"][0]:
                image_data = result["data"][0]
                if isinstance(image_data, str):
                    if "," in image_data:
                        image_data = image_data.split(",", 1)[1]
                    logger.log("image", prompt, "generated", "hf-space", {}, {"time": elapsed})
                    return jsonify({
                        "image_b64": image_data,
                        "meta": f"Generated in {elapsed:.1f}s via HF Space"
                    })
            return jsonify({"error": f"HF Space returned no image. Response: {str(result)[:200]}"})
        else:
            return jsonify({"error": f"HF Space error {resp.status_code}: {resp.text[:200]}"})

    except requests.Timeout:
        return jsonify({"error": "HF Space timed out (CPU generation takes 2-3 min, try again)"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/history")
def api_history():
    try:
        entries = logger.get_history(20)
        return jsonify({"entries": list(reversed(entries))})
    except Exception as e:
        return jsonify({"entries": [], "error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
