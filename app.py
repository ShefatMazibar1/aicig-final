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
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AICIG Studio</title>
<style>
:root[data-theme="dark"]{
  --bg:#0a0a0f;--bg2:#111118;--bg3:#1a1a2e;--bg4:#16213e;
  --border:#ffffff18;--border2:#ffffff30;
  --text:#f0f0ff;--text2:#a0a0c0;--text3:#606080;
  --purple:#a855f7;--purple2:#7c3aed;--purple3:#4c1d95;
  --pink:#ec4899;--cyan:#06b6d4;--green:#10b981;
  --card:#ffffff08;--card2:#ffffff12;
  --neon-purple:0 0 20px #a855f740,0 0 40px #7c3aed20;
  --neon-pink:0 0 20px #ec489940,0 0 40px #ec489920;
  --neon-cyan:0 0 20px #06b6d440,0 0 40px #06b6d420;
}
:root[data-theme="light"]{
  --bg:#f8f7ff;--bg2:#ffffff;--bg3:#ede9fe;--bg4:#f3f0ff;
  --border:#7c3aed20;--border2:#7c3aed40;
  --text:#1e1b4b;--text2:#4c1d95;--text3:#7c3aed;
  --purple:#7c3aed;--purple2:#6d28d9;--purple3:#ede9fe;
  --pink:#db2777;--cyan:#0891b2;--green:#059669;
  --card:#7c3aed08;--card2:#7c3aed14;
  --neon-purple:0 2px 12px #7c3aed20;
  --neon-pink:0 2px 12px #db277720;
  --neon-cyan:0 2px 12px #0891b220;
}
*{box-sizing:border-box;margin:0;padding:0;transition:background .2s,color .2s,border-color .2s}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
.shell{display:grid;grid-template-columns:240px 1fr;flex:1;min-height:100vh}

