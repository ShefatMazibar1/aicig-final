import os
import io
import base64
import time
import requests
from flask import Flask, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

try:
    from model_manager import ModelManager
    manager = ModelManager()
    print("ModelManager loaded")
except Exception as e:
    manager = None
    print(f"ModelManager failed: {e}")

try:
    from text_engine import TextEngine
    text_engine = TextEngine()
    print("TextEngine loaded")
except Exception as e:
    text_engine = None
    print(f"TextEngine failed: {e}")

try:
    from evaluation import Evaluator
    evaluator = Evaluator()
    print("Evaluator loaded")
except Exception as e:
    evaluator = None

try:
    from history_logger import HistoryLogger
    logger = HistoryLogger()
    print("HistoryLogger loaded")
except Exception as e:
    logger = None

try:
    from image_engine import ImageEngine
    image_engine = ImageEngine()
    print("ImageEngine loaded")
except Exception as e:
    image_engine = None
    print(f"ImageEngine failed: {e}")

print("App ready")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AICIG - AI Content & Image Generator</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
header{background:linear-gradient(135deg,#1e3a5f,#7c3aed);padding:24px 40px}
header h1{font-size:1.8rem;font-weight:700}
header p{opacity:.8;margin-top:4px}
.tabs{display:flex;background:#1e293b;padding:0 40px;border-bottom:1px solid #334155;overflow-x:auto}
.tab{padding:14px 24px;cursor:pointer;border-bottom:3px solid transparent;color:#94a3b8;font-weight:500;white-space:nowrap}
.tab.active{border-bottom-color:#7c3aed;color:#fff}
.tab:hover{color:#fff}
.content{padding:32px 40px;max-width:1200px;margin:0 auto}
.panel{display:none}.panel.active{display:block}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media(max-width:768px){.grid{grid-template-columns:1fr}}
.card{background:#1e293b;border-radius:12px;padding:24px;border:1px solid #334155}
h2{font-size:1.1rem;margin-bottom:20px;color:#c4b5fd;font-weight:600}
label{display:block;font-size:.85rem;color:#94a3b8;margin-bottom:6px;font-weight:500;margin-top:14px}
label:first-child{margin-top:0}
textarea{width:100%;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;padding:10px 14px;font-size:.95rem;resize:vertical;min-height:100px}
select{width:100%;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;padding:10px 14px;font-size:.9rem;cursor:pointer}
.row{display:flex;gap:16px;margin-top:0}.row>div{flex:1}
input[type=range]{width:100%;accent-color:#7c3aed;margin-top:4px}
button.primary{background:#7c3aed;color:#fff;border:none;border-radius:8px;padding:12px 28px;font-size:1rem;font-weight:600;cursor:pointer;width:100%;margin-top:20px;transition:background .2s}
button.primary:hover{background:#6d28d9}
button.primary:disabled{background:#4c1d95;cursor:wait}
.output-box{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:16px;min-height:120px;white-space:pre-wrap;font-size:.9rem;line-height:1.6;color:#cbd5e1;margin-top:16px;word-break:break-word}
.meta{font-size:.8rem;color:#64748b;margin-top:8px}
.error-text{color:#f87171}.success-text{color:#4ade80}
img.result-img{max-width:100%;border-radius:8px;margin-top:16px;display:none;border:1px solid #334155}
.status{font-size:.85rem;padding:8px 12px;border-radius:6px;margin-top:12px;display:none}
.status.loading{background:#1e3a5f;color:#93c5fd;display:block}
.status.error{background:#7f1d1d;color:#fca5a5;display:block}
.status.success{background:#14532d;color:#86efac;display:block}
</style>
</head>
<body>
<header>
  <h1>🤖 AICIG — AI Content & Image Generator</h1>
  <p>Final Year Project | Shefat Mazibar (W1967304) | University of Westminster</p>
</header>
<div class="tabs">
  <div class="tab active" onclick="showTab('text',this)">📝 Text Generation</div>
  <div class="tab" onclick="showTab('image',this)">🖼️ Image Generation</div>
  <div class="tab" onclick="showTab('both',this)">🔀 Generate Both</div>
  <div class="tab" onclick="showTab('history',this)">📊 History</div>
</div>
<div class="content">
  <div class="panel active" id="tab-text">
    <div class="grid">
      <div class="card">
        <h2>Text Settings</h2>
        <label>Prompt</label>
        <textarea id="t-prompt" placeholder="Write a blog post about AI..."></textarea>
        <div class="row" style="margin-top:14px">
          <div><label>Model</label>
            <select id="t-model">
              <option value="qwen-7b">Qwen 2.5 7B</option>
              <option value="llama-8b">Llama 3.1 8B</option>
            </select>
          </div>
          <div><label>Profile</label>
            <select id="t-profile">
              <option value="balanced">Balanced</option>
              <option value="creative">Creative</option>
              <option value="precise">Precise</option>
              <option value="fast">Fast</option>
            </select>
          </div>
        </div>
        <label>Max Tokens: <span id="t-tokens-val">300</span></label>
        <input type="range" id="t-tokens" min="50" max="500" value="300" step="10"
          oninput="document.getElementById('t-tokens-val').textContent=this.value">
        <label>Temperature: <span id="t-temp-val">0.7</span></label>
        <input type="range" id="t-temp" min="1" max="20" value="7" step="1"
          oninput="document.getElementById('t-temp-val').textContent=(this.value/10).toFixed(1)">
        <button class="primary" id="t-btn" onclick="generateText()">Generate Text</button>
        <div class="status" id="t-status"></div>
      </div>
      <div class="card">
        <h2>Output</h2>
        <div class="output-box" id="t-output">Your generated text will appear here...</div>
        <div class="meta" id="t-meta"></div>
      </div>
    </div>
  </div>

  <div class="panel" id="tab-image">
    <div class="grid">
      <div class="card">
        <h2>Image Settings</h2>
        <label>Prompt</label>
        <textarea id="i-prompt" placeholder="A futuristic city at sunset..."></textarea>
        <label>Width: <span id="i-w-val">384</span>px</label>
        <input type="range" id="i-width" min="256" max="512" value="384" step="64"
          oninput="document.getElementById('i-w-val').textContent=this.value">
        <label>Height: <span id="i-h-val">384</span>px</label>
        <input type="range" id="i-height" min="256" max="512" value="384" step="64"
          oninput="document.getElementById('i-h-val').textContent=this.value">
        <label>Steps: <span id="i-s-val">15</span></label>
        <input type="range" id="i-steps" min="10" max="25" value="15" step="5"
          oninput="document.getElementById('i-s-val').textContent=this.value">
        <button class="primary" id="i-btn" onclick="generateImage()">Generate Image</button>
        <div class="status" id="i-status"></div>
      </div>
      <div class="card">
        <h2>Output</h2>
        <img class="result-img" id="i-img" alt="Generated image">
        <div class="output-box" id="i-output">Image will appear here after generation.</div>
      </div>
    </div>
  </div>

  <div class="panel" id="tab-both">
    <div class="grid">
      <div class="card">
        <h2>Settings</h2>
        <label>Prompt (used for both text and image)</label>
        <textarea id="b-prompt" placeholder="A futuristic city with flying cars..."></textarea>
        <div class="row" style="margin-top:14px">
          <div><label>Text Model</label>
            <select id="b-tmodel">
              <option value="qwen-7b">Qwen 2.5 7B</option>
              <option value="llama-8b">Llama 3.1 8B</option>
            </select>
          </div>
          <div><label>Profile</label>
            <select id="b-profile">
              <option value="balanced">Balanced</option>
              <option value="creative">Creative</option>
              <option value="precise">Precise</option>
              <option value="fast">Fast</option>
            </select>
          </div>
        </div>
        <button class="primary" id="b-btn" onclick="generateBoth()">Generate Both</button>
        <div class="status" id="b-status"></div>
      </div>
      <div class="card">
        <h2>Output</h2>
        <div class="output-box" id="b-text">Text output appears here...</div>
        <div class="meta" id="b-text-meta"></div>
        <img class="result-img" id="b-img" alt="Generated image" style="margin-top:16px">
        <div class="meta" id="b-img-meta"></div>
      </div>
    </div>
  </div>

  <div class="panel" id="tab-history">
    <div class="card">
      <h2>Generation History</h2>
      <button class="primary" style="width:auto;padding:10px 24px" onclick="loadHistory()">Refresh History</button>
      <div class="output-box" id="h-output" style="margin-top:16px">Click Refresh to load history.</div>
    </div>
  </div>
</div>

<script>
function showTab(name,el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  el.classList.add('active');
}
function setStatus(id,msg,type){
  const el=document.getElementById(id);
  el.textContent=msg;el.className='status '+type;
}
async function generateText(){
  const prompt=document.getElementById('t-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('t-btn');
  btn.disabled=true;btn.textContent='Generating...';
  setStatus('t-status','Generating text...','loading');
  document.getElementById('t-output').textContent='';
  try{
    const resp=await fetch('/generate_text',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt,
        model_key:document.getElementById('t-model').value,
        profile:document.getElementById('t-profile').value,
        max_tokens:parseInt(document.getElementById('t-tokens').value),
        temperature:parseFloat(document.getElementById('t-temp').value)/10})});
    const data=await resp.json();
    if(data.error){
      document.getElementById('t-output').innerHTML='<span class="error-text">'+data.error+'</span>';
      setStatus('t-status','Failed','error');
    }else{
      document.getElementById('t-output').textContent=data.text;
      document.getElementById('t-meta').textContent=data.meta||'';
      setStatus('t-status','Done!','success');
    }
  }catch(e){
    document.getElementById('t-output').innerHTML='<span class="error-text">Network error: '+e.message+'</span>';
    setStatus('t-status','Network error','error');
  }
  btn.disabled=false;btn.textContent='Generate Text';
}
async function generateImage(){
  const prompt=document.getElementById('i-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('i-btn');
  btn.disabled=true;btn.textContent='Generating...';
  setStatus('i-status','Calling Pollinations.ai...','loading');
  document.getElementById('i-img').style.display='none';
  document.getElementById('i-output').textContent='Generating image...';
  try{
    const resp=await fetch('/generate_image',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt,
        width:parseInt(document.getElementById('i-width').value),
        height:parseInt(document.getElementById('i-height').value),
        steps:parseInt(document.getElementById('i-steps').value)})});
    const data=await resp.json();
    if(data.image_b64){
      const img=document.getElementById('i-img');
      img.src='data:image/png;base64,'+data.image_b64;
      img.style.display='block';
      document.getElementById('i-output').textContent=data.meta||'Generated!';
      setStatus('i-status','Image generated!','success');
    }else{
      document.getElementById('i-output').innerHTML='<span class="error-text">'+(data.error||'Unknown error')+'</span>';
      setStatus('i-status','Failed','error');
    }
  }catch(e){
    setStatus('i-status','Network error','error');
  }
  btn.disabled=false;btn.textContent='Generate Image';
}
async function generateBoth(){
  const prompt=document.getElementById('b-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('b-btn');
  btn.disabled=true;btn.textContent='Generating...';
  setStatus('b-status','Generating text and image...','loading');
  try{
    const[tr,ir]=await Promise.all([
      fetch('/generate_text',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({prompt,model_key:document.getElementById('b-tmodel').value,
          profile:document.getElementById('b-profile').value,max_tokens:300,temperature:0.7})}),
      fetch('/generate_image',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({prompt,width:384,height:384,steps:15})})
    ]);
    const td=await tr.json();const id=await ir.json();
    document.getElementById('b-text').textContent=td.text||('Error: '+td.error);
    document.getElementById('b-text-meta').textContent=td.meta||'';
    if(id.image_b64){
      const img=document.getElementById('b-img');
      img.src='data:image/png;base64,'+id.image_b64;
      img.style.display='block';
      document.getElementById('b-img-meta').textContent=id.meta||'';
    }else{
      document.getElementById('b-img-meta').textContent='Image error: '+(id.error||'Unknown');
    }
    setStatus('b-status','Done!','success');
  }catch(e){
    setStatus('b-status','Error: '+e.message,'error');
  }
  btn.disabled=false;btn.textContent='Generate Both';
}
async function loadHistory(){
  try{
    const resp=await fetch('/history');
    const data=await resp.json();
    const out=document.getElementById('h-output');
    if(!data.entries||data.entries.length===0){
      out.textContent='No history yet.';
    }else{
      out.textContent=data.entries.map(e=>
        '['+e.type.toUpperCase()+'] '+e.timestamp.slice(0,19)+' | '+e.model+'\n> '+e.prompt.slice(0,120)
      ).join('\n\n');
    }
  }catch(e){document.getElementById('h-output').textContent='Error: '+e.message;}
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
        data = request.get_json(force=True)
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "No prompt provided"})
        if not text_engine:
            return jsonify({"error": "TextEngine not loaded"})
        if not manager:
            return jsonify({"error": "ModelManager not loaded"})

        model_key = data.get("model_key", "qwen-7b")
        profile_name = data.get("profile", "balanced")
        max_tokens = int(data.get("max_tokens", 300))
        temperature = float(data.get("temperature", 0.7))

        config = manager.get_model_config(model_key)
        params = manager.get_profile(profile_name)
        params.update({"max_tokens": max_tokens, "temperature": temperature})

        text, elapsed = text_engine.generate(prompt, config["model_id"], **params)
        if text.startswith("Error:"):
            return jsonify({"error": text})

        bleu = 0.0
        if evaluator:
            try:
                bleu = evaluator.bleu_score(prompt, text)
            except Exception:
                pass
        if logger:
            try:
                logger.log("text", prompt, text, model_key, params, {"bleu": bleu, "time": elapsed})
            except Exception:
                pass

        return jsonify({
            "text": text,
            "meta": f"BLEU: {bleu:.4f} | Time: {elapsed:.2f}s | Model: {config['model_id']}"
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/generate_image", methods=["POST"])
def api_generate_image():
    try:
        data = request.get_json(force=True)
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "No prompt provided"})
        if not image_engine:
            return jsonify({"error": "ImageEngine not loaded"})

        width = int(data.get("width", 384))
        height = int(data.get("height", 384))
        steps = int(data.get("steps", 15))

        image, elapsed, message = image_engine.generate(prompt, width=width, height=height, steps=steps)

        if image is not None:
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            if logger:
                try:
                    logger.log("image", prompt, "generated", "pollinations", {}, {"time": elapsed})
                except Exception:
                    pass
            return jsonify({"image_b64": b64, "meta": f"Generated in {elapsed:.1f}s via Pollinations.ai"})
        else:
            return jsonify({"error": message})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/history")
def api_history():
    try:
        if not logger:
            return jsonify({"entries": []})
        entries = logger.get_history(20)
        return jsonify({"entries": list(reversed(entries)) if entries else []})
    except Exception as e:
        return jsonify({"entries": [], "error": str(e)})

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "text_engine": text_engine is not None,
        "image_engine": image_engine is not None,
        "manager": manager is not None,
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