/* Sidebar */
.sidebar{background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;position:relative;overflow:hidden}
.sidebar::before{content:'';position:absolute;top:-60px;left:-60px;width:180px;height:180px;background:var(--purple2);opacity:.12;border-radius:50%;filter:blur(40px);pointer-events:none}
.logo-area{padding:28px 24px 20px;border-bottom:1px solid var(--border)}
.logo-name{font-size:20px;font-weight:700;background:linear-gradient(90deg,var(--purple),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.logo-sub{font-size:11px;color:var(--text3);margin-top:3px;letter-spacing:.05em}
.nav-section{font-size:10px;color:var(--text3);padding:18px 24px 6px;letter-spacing:.1em;text-transform:uppercase}
.nav-item{display:flex;align-items:center;gap:12px;padding:10px 24px;cursor:pointer;font-size:13px;color:var(--text2);border-left:2px solid transparent;position:relative;transition:all .15s}
.nav-item:hover{color:var(--text);background:var(--card)}
.nav-item.active{color:var(--purple);border-left-color:var(--purple);background:var(--card2)}
.nav-item.active .nav-icon{filter:drop-shadow(0 0 6px var(--purple))}
.nav-icon{width:16px;height:16px;flex-shrink:0}
.sidebar-footer{margin-top:auto;padding:20px 24px;border-top:1px solid var(--border);font-size:11px;color:var(--text3);line-height:1.6}

/* Theme toggle */
.theme-toggle{display:flex;align-items:center;gap:8px;margin-bottom:12px}
.toggle-track{width:40px;height:22px;background:var(--card2);border:1px solid var(--border2);border-radius:11px;cursor:pointer;position:relative;transition:all .2s}
.toggle-thumb{position:absolute;top:3px;left:3px;width:14px;height:14px;border-radius:50%;background:var(--purple);transition:all .2s}
[data-theme="light"] .toggle-thumb{left:21px;background:var(--purple2)}
.toggle-label{font-size:11px;color:var(--text2)}

/* Main */
.main{display:flex;flex-direction:column;min-height:100vh}
.topbar{background:var(--bg2);border-bottom:1px solid var(--border);padding:16px 32px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10}
.topbar-left{display:flex;align-items:center;gap:12px}
.topbar-title{font-size:15px;font-weight:600}
.topbar-badge{font-size:10px;padding:3px 8px;border-radius:99px;background:var(--green);color:#fff;display:flex;align-items:center;gap:4px;opacity:.9}
.live-dot{width:6px;height:6px;border-radius:50%;background:#fff;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.topbar-sub{font-size:11px;color:var(--text3)}
.workspace{flex:1;padding:28px 32px}
.panel{display:none}.panel.active{display:block}

/* Cards */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){.two-col{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--purple)40,transparent)}
.card-title{font-size:11px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px;display:flex;align-items:center;gap:6px}
.card-title-dot{width:6px;height:6px;border-radius:50%;background:var(--purple);box-shadow:0 0 8px var(--purple)}

/* Form elements */
textarea{width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:12px 14px;font-size:13px;font-family:inherit;color:var(--text);resize:none;min-height:100px;outline:none;line-height:1.6;transition:border-color .15s}
textarea:focus{border-color:var(--purple);box-shadow:var(--neon-purple)}
select{width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:8px 12px;font-size:12px;font-family:inherit;outline:none;cursor:pointer}
select:focus{border-color:var(--purple)}
.ctrl-row{display:flex;gap:12px;margin-top:12px}
.ctrl-group{flex:1}
.ctrl-label{font-size:11px;color:var(--text3);margin-bottom:5px}
.slider-wrap{display:flex;align-items:center;gap:10px;margin-top:10px}
.slider-name{font-size:11px;color:var(--text3);width:90px;flex-shrink:0}
input[type=range]{flex:1;-webkit-appearance:none;height:4px;border-radius:2px;background:var(--bg3);outline:none;cursor:pointer}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:var(--purple);box-shadow:0 0 8px var(--purple);cursor:pointer}
.slider-val{font-size:11px;color:var(--purple);min-width:32px;text-align:right;font-weight:600}

/* Button */
.gen-btn{width:100%;margin-top:18px;padding:11px;border:none;border-radius:10px;background:linear-gradient(135deg,var(--purple2),var(--pink));color:#fff;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;position:relative;overflow:hidden;transition:opacity .15s,transform .1s}
.gen-btn:hover{opacity:.9}
.gen-btn:active{transform:scale(.98)}
.gen-btn:disabled{opacity:.5;cursor:wait}
.gen-btn::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,transparent,#ffffff18,transparent);transform:translateX(-100%);transition:transform .4s}
.gen-btn:hover::after{transform:translateX(100%)}

/* Status */
.status{font-size:12px;padding:8px 12px;border-radius:8px;margin-top:10px;display:none;align-items:center;gap:6px}
.status.loading{background:#a855f715;border:1px solid #a855f730;color:var(--purple);display:flex}
.status.error{background:#ef444415;border:1px solid #ef444430;color:#f87171;display:block}
.status.success{background:#10b98115;border:1px solid #10b98130;color:var(--green);display:block}
.spin{width:10px;height:10px;border:2px solid var(--purple);border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite;flex-shrink:0}
@keyframes spin{to{transform:rotate(360deg)}}

/* Output */
.output-box{min-height:160px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:14px;font-size:13px;line-height:1.8;color:var(--text2);white-space:pre-wrap;word-break:break-word;margin-top:0}
.output-placeholder{color:var(--text3);font-style:italic}
.meta-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:10px;padding:3px 8px;border-radius:99px;background:var(--card2);border:1px solid var(--border);color:var(--text3)}
.chip.purple{background:#a855f715;border-color:#a855f730;color:var(--purple)}

/* Image output */
.img-box{min-height:180px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--text3);position:relative;overflow:hidden}
.img-box::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,var(--purple)05,var(--pink)05);pointer-events:none}
img.result{max-width:100%;border-radius:10px;display:none;border:1px solid var(--border)}

/* Stats */
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center}
.stat-num{font-size:28px;font-weight:700;background:linear-gradient(90deg,var(--purple),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.stat-lbl{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;margin-top:2px}

/* History */
.hist-item{padding:14px 0;border-bottom:1px solid var(--border)}
.hist-item:last-child{border:none}
.hist-badge{display:inline-flex;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600;margin-bottom:5px}
.hist-badge.text{background:#a855f720;color:var(--purple);border:1px solid #a855f740}
.hist-badge.image{background:#06b6d420;color:var(--cyan);border:1px solid #06b6d440}
.hist-prompt{font-size:12px;color:var(--text2);line-height:1.5}
.hist-ts{font-size:10px;color:var(--text3);margin-top:3px}
.refresh-btn{font-size:12px;padding:6px 14px;border:1px solid var(--border2);border-radius:8px;background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;transition:all .15s}
.refresh-btn:hover{border-color:var(--purple);color:var(--purple)}
</style>
</head>
<body>
<div class="shell">
  <div class="sidebar">
    <div class="logo-area">
      <div class="logo-name">AICIG Studio</div>
      <div class="logo-sub">AI Content &amp; Image Generator</div>
    </div>

    <div class="nav-section">Generate</div>
    <div class="nav-item active" onclick="switchTab('text',this)">
      <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
        <rect x="2" y="3" width="12" height="1.5" rx=".75" fill="currentColor"/>
        <rect x="2" y="7" width="9" height="1.5" rx=".75" fill="currentColor"/>
        <rect x="2" y="11" width="11" height="1.5" rx=".75" fill="currentColor"/>
      </svg>
      Text generation
    </div>
    <div class="nav-item" onclick="switchTab('image',this)">
      <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
        <rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.2"/>
        <circle cx="5.5" cy="5.5" r="1.2" fill="currentColor"/>
        <path d="M2 11l3.5-3.5 2.5 2 2.5-3 3 4" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" fill="none"/>
      </svg>
      Image generation
    </div>
    <div class="nav-item" onclick="switchTab('both',this)">
      <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
        <rect x="1.5" y="3" width="5.5" height="10" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
        <rect x="9" y="3" width="5.5" height="10" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
      </svg>
      Generate both
    </div>

    <div class="nav-section">Analytics</div>
    <div class="nav-item" onclick="switchTab('history',this)">
      <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.2"/>
        <path d="M8 5v3.5l2 1.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
      </svg>
      History &amp; analytics
    </div>

    <div class="sidebar-footer">
      <div class="theme-toggle">
        <div class="toggle-track" onclick="toggleTheme()">
          <div class="toggle-thumb"></div>
        </div>
        <span class="toggle-label" id="theme-label">Dark mode</span>
      </div>
      Shefat Mazibar · W1967304<br>
      University of Westminster<br>
      Supervisor: Jeffrey Ferguson
    </div>
  </div>

  <div class="main">
    <div class="topbar">
      <div class="topbar-left">
        <div>
          <div class="topbar-title" id="topbar-title">Text generation</div>
          <div class="topbar-sub">Powered by Groq · Llama 3.1 · Pollinations.ai</div>
        </div>
      </div>
      <div class="topbar-badge"><span class="live-dot"></span>Live</div>
    </div>

    <div class="workspace">

      <!-- TEXT TAB -->
      <div class="panel active" id="panel-text">
        <div class="two-col">
          <div class="card">
            <div class="card-title"><span class="card-title-dot"></span>Prompt &amp; settings</div>
            <textarea id="t-prompt" placeholder="Write a detailed blog post about the future of artificial intelligence in healthcare..." rows="5"></textarea>
            <div class="ctrl-row">
              <div class="ctrl-group">
                <div class="ctrl-label">Model</div>
                <select id="t-model">
                  <option value="qwen-7b">Qwen 2.5 7B</option>
                  <option value="llama-8b">Llama 3.1 8B</option>
                </select>
              </div>
              <div class="ctrl-group">
                <div class="ctrl-label">Profile</div>
                <select id="t-profile">
                  <option value="balanced">Balanced</option>
                  <option value="creative">Creative</option>
                  <option value="precise">Precise</option>
                  <option value="fast">Fast</option>
                </select>
              </div>
            </div>
            <div class="slider-wrap">
              <span class="slider-name">Max tokens</span>
              <input type="range" min="50" max="500" value="300" step="10" id="t-tokens"
                oninput="document.getElementById('t-tok-v').textContent=this.value">
              <span class="slider-val" id="t-tok-v">300</span>
            </div>
            <div class="slider-wrap">
              <span class="slider-name">Temperature</span>
              <input type="range" min="1" max="20" value="7" step="1" id="t-temp"
                oninput="document.getElementById('t-tmp-v').textContent=(this.value/10).toFixed(1)">
              <span class="slider-val" id="t-tmp-v">0.7</span>
            </div>
            <button class="gen-btn" id="t-btn" onclick="generateText()">Generate text</button>
            <div class="status" id="t-status"></div>
          </div>
          <div class="card">
            <div class="card-title"><span class="card-title-dot" style="background:var(--cyan);box-shadow:0 0 8px var(--cyan)"></span>Output</div>
            <div class="output-box" id="t-output"><span class="output-placeholder">Your generated content will appear here after clicking Generate text...</span></div>
            <div class="meta-row" id="t-meta" style="display:none">
              <span class="chip purple" id="t-bleu"></span>
              <span class="chip" id="t-time"></span>
              <span class="chip" id="t-model-chip"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- IMAGE TAB -->
      <div class="panel" id="panel-image">
        <div class="two-col">
          <div class="card">
            <div class="card-title"><span class="card-title-dot" style="background:var(--pink);box-shadow:0 0 8px var(--pink)"></span>Prompt &amp; settings</div>
            <textarea id="i-prompt" placeholder="A neon-lit cyberpunk city at night, rain reflections on the street, flying vehicles, ultra detailed..." rows="5"></textarea>
            <div class="slider-wrap">
              <span class="slider-name">Width</span>
              <input type="range" min="256" max="512" value="384" step="64" id="i-w"
                oninput="document.getElementById('i-w-v').textContent=this.value+'px'">
              <span class="slider-val" id="i-w-v">384px</span>
            </div>
            <div class="slider-wrap">
              <span class="slider-name">Height</span>
              <input type="range" min="256" max="512" value="384" step="64" id="i-h"
                oninput="document.getElementById('i-h-v').textContent=this.value+'px'">
              <span class="slider-val" id="i-h-v">384px</span>
            </div>
            <div class="slider-wrap">
              <span class="slider-name">Steps</span>
              <input type="range" min="10" max="25" value="15" step="5" id="i-steps"
                oninput="document.getElementById('i-s-v').textContent=this.value">
              <span class="slider-val" id="i-s-v">15</span>
            </div>
            <button class="gen-btn" id="i-btn" onclick="generateImage()" style="background:linear-gradient(135deg,#7c3aed,#06b6d4)">Generate image</button>
            <div class="status" id="i-status"></div>
          </div>
          <div class="card">
            <div class="card-title"><span class="card-title-dot" style="background:var(--pink);box-shadow:0 0 8px var(--pink)"></span>Output</div>
            <div class="img-box" id="i-placeholder">Image will render here</div>
            <img class="result" id="i-img" alt="Generated image">
            <div class="meta-row" id="i-meta" style="display:none">
              <span class="chip purple" id="i-time"></span>
              <span class="chip">Pollinations.ai</span>
            </div>
          </div>
        </div>
      </div>

      <!-- BOTH TAB -->
      <div class="panel" id="panel-both">
        <div class="two-col">
          <div class="card">
            <div class="card-title"><span class="card-title-dot" style="background:var(--cyan);box-shadow:0 0 8px var(--cyan)"></span>Prompt &amp; settings</div>
            <textarea id="b-prompt" placeholder="A futuristic Mars colony in 2150, domed habitats glowing under a red sky..." rows="5"></textarea>
            <div class="ctrl-row">
              <div class="ctrl-group">
                <div class="ctrl-label">Text model</div>
                <select id="b-model">
                  <option value="qwen-7b">Qwen 2.5 7B</option>
                  <option value="llama-8b">Llama 3.1 8B</option>
                </select>
              </div>
              <div class="ctrl-group">
                <div class="ctrl-label">Profile</div>
                <select id="b-profile">
                  <option value="balanced">Balanced</option>
                  <option value="creative">Creative</option>
                  <option value="precise">Precise</option>
                  <option value="fast">Fast</option>
                </select>
              </div>
            </div>
            <button class="gen-btn" id="b-btn" onclick="generateBoth()" style="background:linear-gradient(135deg,#06b6d4,#a855f7,#ec4899)">Generate both</button>
            <div class="status" id="b-status"></div>
          </div>
          <div class="card">
            <div class="card-title"><span class="card-title-dot"></span>Text output</div>
            <div class="output-box" id="b-text"><span class="output-placeholder">Text output will appear here...</span></div>
            <div class="card-title" style="margin-top:16px"><span class="card-title-dot" style="background:var(--pink);box-shadow:0 0 8px var(--pink)"></span>Image output</div>
            <div class="img-box" id="b-placeholder">Image will render here</div>
            <img class="result" id="b-img" alt="Generated image">
          </div>
        </div>
      </div>

      <!-- HISTORY TAB -->
      <div class="panel" id="panel-history">
        <div class="stat-grid">
          <div class="stat-card">
            <div class="stat-num" id="s-total">0</div>
            <div class="stat-lbl">Total generations</div>
          </div>
          <div class="stat-card">
            <div class="stat-num" id="s-text">0</div>
            <div class="stat-lbl">Text generations</div>
          </div>
          <div class="stat-card">
            <div class="stat-num" id="s-img">0</div>
            <div class="stat-lbl">Image generations</div>
          </div>
        </div>
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
            <div class="card-title" style="margin:0"><span class="card-title-dot"></span>Recent activity</div>
            <button class="refresh-btn" onclick="loadHistory()">Refresh</button>
          </div>
          <div id="h-list"><div style="font-size:13px;color:var(--text3)">Click refresh to load history.</div></div>
        </div>
      </div>

    </div>
  </div>
</div>

<script>
const tabTitles={text:'Text generation',image:'Image generation',both:'Generate both',history:'History & analytics'};

function switchTab(name,el){
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('panel-'+name).classList.add('active');
  document.getElementById('topbar-title').textContent=tabTitles[name];
  if(name==='history')loadHistory();
}

function toggleTheme(){
  const html=document.documentElement;
  const isDark=html.getAttribute('data-theme')==='dark';
  html.setAttribute('data-theme',isDark?'light':'dark');
  document.getElementById('theme-label').textContent=isDark?'Light mode':'Dark mode';
}

function setStatus(id,msg,type){
  const el=document.getElementById(id);
  if(!msg){el.style.display='none';return;}
  el.className='status '+type;
  el.innerHTML=type==='loading'?'<span class="spin"></span>'+msg:msg;
}

async function generateText(){
  const prompt=document.getElementById('t-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('t-btn');
  btn.disabled=true;btn.textContent='Generating...';
  setStatus('t-status','Sending to Groq · Llama 3.1 8B...','loading');
  document.getElementById('t-output').innerHTML='<span class="output-placeholder">Generating...</span>';
  document.getElementById('t-meta').style.display='none';
  try{
    const resp=await fetch('/generate_text',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt,
        model_key:document.getElementById('t-model').value,
        profile:document.getElementById('t-profile').value,
        max_tokens:parseInt(document.getElementById('t-tokens').value),
        temperature:parseFloat(document.getElementById('t-temp').value)/10})});
    const data=await resp.json();
    if(data.error){
      document.getElementById('t-output').innerHTML='<span style="color:#f87171">'+data.error+'</span>';
      setStatus('t-status',data.error,'error');
    }else{
      document.getElementById('t-output').textContent=data.text;
      setStatus('t-status','Generated successfully','success');
      if(data.meta){
        const p=data.meta.split('|');
        document.getElementById('t-bleu').textContent=(p[0]||'').trim();
        document.getElementById('t-time').textContent=(p[1]||'').trim();
        document.getElementById('t-model-chip').textContent=(p[2]||'').trim();
        document.getElementById('t-meta').style.display='flex';
      }
    }
  }catch(e){setStatus('t-status','Network error: '+e.message,'error');}
  btn.disabled=false;btn.textContent='Generate text';
}

async function generateImage(){
  const prompt=document.getElementById('i-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('i-btn');
  btn.disabled=true;btn.textContent='Generating...';
  setStatus('i-status','Calling Pollinations.ai...','loading');
  document.getElementById('i-img').style.display='none';
  document.getElementById('i-placeholder').style.display='flex';
  document.getElementById('i-meta').style.display='none';
  try{
    const resp=await fetch('/generate_image',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt,
        width:parseInt(document.getElementById('i-w').value),
        height:parseInt(document.getElementById('i-h').value),
        steps:parseInt(document.getElementById('i-steps').value)})});
    const data=await resp.json();
    if(data.image_b64){
      const img=document.getElementById('i-img');
      img.src='data:image/png;base64,'+data.image_b64;
      img.style.display='block';
      document.getElementById('i-placeholder').style.display='none';
      document.getElementById('i-time').textContent=data.meta||'';
      document.getElementById('i-meta').style.display='flex';
      setStatus('i-status','Image generated successfully','success');
    }else{
      setStatus('i-status',data.error||'Unknown error','error');
    }
  }catch(e){setStatus('i-status','Network error: '+e.message,'error');}
  btn.disabled=false;btn.style.background='linear-gradient(135deg,#7c3aed,#06b6d4)';
  btn.textContent='Generate image';
}

async function generateBoth(){
  const prompt=document.getElementById('b-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('b-btn');
  btn.disabled=true;btn.textContent='Generating...';
  setStatus('b-status','Generating text and image in parallel...','loading');
  document.getElementById('b-text').innerHTML='<span class="output-placeholder">Generating...</span>';
  document.getElementById('b-img').style.display='none';
  document.getElementById('b-placeholder').style.display='flex';
  try{
    const[tr,ir]=await Promise.all([
      fetch('/generate_text',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({prompt,model_key:document.getElementById('b-model').value,
          profile:document.getElementById('b-profile').value,max_tokens:300,temperature:0.7})}),
      fetch('/generate_image',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({prompt,width:384,height:384,steps:15})})
    ]);
    const td=await tr.json();const id=await ir.json();
    document.getElementById('b-text').textContent=td.text||('Error: '+td.error);
    if(id.image_b64){
      const img=document.getElementById('b-img');
      img.src='data:image/png;base64,'+id.image_b64;
      img.style.display='block';
      document.getElementById('b-placeholder').style.display='none';
    }else{
      document.getElementById('b-placeholder').textContent='Image error: '+(id.error||'Unknown');
    }
    setStatus('b-status','Done! Both generated successfully','success');
  }catch(e){setStatus('b-status','Error: '+e.message,'error');}
  btn.disabled=false;btn.textContent='Generate both';
}

async function loadHistory(){
  try{
    const resp=await fetch('/history');
    const data=await resp.json();
    const entries=data.entries||[];
    document.getElementById('s-total').textContent=entries.length;
    document.getElementById('s-text').textContent=entries.filter(e=>e.type==='text').length;
    document.getElementById('s-img').textContent=entries.filter(e=>e.type==='image').length;
    const list=document.getElementById('h-list');
    if(!entries.length){
      list.innerHTML='<div style="font-size:13px;color:var(--text3)">No history yet. Generate some content to see it here.</div>';
      return;
    }
    list.innerHTML=entries.map(e=>`
      <div class="hist-item">
        <span class="hist-badge ${e.type}">${e.type.toUpperCase()}</span>
        <div class="hist-prompt">${e.prompt.slice(0,150)}${e.prompt.length>150?'...':''}</div>
        <div class="hist-ts">${e.timestamp.slice(0,19).replace('T',' ')} &nbsp;·&nbsp; ${e.model}</div>
      </div>`).join('');
  }catch(e){
    document.getElementById('h-list').innerHTML='<div style="color:#f87171;font-size:13px">Error loading history</div>';
  }
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
