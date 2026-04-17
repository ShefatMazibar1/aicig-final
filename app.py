import os
import io
import base64
import time
import requests
from flask import Flask, request, jsonify, session, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aicig-secret-2024-fyp")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except:
        pass

try:
    from model_manager import ModelManager
    manager = ModelManager()
    print("ModelManager loaded")
except Exception as e:
    manager = None

try:
    from text_engine import TextEngine
    text_engine = TextEngine()
    print("TextEngine loaded")
except Exception as e:
    text_engine = None

try:
    from evaluation import Evaluator
    evaluator = Evaluator()
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

print("App ready")

LANDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AICIG Studio — Generate Content & Images with AI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#07070e;--bg2:#0d0d1a;--bg3:#13131f;
  --purple:#a855f7;--purple2:#7c3aed;--pink:#ec4899;--cyan:#06b6d4;--green:#10b981;
  --text:#ffffff;--text2:#9ca3af;--text3:#4b5563;
  --border:#ffffff0f;--border2:#ffffff1a;
}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;line-height:1.6}
canvas#bg{position:fixed;inset:0;z-index:0;pointer-events:none}

/* NAV */
nav{position:fixed;top:0;left:0;right:0;z-index:50;padding:0 48px;height:64px;display:flex;align-items:center;justify-content:space-between;background:#07070eee;backdrop-filter:blur(16px);border-bottom:1px solid var(--border)}
.logo{font-size:17px;font-weight:700;letter-spacing:-.3px;color:#fff;text-decoration:none;display:flex;align-items:center;gap:8px}
.logo-icon{width:28px;height:28px;border-radius:7px;background:linear-gradient(135deg,var(--purple2),var(--pink));display:flex;align-items:center;justify-content:center;font-size:13px}
.nav-mid{display:flex;gap:28px}
.nav-mid a{font-size:14px;color:var(--text2);text-decoration:none;transition:color .15s}
.nav-mid a:hover{color:#fff}
.nav-right{display:flex;align-items:center;gap:10px}
.n-login{font-size:13px;color:var(--text2);text-decoration:none;padding:7px 16px;transition:color .15s}
.n-login:hover{color:#fff}
.n-signup{font-size:13px;font-weight:600;color:#fff;text-decoration:none;padding:8px 18px;background:linear-gradient(135deg,var(--purple2),var(--pink));border-radius:8px;transition:opacity .15s}
.n-signup:hover{opacity:.85}

/* HERO */
.hero{position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:100px 24px 60px}
.hero-tag{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;border:1px solid #a855f730;border-radius:99px;font-size:12px;color:#c084fc;background:#a855f70a;margin-bottom:32px;animation:up .7s ease both}
.tag-pulse{width:6px;height:6px;border-radius:50%;background:#a855f7;box-shadow:0 0 8px #a855f7;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.75)}}
@keyframes up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.hero h1{font-size:clamp(40px,7vw,82px);font-weight:800;letter-spacing:-.04em;line-height:1.05;margin-bottom:24px;animation:up .7s .08s ease both}
.hero h1 em{font-style:normal;background:linear-gradient(90deg,#c084fc,#f472b6,#67e8f9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;background-size:200%;animation:gradmove 5s infinite linear}
@keyframes gradmove{0%{background-position:0%}100%{background-position:200%}}
.hero-sub{font-size:18px;color:var(--text2);max-width:560px;line-height:1.65;margin-bottom:40px;animation:up .7s .16s ease both}
.hero-ctas{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;animation:up .7s .24s ease both}
.cta-main{display:inline-flex;align-items:center;gap:8px;padding:14px 28px;background:linear-gradient(135deg,var(--purple2),var(--pink));color:#fff;font-size:15px;font-weight:700;border-radius:10px;text-decoration:none;transition:transform .15s,box-shadow .15s}
.cta-main:hover{transform:translateY(-2px);box-shadow:0 10px 40px #7c3aed35}
.cta-sec{display:inline-flex;align-items:center;gap:6px;padding:14px 28px;border:1px solid var(--border2);color:var(--text2);font-size:15px;font-weight:500;border-radius:10px;text-decoration:none;transition:all .15s}
.cta-sec:hover{border-color:#a855f750;color:#fff}
.hero-note{margin-top:20px;font-size:12px;color:var(--text3);animation:up .7s .32s ease both}

/* MARQUEE */
.marquee-wrap{position:relative;z-index:1;padding:32px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);overflow:hidden;background:#ffffff03}
.marquee-track{display:flex;gap:48px;animation:marquee 20s linear infinite;white-space:nowrap}
.marquee-item{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text3);flex-shrink:0}
.marquee-dot{width:5px;height:5px;border-radius:50%;background:var(--purple)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* LIVE DEMO */
.demo-section{position:relative;z-index:1;padding:100px 48px;max-width:1100px;margin:0 auto}
.section-eyebrow{font-size:11px;font-weight:700;color:#a855f7;text-transform:uppercase;letter-spacing:.14em;margin-bottom:14px}
.section-h{font-size:clamp(28px,4vw,46px);font-weight:800;letter-spacing:-.03em;line-height:1.15;margin-bottom:14px}
.section-p{font-size:16px;color:var(--text2);max-width:480px;line-height:1.7;margin-bottom:40px}
.demo-card{background:var(--bg2);border:1px solid var(--border2);border-radius:20px;overflow:hidden;position:relative}
.demo-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#a855f780,#ec489980,transparent)}
.demo-grid{display:grid;grid-template-columns:1fr 1fr;gap:0}
@media(max-width:700px){.demo-grid{grid-template-columns:1fr}}
.demo-left{padding:28px;border-right:1px solid var(--border)}
.demo-right{padding:28px;display:flex;flex-direction:column}
.demo-field-label{font-size:11px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
.demo-textarea{width:100%;background:var(--bg3);border:1px solid var(--border2);border-radius:10px;padding:12px;font-size:13px;font-family:inherit;color:#fff;resize:none;min-height:80px;outline:none;line-height:1.5;transition:border-color .15s}
.demo-textarea:focus{border-color:#a855f7;box-shadow:0 0 0 3px #a855f712}
.demo-textarea::placeholder{color:var(--text3)}
.chip-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.chip{font-size:11px;padding:4px 11px;border:1px solid var(--border2);border-radius:99px;color:var(--text3);cursor:pointer;transition:all .15s}
.chip:hover{border-color:#a855f7;color:#c084fc}
.demo-gen-btn{width:100%;padding:12px;margin-top:16px;border:none;border-radius:10px;background:linear-gradient(135deg,var(--purple2),var(--pink));color:#fff;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;transition:opacity .15s,transform .1s}
.demo-gen-btn:hover{opacity:.88;transform:translateY(-1px)}
.demo-gen-btn:disabled{opacity:.4;cursor:wait;transform:none}
.demo-img-wrap{flex:1;background:var(--bg3);border:1px solid var(--border);border-radius:12px;min-height:200px;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.demo-img-wrap img{width:100%;height:100%;object-fit:cover;border-radius:12px;display:none}
.demo-empty{display:flex;flex-direction:column;align-items:center;gap:8px;color:var(--text3)}
.demo-empty svg{opacity:.25}
.demo-empty p{font-size:12px}
.demo-prog{height:3px;background:var(--border);border-radius:2px;overflow:hidden;margin-top:14px;display:none}
.demo-prog-fill{height:100%;background:linear-gradient(90deg,var(--purple2),var(--pink));width:0%;transition:width .5s ease}
.demo-stat-row{display:flex;align-items:center;gap:6px;margin-top:12px;font-size:12px;color:var(--text3);display:none}
.demo-stat-row.show{display:flex}
.spin{width:10px;height:10px;border:1.5px solid var(--purple);border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* STATS */
.stats-section{position:relative;z-index:1;background:#ffffff04;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:72px 48px}
.stats-grid{max-width:900px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);gap:32px;text-align:center}
@media(max-width:700px){.stats-grid{grid-template-columns:repeat(2,1fr)}}
.stat-n{font-size:48px;font-weight:800;letter-spacing:-.04em;background:linear-gradient(135deg,#c084fc,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1}
.stat-l{font-size:13px;color:var(--text3);margin-top:6px}

/* FEATURES */
.features-section{position:relative;z-index:1;padding:100px 48px;max-width:1100px;margin:0 auto}
.feat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:900px){.feat-grid{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.feat-grid{grid-template-columns:1fr}}
.feat-card{background:var(--bg2);border:1px solid var(--border);border-radius:16px;padding:24px;transition:all .2s;cursor:default}
.feat-card:hover{border-color:#a855f730;transform:translateY(-2px)}
.feat-icon{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:14px}
.feat-title{font-size:15px;font-weight:700;margin-bottom:8px;letter-spacing:-.02em}
.feat-desc{font-size:13px;color:var(--text2);line-height:1.65}

/* STEPS */
.steps-section{position:relative;z-index:1;padding:100px 48px;max-width:1100px;margin:0 auto}
.steps-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-top:48px}
@media(max-width:700px){.steps-grid{grid-template-columns:1fr 1fr}}
.step-card{position:relative}
.step-num{font-size:13px;font-weight:700;color:#a855f7;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.step-num::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,#a855f730,transparent)}
.step-title{font-size:15px;font-weight:700;margin-bottom:6px;letter-spacing:-.02em}
.step-desc{font-size:13px;color:var(--text2);line-height:1.6}

/* CTA BANNER */
.cta-section{position:relative;z-index:1;margin:0 48px 80px;border-radius:20px;background:linear-gradient(135deg,#1a0a2e,#1a0a1e,#0a1a1e);border:1px solid #a855f720;padding:72px 48px;text-align:center;overflow:hidden}
.cta-section::before{content:'';position:absolute;top:-80px;left:50%;transform:translateX(-50%);width:400px;height:200px;background:radial-gradient(ellipse,#7c3aed20,transparent 70%);pointer-events:none}
.cta-section h2{font-size:clamp(28px,4vw,46px);font-weight:800;letter-spacing:-.03em;margin-bottom:14px}
.cta-section p{font-size:16px;color:var(--text2);margin-bottom:32px}

/* FOOTER */
footer{position:relative;z-index:1;border-top:1px solid var(--border);padding:40px 48px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}
.foot-logo{font-size:15px;font-weight:700;color:#fff;display:flex;align-items:center;gap:7px}
.foot-icon{width:22px;height:22px;border-radius:6px;background:linear-gradient(135deg,var(--purple2),var(--pink));display:flex;align-items:center;justify-content:center;font-size:10px}
.foot-text{font-size:12px;color:var(--text3)}
</style>
</head>
<body>
<canvas id="bg"></canvas>

<nav>
  <a href="/" class="logo">
    <div class="logo-icon">🤖</div>
    AICIG Studio
  </a>
  <div class="nav-mid">
    <a href="#demo">Live demo</a>
    <a href="#features">Features</a>
    <a href="#how">How it works</a>
  </div>
  <div class="nav-right">
    <a href="/login" class="n-login">Sign in</a>
    <a href="/signup" class="n-signup">Get started free →</a>
  </div>
</nav>

<section class="hero">
  <div class="hero-tag"><span class="tag-pulse"></span>Final Year Project · University of Westminster</div>
  <h1>Stop Searching.<br>Start <em>Generating.</em></h1>
  <p class="hero-sub">AICIG Studio turns your prompts into high-quality articles, blog posts, and AI images — in seconds. Completely free. No credit card needed.</p>
  <div class="hero-ctas">
    <a href="/signup" class="cta-main">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v12M1 7h12" stroke="white" stroke-width="2.5" stroke-linecap="round"/></svg>
      Start generating free
    </a>
    <a href="#demo" class="cta-sec">
      See it live
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </a>
  </div>
  <div class="hero-note">No credit card &nbsp;·&nbsp; Free forever &nbsp;·&nbsp; Open source</div>
</section>

<div class="marquee-wrap">
  <div class="marquee-track" id="marquee">
    <div class="marquee-item"><span class="marquee-dot"></span>Text generation</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Image synthesis</div>
    <div class="marquee-item"><span class="marquee-dot"></span>BLEU evaluation</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Llama 3.1 · Qwen 2.5</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Pollinations.ai</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Generation history</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Dark &amp; light mode</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Real-time analytics</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Text generation</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Image synthesis</div>
    <div class="marquee-item"><span class="marquee-dot"></span>BLEU evaluation</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Llama 3.1 · Qwen 2.5</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Pollinations.ai</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Generation history</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Dark &amp; light mode</div>
    <div class="marquee-item"><span class="marquee-dot"></span>Real-time analytics</div>
  </div>
</div>

<section class="stats-section">
  <div class="stats-grid">
    <div><div class="stat-n" id="sn1">0</div><div class="stat-l">AI models available</div></div>
    <div><div class="stat-n" id="sn2">0%</div><div class="stat-l">Free to use, forever</div></div>
    <div><div class="stat-n" id="sn3">0s</div><div class="stat-l">Average text generation</div></div>
    <div><div class="stat-n" id="sn4">∞</div><div class="stat-l">Generations allowed</div></div>
  </div>
</section>

<section id="demo" class="demo-section">
  <div class="section-eyebrow">Live demo</div>
  <div class="section-h">Try it now.<br>No account required.</div>
  <div class="section-p">Type a prompt, click generate, and watch AICIG create a real AI image in seconds. Sign up for text generation and history.</div>
  <div class="demo-card">
    <div class="demo-grid">
      <div class="demo-left">
        <div class="demo-field-label">Your prompt</div>
        <textarea class="demo-textarea" id="dp" placeholder="A cyberpunk city at night with neon lights..." rows="3"></textarea>
        <div class="demo-field-label" style="margin-top:16px">Quick examples</div>
        <div class="chip-row">
          <span class="chip" onclick="setP('A neon cyberpunk city at night')">Cyberpunk city</span>
          <span class="chip" onclick="setP('A magical glowing forest at dusk')">Magic forest</span>
          <span class="chip" onclick="setP('A futuristic space station orbiting Earth')">Space station</span>
          <span class="chip" onclick="setP('An AI robot brain made of crystal and light')">AI robot brain</span>
          <span class="chip" onclick="setP('An underwater bioluminescent kingdom')">Ocean kingdom</span>
          <span class="chip" onclick="setP('A dragon made of fire and stars')">Fire dragon</span>
        </div>
        <button class="demo-gen-btn" id="dgb" onclick="demoGen()">Generate image →</button>
        <div class="demo-prog" id="dprog"><div class="demo-prog-fill" id="dpf"></div></div>
        <div class="demo-stat-row" id="dstat"></div>
      </div>
      <div class="demo-right">
        <div class="demo-field-label">Generated image</div>
        <div class="demo-img-wrap" id="diw">
          <div class="demo-empty" id="dem">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="6" y="6" width="36" height="36" rx="7" stroke="currentColor" stroke-width="1.5"/><circle cx="16" cy="17" r="3.5" fill="currentColor" opacity=".4"/><path d="M6 32l11-11 8 8 7-8 16 11" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
            <p>Image renders here</p>
          </div>
          <img id="dimg" alt="Generated">
        </div>
        <div style="margin-top:12px;font-size:12px;color:var(--text3)">
          Want text generation too? <a href="/signup" style="color:#a855f7;text-decoration:none">Create a free account →</a>
        </div>
      </div>
    </div>
  </div>
</section>

<section id="features" class="features-section">
  <div class="section-eyebrow">Features</div>
  <div class="section-h">Everything you need<br>to create AI content</div>
  <div class="section-p">A complete platform for generating, evaluating, and tracking AI content — built for research and everyday use.</div>
  <div class="feat-grid">
    <div class="feat-card"><div class="feat-icon" style="background:#a855f715;border:1px solid #a855f730">✍️</div><div class="feat-title">Text generation</div><div class="feat-desc">Generate articles, blogs, and summaries with Llama 3.1 via Groq — sub-second response times on free tier.</div></div>
    <div class="feat-card"><div class="feat-icon" style="background:#ec489915;border:1px solid #ec489930">🖼️</div><div class="feat-title">Image generation</div><div class="feat-desc">Create stunning AI images from any prompt using Pollinations.ai — completely free, unlimited, no API key needed.</div></div>
    <div class="feat-card"><div class="feat-icon" style="background:#06b6d415;border:1px solid #06b6d430">⚡</div><div class="feat-title">Generate both</div><div class="feat-desc">Run text and image generation simultaneously from one prompt — perfect for content creation at speed.</div></div>
    <div class="feat-card"><div class="feat-icon" style="background:#10b98115;border:1px solid #10b98130">📊</div><div class="feat-title">BLEU scoring</div><div class="feat-desc">Every text output is automatically evaluated with BLEU-4 metrics so you can measure and improve quality.</div></div>
    <div class="feat-card"><div class="feat-icon" style="background:#f59e0b15;border:1px solid #f59e0b30">🎛️</div><div class="feat-title">Fine-grained control</div><div class="feat-desc">Tune temperature, max tokens, top-p, and generation profiles — or pick balanced, creative, precise, or fast.</div></div>
    <div class="feat-card"><div class="feat-icon" style="background:#3b82f615;border:1px solid #3b82f630">📜</div><div class="feat-title">History & analytics</div><div class="feat-desc">Every generation is logged with timestamps, metrics, and model info — track your usage and review past outputs.</div></div>
  </div>
</section>

<section id="how" style="background:#ffffff03;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:100px 0;position:relative;z-index:1">
  <div class="steps-section" style="padding:0 48px">
    <div class="section-eyebrow">How it works</div>
    <div class="section-h">From zero to<br>generating in minutes</div>
    <div class="steps-grid">
      <div class="step-card">
        <div class="step-num">01 <span style="color:var(--text3);font-weight:400;font-size:11px">Account</span></div>
        <div class="step-title">Create your account</div>
        <div class="step-desc">Sign up in under 30 seconds — username, email, password. No credit card, no subscription, ever.</div>
      </div>
      <div class="step-card">
        <div class="step-num">02 <span style="color:var(--text3);font-weight:400;font-size:11px">Prompt</span></div>
        <div class="step-title">Write your prompt</div>
        <div class="step-desc">Describe what you want — a blog post about AI, an image of a space station, or both at once.</div>
      </div>
      <div class="step-card">
        <div class="step-num">03 <span style="color:var(--text3);font-weight:400;font-size:11px">Configure</span></div>
        <div class="step-title">Choose your settings</div>
        <div class="step-desc">Pick a model, profile, and tune the sliders — or just hit generate with the smart defaults.</div>
      </div>
      <div class="step-card">
        <div class="step-num">04 <span style="color:var(--text3);font-weight:400;font-size:11px">Done</span></div>
        <div class="step-title">Generate & review</div>
        <div class="step-desc">Get your content instantly. Everything auto-saves to your personal history with full metrics.</div>
      </div>
    </div>
  </div>
</section>

<section class="cta-section">
  <h2>Ready to start<br>generating?</h2>
  <p>Join AICIG Studio today. Free forever, no credit card needed.</p>
  <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
    <a href="/signup" class="cta-main">Create free account →</a>
    <a href="/login" class="cta-sec" style="border-color:#ffffff20;color:#9ca3af">Sign in</a>
  </div>
</section>

<footer>
  <div class="foot-logo">
    <div class="foot-icon">🤖</div>
    AICIG Studio
  </div>
  <div class="foot-text">Final Year Project · Shefat Mazibar (W1967304) · University of Westminster · Supervisor: Jeffrey Ferguson</div>
</footer>

<script>
/* WEBGL-STYLE CANVAS BACKGROUND */
const c = document.getElementById('bg');
const ctx = c.getContext('2d');
let W, H, pts = [];
function resize(){ W = c.width = innerWidth; H = c.height = innerHeight; }
resize(); window.addEventListener('resize', resize);

class Pt {
  constructor(){
    this.x = Math.random()*W; this.y = Math.random()*H;
    this.vx = (Math.random()-.5)*.25; this.vy = (Math.random()-.5)*.25;
    this.r = Math.random()*1.2+.3;
    this.col = ['#a855f7','#7c3aed','#ec4899','#06b6d4'][Math.floor(Math.random()*4)];
    this.a = Math.random()*.4+.1; this.p = Math.random()*Math.PI*2;
  }
  tick(){
    this.x+=this.vx; this.y+=this.vy; this.p+=.015;
    if(this.x<0||this.x>W) this.vx*=-1;
    if(this.y<0||this.y>H) this.vy*=-1;
  }
  draw(){
    ctx.globalAlpha = this.a*(0.6+0.4*Math.sin(this.p));
    ctx.fillStyle = this.col;
    ctx.beginPath(); ctx.arc(this.x,this.y,this.r,0,Math.PI*2); ctx.fill();
  }
}

for(let i=0;i<100;i++) pts.push(new Pt());

function frame(){
  ctx.clearRect(0,0,W,H);
  for(let i=0;i<pts.length;i++){
    for(let j=i+1;j<pts.length;j++){
      const dx=pts[i].x-pts[j].x, dy=pts[i].y-pts[j].y, d=Math.sqrt(dx*dx+dy*dy);
      if(d<90){ ctx.globalAlpha=(1-d/90)*.06; ctx.strokeStyle='#7c3aed'; ctx.lineWidth=.5; ctx.beginPath(); ctx.moveTo(pts[i].x,pts[i].y); ctx.lineTo(pts[j].x,pts[j].y); ctx.stroke(); }
    }
  }
  pts.forEach(p=>{ p.tick(); p.draw(); });
  ctx.globalAlpha=1;
  requestAnimationFrame(frame);
}
frame();

/* COUNTER ANIMATION */
function countUp(el, target, suffix='', duration=1800){
  const start = performance.now();
  const isStr = typeof target === 'string';
  function step(now){
    const prog = Math.min((now-start)/duration,1);
    const ease = 1-Math.pow(1-prog,3);
    if(isStr){ el.textContent = target; return; }
    el.textContent = Math.round(ease*target) + suffix;
    if(prog<1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
const statsObs = new IntersectionObserver(entries=>{
  if(entries[0].isIntersecting){
    countUp(document.getElementById('sn1'),3,'');
    countUp(document.getElementById('sn2'),100,'%');
    countUp(document.getElementById('sn3'),2,'s');
    document.getElementById('sn4').textContent='∞';
    statsObs.disconnect();
  }
},{threshold:.5});
statsObs.observe(document.querySelector('.stats-section'));

/* SCROLL REVEAL */
const revealObs = new IntersectionObserver(entries=>{
  entries.forEach(e=>{ if(e.isIntersecting){ e.target.style.opacity='1'; e.target.style.transform='translateY(0)'; }});
},{threshold:.1});
document.querySelectorAll('.feat-card,.step-card').forEach(el=>{
  el.style.opacity='0'; el.style.transform='translateY(18px)';
  el.style.transition='opacity .55s ease, transform .55s ease';
  revealObs.observe(el);
});

/* LIVE IMAGE DEMO */
function setP(t){ document.getElementById('dp').value=t; }

async function demoGen(){
  const prompt = document.getElementById('dp').value.trim();
  if(!prompt){ alert('Enter a prompt or pick an example'); return; }
  const btn = document.getElementById('dgb');
  btn.disabled=true; btn.textContent='Generating...';
  document.getElementById('dprog').style.display='block';
  document.getElementById('dstat').className='demo-stat-row show';
  document.getElementById('dstat').innerHTML='<span class="spin"></span> Calling Pollinations.ai — this takes ~5s...';
  document.getElementById('dimg').style.display='none';
  document.getElementById('dem').style.display='flex';
  let prog=0;
  const pi = setInterval(()=>{ prog=Math.min(prog+5,88); document.getElementById('dpf').style.width=prog+'%'; },400);
  try{
    const resp = await fetch('/demo_image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
    const data = await resp.json();
    clearInterval(pi);
    document.getElementById('dpf').style.width='100%';
    if(data.image_b64){
      const img=document.getElementById('dimg');
      img.src='data:image/png;base64,'+data.image_b64;
      img.style.display='block';
      document.getElementById('dem').style.display='none';
      document.getElementById('dstat').innerHTML='✓ Generated in '+data.time+'s — <a href="/signup" style="color:#a855f7;text-decoration:none">Sign up for full access →</a>';
    } else {
      document.getElementById('dstat').textContent='Error: '+(data.error||'Unknown');
    }
  }catch(e){ clearInterval(pi); document.getElementById('dstat').textContent='Error: '+e.message; }
  setTimeout(()=>{ document.getElementById('dprog').style.display='none'; document.getElementById('dpf').style.width='0'; },1200);
  btn.disabled=false; btn.textContent='Generate image →';
}
</script>
</body>
</html>"""


AUTH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — AICIG Studio</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#08080f;color:#f0f0ff;min-height:100vh;display:flex;flex-direction:column}}
nav{{padding:16px 40px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #ffffff15}}
.nav-logo{{font-size:18px;font-weight:700;background:linear-gradient(90deg,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;text-decoration:none}}
.nav-link{{font-size:13px;color:#a0a0c0;text-decoration:none;transition:color .15s}}
.nav-link:hover{{color:#f0f0ff}}
.auth-wrap{{flex:1;display:flex;align-items:center;justify-content:center;padding:40px 20px;position:relative;overflow:hidden}}
.auth-glow{{position:absolute;width:400px;height:400px;border-radius:50%;background:radial-gradient(circle,#7c3aed20,transparent 70%);top:50%;left:50%;transform:translate(-50%,-50%);pointer-events:none}}
.auth-card{{background:#0f0f1a;border:1px solid #ffffff20;border-radius:20px;padding:40px;width:100%;max-width:420px;position:relative;z-index:1}}
.auth-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#a855f780,transparent);border-radius:20px 20px 0 0}}
.auth-icon{{width:52px;height:52px;border-radius:14px;background:linear-gradient(135deg,#7c3aed,#ec4899);display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:20px}}
.auth-title{{font-size:22px;font-weight:700;margin-bottom:6px}}
.auth-sub{{font-size:13px;color:#a0a0c0;margin-bottom:28px;line-height:1.5}}
.form-group{{margin-bottom:16px}}
label{{display:block;font-size:12px;color:#a0a0c0;margin-bottom:6px;font-weight:500}}
input{{width:100%;background:#1a1a2e;border:1px solid #ffffff20;border-radius:10px;padding:12px 14px;font-size:14px;color:#f0f0ff;font-family:inherit;outline:none;transition:border-color .15s}}
input:focus{{border-color:#a855f7;box-shadow:0 0 0 3px #a855f715}}
input::placeholder{{color:#505070}}
.auth-btn{{width:100%;padding:12px;border:none;border-radius:10px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;margin-top:8px;transition:opacity .15s}}
.auth-btn:hover{{opacity:.88}}
.auth-footer{{text-align:center;margin-top:20px;font-size:13px;color:#a0a0c0}}
.auth-footer a{{color:#a855f7;text-decoration:none}}
.auth-footer a:hover{{text-decoration:underline}}
.error-msg{{background:#ef444415;border:1px solid #ef444430;color:#f87171;padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:16px}}
.success-msg{{background:#10b98115;border:1px solid #10b98130;color:#34d399;padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:16px}}
.divider{{display:flex;align-items:center;gap:12px;margin:20px 0;color:#505070;font-size:12px}}
.divider::before,.divider::after{{content:'';flex:1;height:1px;background:#ffffff15}}
.features-mini{{display:flex;flex-direction:column;gap:8px;margin-top:20px;padding-top:20px;border-top:1px solid #ffffff10}}
.feat-item{{display:flex;align-items:center;gap:8px;font-size:12px;color:#a0a0c0}}
.feat-dot{{width:6px;height:6px;border-radius:50%;background:#a855f7;flex-shrink:0}}
</style>
</head>
<body>
<nav>
  <a href="/" class="nav-logo">AICIG Studio</a>
  <a href="{alt_link}" class="nav-link">{alt_text}</a>
</nav>
<div class="auth-wrap">
  <div class="auth-glow"></div>
  <div class="auth-card">
    <div class="auth-icon">{icon}</div>
    <div class="auth-title">{title}</div>
    <div class="auth-sub">{subtitle}</div>
    {message}
    <form method="POST" action="{action}">
      {fields}
      <button type="submit" class="auth-btn">{btn}</button>
    </form>
    <div class="auth-footer">{footer}</div>
    {extras}
  </div>
</div>
</body>
</html>"""

APP_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AICIG Studio</title>
<style>
:root[data-theme="dark"]{
  --bg:#08080f;--bg2:#0f0f1a;--bg3:#1a1a2e;
  --border:#ffffff18;--border2:#ffffff30;
  --text:#f0f0ff;--text2:#a0a0c0;--text3:#505070;
  --purple:#a855f7;--purple2:#7c3aed;--pink:#ec4899;--cyan:#06b6d4;--green:#10b981;
  --card:#ffffff08;--card2:#ffffff14;
}
:root[data-theme="light"]{
  --bg:#f8f7ff;--bg2:#ffffff;--bg3:#ede9fe;
  --border:#7c3aed20;--border2:#7c3aed40;
  --text:#1e1b4b;--text2:#4c1d95;--text3:#7c3aed;
  --purple:#7c3aed;--purple2:#6d28d9;--pink:#db2777;--cyan:#0891b2;--green:#059669;
  --card:#7c3aed08;--card2:#7c3aed14;
}
*{box-sizing:border-box;margin:0;padding:0;transition:background .2s,color .2s,border-color .2s}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.shell{display:grid;grid-template-columns:240px 1fr;min-height:100vh}
.sidebar{background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;position:relative;overflow:hidden}
.sidebar::before{content:'';position:absolute;top:-60px;left:-60px;width:200px;height:200px;background:var(--purple2);opacity:.1;border-radius:50%;filter:blur(50px);pointer-events:none}
.logo-area{padding:24px;border-bottom:1px solid var(--border)}
.logo-name{font-size:18px;font-weight:700;background:linear-gradient(90deg,var(--purple),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.logo-sub{font-size:10px;color:var(--text3);margin-top:3px;letter-spacing:.04em}
.user-chip{display:flex;align-items:center;gap:8px;margin-top:12px;padding:8px 10px;background:var(--card);border-radius:8px;border:1px solid var(--border)}
.user-avatar{width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,var(--purple2),var(--pink));display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;flex-shrink:0}
.user-name{font-size:11px;color:var(--text2);font-weight:500}
.nav-section{font-size:10px;color:var(--text3);padding:16px 24px 6px;letter-spacing:.1em;text-transform:uppercase}
.nav-item{display:flex;align-items:center;gap:12px;padding:10px 24px;cursor:pointer;font-size:13px;color:var(--text2);border-left:2px solid transparent;transition:all .15s}
.nav-item:hover{color:var(--text);background:var(--card)}
.nav-item.active{color:var(--purple);border-left-color:var(--purple);background:var(--card2)}
.nav-item.active svg{filter:drop-shadow(0 0 5px var(--purple))}
.sidebar-footer{margin-top:auto;padding:16px 24px;border-top:1px solid var(--border)}
.theme-toggle{display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer}
.toggle-track{width:36px;height:20px;background:var(--card2);border:1px solid var(--border2);border-radius:10px;position:relative;transition:all .2s}
.toggle-thumb{position:absolute;top:3px;left:3px;width:12px;height:12px;border-radius:50%;background:var(--purple);transition:all .2s;box-shadow:0 0 6px var(--purple)}
[data-theme="light"] .toggle-thumb{left:19px}
.toggle-label{font-size:11px;color:var(--text2)}
.logout-btn{display:flex;align-items:center;gap:8px;padding:8px 0;font-size:12px;color:var(--text3);cursor:pointer;text-decoration:none;transition:color .15s}
.logout-btn:hover{color:var(--pink)}
.sidebar-info{font-size:10px;color:var(--text3);line-height:1.6;margin-top:8px}
.main{display:flex;flex-direction:column}
.topbar{background:var(--bg2);border-bottom:1px solid var(--border);padding:14px 32px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10}
.topbar-title{font-size:14px;font-weight:600}
.topbar-sub{font-size:11px;color:var(--text3);margin-top:2px}
.live-badge{display:flex;align-items:center;gap:5px;font-size:10px;padding:4px 10px;border-radius:99px;background:var(--green);color:#fff;opacity:.9}
.live-dot{width:5px;height:5px;border-radius:50%;background:#fff;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.workspace{flex:1;padding:24px 32px}
.panel{display:none}.panel.active{display:block}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){.two-col{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--purple)50,transparent)}
.card-label{font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;display:flex;align-items:center;gap:6px}
.label-dot{width:5px;height:5px;border-radius:50%;background:var(--purple);box-shadow:0 0 6px var(--purple)}
textarea{width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:11px 13px;font-size:13px;font-family:inherit;color:var(--text);resize:none;min-height:96px;outline:none;line-height:1.6}
textarea:focus{border-color:var(--purple);box-shadow:0 0 0 3px #a855f715}
select{width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:8px 11px;font-size:12px;font-family:inherit;outline:none;cursor:pointer}
.ctrl-row{display:flex;gap:10px;margin-top:12px}
.ctrl-group{flex:1}
.ctrl-label{font-size:11px;color:var(--text3);margin-bottom:5px}
.slider-wrap{display:flex;align-items:center;gap:10px;margin-top:10px}
.slider-name{font-size:11px;color:var(--text3);width:88px;flex-shrink:0}
input[type=range]{flex:1;-webkit-appearance:none;height:3px;border-radius:2px;background:var(--bg3);outline:none;cursor:pointer}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:13px;height:13px;border-radius:50%;background:var(--purple);box-shadow:0 0 6px var(--purple);cursor:pointer}
.slider-val{font-size:11px;color:var(--purple);min-width:30px;text-align:right;font-weight:600}
.gen-btn{width:100%;margin-top:16px;padding:11px;border:none;border-radius:10px;background:linear-gradient(135deg,var(--purple2),var(--pink));color:#fff;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;position:relative;overflow:hidden;transition:opacity .15s,transform .1s}
.gen-btn:hover{opacity:.88;transform:translateY(-1px)}
.gen-btn:active{transform:scale(.98)}
.gen-btn:disabled{opacity:.45;cursor:wait;transform:none}
.status{font-size:12px;padding:8px 12px;border-radius:8px;margin-top:10px;display:none;align-items:center;gap:6px}
.status.loading{background:#a855f712;border:1px solid #a855f730;color:var(--purple);display:flex}
.status.error{background:#ef444412;border:1px solid #ef444430;color:#f87171;display:block}
.status.success{background:#10b98112;border:1px solid #10b98130;color:var(--green);display:block}
.spin{width:10px;height:10px;border:1.5px solid var(--purple);border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite;flex-shrink:0}
@keyframes spin{to{transform:rotate(360deg)}}
.output-box{min-height:150px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:13px;font-size:13px;line-height:1.8;color:var(--text2);white-space:pre-wrap;word-break:break-word}
.output-placeholder{color:var(--text3);font-style:italic}
.meta-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:10px;padding:3px 8px;border-radius:99px;background:var(--card2);border:1px solid var(--border);color:var(--text3)}
.chip.purple{background:#a855f712;border-color:#a855f730;color:var(--purple)}
.img-box{min-height:160px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--text3)}
img.result{max-width:100%;border-radius:10px;display:none;border:1px solid var(--border)}
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center}
.stat-num{font-size:26px;font-weight:700;background:linear-gradient(90deg,var(--purple),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.stat-lbl{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.hist-item{padding:13px 0;border-bottom:1px solid var(--border)}
.hist-item:last-child{border:none}
.hist-badge{display:inline-flex;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600;margin-bottom:5px}
.hist-badge.text{background:#a855f718;color:var(--purple);border:1px solid #a855f730}
.hist-badge.image{background:#06b6d418;color:var(--cyan);border:1px solid #06b6d430}
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
      <div class="user-chip">
        <div class="user-avatar" id="user-avatar">?</div>
        <div class="user-name" id="user-name">Loading...</div>
      </div>
    </div>
    <div class="nav-section">Generate</div>
    <div class="nav-item active" onclick="switchTab('text',this)">
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="1.5" rx=".75" fill="currentColor"/><rect x="2" y="7" width="9" height="1.5" rx=".75" fill="currentColor"/><rect x="2" y="11" width="11" height="1.5" rx=".75" fill="currentColor"/></svg>
      Text generation
    </div>
    <div class="nav-item" onclick="switchTab('image',this)">
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.2"/><circle cx="5.5" cy="5.5" r="1.2" fill="currentColor"/><path d="M2 11l3.5-3.5 2.5 2 2.5-3 3 4" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" fill="none"/></svg>
      Image generation
    </div>
    <div class="nav-item" onclick="switchTab('both',this)">
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><rect x="1.5" y="3" width="5.5" height="10" rx="1.5" stroke="currentColor" stroke-width="1.2"/><rect x="9" y="3" width="5.5" height="10" rx="1.5" stroke="currentColor" stroke-width="1.2"/></svg>
      Generate both
    </div>
    <div class="nav-section">Analytics</div>
    <div class="nav-item" onclick="switchTab('history',this)">
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.2"/><path d="M8 5v3.5l2 1.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
      History &amp; analytics
    </div>
    <div class="sidebar-footer">
      <div class="theme-toggle" onclick="toggleTheme()">
        <div class="toggle-track"><div class="toggle-thumb"></div></div>
        <span class="toggle-label" id="theme-label">Dark mode</span>
      </div>
      <a href="/logout" class="logout-btn">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M6 2H3a1 1 0 00-1 1v10a1 1 0 001 1h3M10 11l3-3-3-3M13 8H6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Sign out
      </a>
      <div class="sidebar-info">Shefat Mazibar · W1967304<br>University of Westminster</div>
    </div>
  </div>

  <div class="main">
    <div class="topbar">
      <div>
        <div class="topbar-title" id="topbar-title">Text generation</div>
        <div class="topbar-sub">Groq · Llama 3.1 · Pollinations.ai</div>
      </div>
      <div class="live-badge"><span class="live-dot"></span>Live</div>
    </div>
    <div class="workspace">

      <div class="panel active" id="panel-text">
        <div class="two-col">
          <div class="card">
            <div class="card-label"><span class="label-dot"></span>Prompt &amp; settings</div>
            <textarea id="t-prompt" placeholder="Write a detailed blog post about the future of artificial intelligence..." rows="4"></textarea>
            <div class="ctrl-row">
              <div class="ctrl-group"><div class="ctrl-label">Model</div>
                <select id="t-model"><option value="qwen-7b">Qwen 2.5 7B</option><option value="llama-8b">Llama 3.1 8B</option></select>
              </div>
              <div class="ctrl-group"><div class="ctrl-label">Profile</div>
                <select id="t-profile"><option value="balanced">Balanced</option><option value="creative">Creative</option><option value="precise">Precise</option><option value="fast">Fast</option></select>
              </div>
            </div>
            <div class="slider-wrap">
              <span class="slider-name">Max tokens</span>
              <input type="range" min="50" max="500" value="300" step="10" id="t-tokens" oninput="document.getElementById('t-tok-v').textContent=this.value">
              <span class="slider-val" id="t-tok-v">300</span>
            </div>
            <div class="slider-wrap">
              <span class="slider-name">Temperature</span>
              <input type="range" min="1" max="20" value="7" step="1" id="t-temp" oninput="document.getElementById('t-tmp-v').textContent=(this.value/10).toFixed(1)">
              <span class="slider-val" id="t-tmp-v">0.7</span>
            </div>
            <button class="gen-btn" id="t-btn" onclick="generateText()">Generate text</button>
            <div class="status" id="t-status"></div>
          </div>
          <div class="card">
            <div class="card-label"><span class="label-dot" style="background:var(--cyan);box-shadow:0 0 6px var(--cyan)"></span>Output</div>
            <div class="output-box" id="t-output"><span class="output-placeholder">Generated content appears here...</span></div>
            <div class="meta-row" id="t-meta" style="display:none">
              <span class="chip purple" id="t-bleu"></span>
              <span class="chip" id="t-time"></span>
              <span class="chip" id="t-mchip"></span>
            </div>
          </div>
        </div>
      </div>

      <div class="panel" id="panel-image">
        <div class="two-col">
          <div class="card">
            <div class="card-label"><span class="label-dot" style="background:var(--pink);box-shadow:0 0 6px var(--pink)"></span>Prompt &amp; settings</div>
            <textarea id="i-prompt" placeholder="A neon-lit cyberpunk city at night, rain reflections, ultra detailed..." rows="4"></textarea>
            <div class="slider-wrap"><span class="slider-name">Width</span><input type="range" min="256" max="512" value="384" step="64" id="i-w" oninput="document.getElementById('i-wv').textContent=this.value+'px'"><span class="slider-val" id="i-wv">384px</span></div>
            <div class="slider-wrap"><span class="slider-name">Height</span><input type="range" min="256" max="512" value="384" step="64" id="i-h" oninput="document.getElementById('i-hv').textContent=this.value+'px'"><span class="slider-val" id="i-hv">384px</span></div>
            <div class="slider-wrap"><span class="slider-name">Steps</span><input type="range" min="10" max="25" value="15" step="5" id="i-steps" oninput="document.getElementById('i-sv').textContent=this.value"><span class="slider-val" id="i-sv">15</span></div>
            <button class="gen-btn" id="i-btn" onclick="generateImage()" style="background:linear-gradient(135deg,#7c3aed,#06b6d4)">Generate image</button>
            <div class="status" id="i-status"></div>
          </div>
          <div class="card">
            <div class="card-label"><span class="label-dot" style="background:var(--pink);box-shadow:0 0 6px var(--pink)"></span>Output</div>
            <div class="img-box" id="i-placeholder">Image renders here</div>
            <img class="result" id="i-img" alt="Generated image">
            <div class="meta-row" id="i-meta" style="display:none"><span class="chip purple" id="i-time"></span><span class="chip">Pollinations.ai</span></div>
          </div>
        </div>
      </div>

      <div class="panel" id="panel-both">
        <div class="two-col">
          <div class="card">
            <div class="card-label"><span class="label-dot" style="background:var(--cyan);box-shadow:0 0 6px var(--cyan)"></span>Prompt &amp; settings</div>
            <textarea id="b-prompt" placeholder="A futuristic Mars colony in 2150, domed habitats glowing under a red sky..." rows="4"></textarea>
            <div class="ctrl-row">
              <div class="ctrl-group"><div class="ctrl-label">Text model</div><select id="b-model"><option value="qwen-7b">Qwen 2.5 7B</option><option value="llama-8b">Llama 3.1 8B</option></select></div>
              <div class="ctrl-group"><div class="ctrl-label">Profile</div><select id="b-profile"><option value="balanced">Balanced</option><option value="creative">Creative</option><option value="precise">Precise</option><option value="fast">Fast</option></select></div>
            </div>
            <button class="gen-btn" id="b-btn" onclick="generateBoth()" style="background:linear-gradient(135deg,#06b6d4,#a855f7,#ec4899)">Generate both</button>
            <div class="status" id="b-status"></div>
          </div>
          <div class="card">
            <div class="card-label"><span class="label-dot"></span>Text output</div>
            <div class="output-box" id="b-text"><span class="output-placeholder">Text output appears here...</span></div>
            <div class="card-label" style="margin-top:14px"><span class="label-dot" style="background:var(--pink);box-shadow:0 0 6px var(--pink)"></span>Image output</div>
            <div class="img-box" id="b-placeholder">Image renders here</div>
            <img class="result" id="b-img" alt="Generated image">
          </div>
        </div>
      </div>

      <div class="panel" id="panel-history">
        <div class="stat-grid">
          <div class="stat-card"><div class="stat-num" id="s-total">0</div><div class="stat-lbl">Total generations</div></div>
          <div class="stat-card"><div class="stat-num" id="s-text">0</div><div class="stat-lbl">Text generations</div></div>
          <div class="stat-card"><div class="stat-num" id="s-img">0</div><div class="stat-lbl">Image generations</div></div>
        </div>
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
            <div class="card-label" style="margin:0"><span class="label-dot"></span>Recent activity</div>
            <button class="refresh-btn" onclick="loadHistory()">Refresh</button>
          </div>
          <div id="h-list"><div style="font-size:13px;color:var(--text3)">Click refresh to load your history.</div></div>
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
  el.classList.add('active');document.getElementById('panel-'+name).classList.add('active');
  document.getElementById('topbar-title').textContent=tabTitles[name];
  if(name==='history')loadHistory();
}
function toggleTheme(){
  const h=document.documentElement;const d=h.getAttribute('data-theme')==='dark';
  h.setAttribute('data-theme',d?'light':'dark');
  document.getElementById('theme-label').textContent=d?'Light mode':'Dark mode';
}
function setStatus(id,msg,type){
  const el=document.getElementById(id);if(!msg){el.style.display='none';return;}
  el.className='status '+type;el.innerHTML=type==='loading'?'<span class="spin"></span>'+msg:msg;
}
fetch('/whoami').then(r=>r.json()).then(d=>{
  const u=d.username||'User';
  document.getElementById('user-name').textContent=u;
  document.getElementById('user-avatar').textContent=u[0].toUpperCase();
});
async function generateText(){
  const prompt=document.getElementById('t-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('t-btn');btn.disabled=true;btn.textContent='Generating...';
  setStatus('t-status','Sending to Groq · Llama 3.1...','loading');
  document.getElementById('t-output').innerHTML='<span class="output-placeholder">Generating...</span>';
  document.getElementById('t-meta').style.display='none';
  try{
    const resp=await fetch('/generate_text',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt,model_key:document.getElementById('t-model').value,
        profile:document.getElementById('t-profile').value,
        max_tokens:parseInt(document.getElementById('t-tokens').value),
        temperature:parseFloat(document.getElementById('t-temp').value)/10})});
    const data=await resp.json();
    if(data.error){document.getElementById('t-output').innerHTML='<span style="color:#f87171">'+data.error+'</span>';setStatus('t-status',data.error,'error');}
    else{
      document.getElementById('t-output').textContent=data.text;setStatus('t-status','Generated successfully','success');
      if(data.meta){const p=data.meta.split('|');
        document.getElementById('t-bleu').textContent=(p[0]||'').trim();
        document.getElementById('t-time').textContent=(p[1]||'').trim();
        document.getElementById('t-mchip').textContent=(p[2]||'').trim();
        document.getElementById('t-meta').style.display='flex';
      }
    }
  }catch(e){setStatus('t-status','Network error: '+e.message,'error');}
  btn.disabled=false;btn.textContent='Generate text';
}
async function generateImage(){
  const prompt=document.getElementById('i-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('i-btn');btn.disabled=true;btn.textContent='Generating...';
  setStatus('i-status','Calling Pollinations.ai...','loading');
  document.getElementById('i-img').style.display='none';document.getElementById('i-placeholder').style.display='flex';
  document.getElementById('i-meta').style.display='none';
  try{
    const resp=await fetch('/generate_image',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt,width:parseInt(document.getElementById('i-w').value),
        height:parseInt(document.getElementById('i-h').value),steps:parseInt(document.getElementById('i-steps').value)})});
    const data=await resp.json();
    if(data.image_b64){
      const img=document.getElementById('i-img');img.src='data:image/png;base64,'+data.image_b64;img.style.display='block';
      document.getElementById('i-placeholder').style.display='none';
      document.getElementById('i-time').textContent=data.meta||'';document.getElementById('i-meta').style.display='flex';
      setStatus('i-status','Image generated successfully','success');
    }else{setStatus('i-status',data.error||'Unknown error','error');}
  }catch(e){setStatus('i-status','Network error: '+e.message,'error');}
  btn.disabled=false;btn.textContent='Generate image';
}
async function generateBoth(){
  const prompt=document.getElementById('b-prompt').value.trim();
  if(!prompt){alert('Please enter a prompt');return;}
  const btn=document.getElementById('b-btn');btn.disabled=true;btn.textContent='Generating...';
  setStatus('b-status','Generating text and image in parallel...','loading');
  document.getElementById('b-text').innerHTML='<span class="output-placeholder">Generating...</span>';
  document.getElementById('b-img').style.display='none';document.getElementById('b-placeholder').style.display='flex';
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
    if(id.image_b64){const img=document.getElementById('b-img');img.src='data:image/png;base64,'+id.image_b64;img.style.display='block';document.getElementById('b-placeholder').style.display='none';}
    else{document.getElementById('b-placeholder').textContent='Image error: '+(id.error||'Unknown');}
    setStatus('b-status','Done! Both generated successfully','success');
  }catch(e){setStatus('b-status','Error: '+e.message,'error');}
  btn.disabled=false;btn.textContent='Generate both';
}
async function loadHistory(){
  try{
    const resp=await fetch('/history');const data=await resp.json();const entries=data.entries||[];
    document.getElementById('s-total').textContent=entries.length;
    document.getElementById('s-text').textContent=entries.filter(e=>e.type==='text').length;
    document.getElementById('s-img').textContent=entries.filter(e=>e.type==='image').length;
    const list=document.getElementById('h-list');
    if(!entries.length){list.innerHTML='<div style="font-size:13px;color:var(--text3)">No history yet.</div>';return;}
    list.innerHTML=entries.map(e=>`<div class="hist-item"><span class="hist-badge ${e.type}">${e.type.toUpperCase()}</span><div class="hist-prompt">${e.prompt.slice(0,150)}</div><div class="hist-ts">${e.timestamp.slice(0,19).replace('T',' ')} · ${e.model}</div></div>`).join('');
  }catch(e){document.getElementById('h-list').innerHTML='<div style="color:#f87171;font-size:13px">Error loading history</div>';}
}
</script>
</body>
</html>"""

def make_auth_page(title, subtitle, icon, action, fields, btn, footer, alt_link, alt_text, message="", extras=""):
    return AUTH_HTML.format(
        title=title, subtitle=subtitle, icon=icon, action=action,
        fields=fields, btn=btn, footer=footer, alt_link=alt_link,
        alt_text=alt_text, message=message, extras=extras
    )

@app.route("/")
def landing():
    if "username" in session:
        return redirect("/app")
    return LANDING_HTML

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not email or not password:
            return make_auth_page(
                "Create account", "Join AICIG Studio — free forever.", "✨",
                "/signup",
                '<div class="form-group"><label>Username</label><input name="username" type="text" placeholder="yourname" value="'+username+'"></div><div class="form-group"><label>Email address</label><input name="email" type="email" placeholder="you@example.com" value="'+email+'"></div><div class="form-group"><label>Password</label><input name="password" type="password" placeholder="Min 6 characters"></div><div class="form-group"><label>Confirm password</label><input name="confirm" type="password" placeholder="Repeat password"></div>',
                "Create account", 'Already have an account? <a href="/login">Sign in</a>',
                "/login", "Sign in",
                message='<div class="error-msg">All fields are required.</div>'
            )

        if password != confirm:
            return make_auth_page(
                "Create account", "Join AICIG Studio — free forever.", "✨",
                "/signup",
                '<div class="form-group"><label>Username</label><input name="username" type="text" placeholder="yourname" value="'+username+'"></div><div class="form-group"><label>Email address</label><input name="email" type="email" placeholder="you@example.com" value="'+email+'"></div><div class="form-group"><label>Password</label><input name="password" type="password" placeholder="Min 6 characters"></div><div class="form-group"><label>Confirm password</label><input name="confirm" type="password" placeholder="Repeat password"></div>',
                "Create account", 'Already have an account? <a href="/login">Sign in</a>',
                "/login", "Sign in",
                message='<div class="error-msg">Passwords do not match.</div>'
            )

        if len(password) < 6:
            return make_auth_page(
                "Create account", "Join AICIG Studio — free forever.", "✨",
                "/signup",
                '<div class="form-group"><label>Username</label><input name="username" type="text" placeholder="yourname" value="'+username+'"></div><div class="form-group"><label>Email address</label><input name="email" type="email" placeholder="you@example.com" value="'+email+'"></div><div class="form-group"><label>Password</label><input name="password" type="password" placeholder="Min 6 characters"></div><div class="form-group"><label>Confirm password</label><input name="confirm" type="password" placeholder="Repeat password"></div>',
                "Create account", 'Already have an account? <a href="/login">Sign in</a>',
                "/login", "Sign in",
                message='<div class="error-msg">Password must be at least 6 characters.</div>'
            )

        users = load_users()
        if username in users:
            return make_auth_page(
                "Create account", "Join AICIG Studio — free forever.", "✨",
                "/signup",
                '<div class="form-group"><label>Username</label><input name="username" type="text" placeholder="yourname"></div><div class="form-group"><label>Email address</label><input name="email" type="email" placeholder="you@example.com" value="'+email+'"></div><div class="form-group"><label>Password</label><input name="password" type="password" placeholder="Min 6 characters"></div><div class="form-group"><label>Confirm password</label><input name="confirm" type="password" placeholder="Repeat password"></div>',
                "Create account", 'Already have an account? <a href="/login">Sign in</a>',
                "/login", "Sign in",
                message='<div class="error-msg">Username already taken. Please choose another.</div>'
            )

        users[username] = {
            "email": email,
            "password": generate_password_hash(password),
            "created": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        save_users(users)
        session["username"] = username
        return redirect("/app")

    fields = '<div class="form-group"><label>Username</label><input name="username" type="text" placeholder="yourname" autocomplete="username"></div><div class="form-group"><label>Email address</label><input name="email" type="email" placeholder="you@example.com"></div><div class="form-group"><label>Password</label><input name="password" type="password" placeholder="Min 6 characters" autocomplete="new-password"></div><div class="form-group"><label>Confirm password</label><input name="confirm" type="password" placeholder="Repeat password" autocomplete="new-password"></div>'
    extras = '<div class="features-mini"><div class="feat-item"><span class="feat-dot"></span>Free text generation via Groq</div><div class="feat-item"><span class="feat-dot"></span>Free image generation via Pollinations.ai</div><div class="feat-item"><span class="feat-dot"></span>Personal generation history</div></div>'
    return make_auth_page(
        "Create account", "Join AICIG Studio — free forever, no credit card needed.", "✨",
        "/signup", fields, "Create free account",
        'Already have an account? <a href="/login">Sign in</a>',
        "/login", "Sign in", extras=extras
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        users = load_users()

        if username not in users or not check_password_hash(users[username]["password"], password):
            fields = '<div class="form-group"><label>Username</label><input name="username" type="text" placeholder="yourname" value="'+username+'" autocomplete="username"></div><div class="form-group"><label>Password</label><input name="password" type="password" placeholder="Your password" autocomplete="current-password"></div>'
            return make_auth_page(
                "Welcome back", "Sign in to your AICIG Studio account.", "👋",
                "/login", fields, "Sign in",
                'No account? <a href="/signup">Create one free</a>',
                "/signup", "Sign up",
                message='<div class="error-msg">Incorrect username or password.</div>'
            )

        session["username"] = username
        return redirect("/app")

    fields = '<div class="form-group"><label>Username</label><input name="username" type="text" placeholder="yourname" autocomplete="username"></div><div class="form-group"><label>Password</label><input name="password" type="password" placeholder="Your password" autocomplete="current-password"></div>'
    return make_auth_page(
        "Welcome back", "Sign in to your AICIG Studio account.", "👋",
        "/login", fields, "Sign in",
        'No account? <a href="/signup">Create one free</a>',
        "/signup", "Sign up"
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/app")
def main_app():
    if "username" not in session:
        return redirect("/login")
    return APP_HTML

@app.route("/whoami")
def whoami():
    return jsonify({"username": session.get("username", "")})

@app.route("/generate_text", methods=["POST"])
def api_generate_text():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        data = request.get_json(force=True)
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "No prompt provided"})
        if not text_engine or not manager:
            return jsonify({"error": "Engine not loaded"})

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
            except:
                pass
        if logger:
            try:
                logger.log("text", prompt, text, model_key, params, {"bleu": bleu, "time": elapsed})
            except:
                pass

        return jsonify({"text": text, "meta": f"BLEU: {bleu:.4f} | Time: {elapsed:.2f}s | Model: {config['model_id']}"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/generate_image", methods=["POST"])
def api_generate_image():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
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
                except:
                    pass
            return jsonify({"image_b64": b64, "meta": f"Generated in {elapsed:.1f}s via Pollinations.ai"})
        else:
            return jsonify({"error": message})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/history")
def api_history():
    if "username" not in session:
        return jsonify({"entries": []}), 401
    try:
        if not logger:
            return jsonify({"entries": []})
        entries = logger.get_history(20)
        return jsonify({"entries": list(reversed(entries)) if entries else []})
    except Exception as e:
        return jsonify({"entries": [], "error": str(e)})


@app.route("/demo_image", methods=["POST"])
def demo_image():
    """Public image generation for landing page demo - no auth needed."""
    try:
        data = request.get_json(force=True)
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "No prompt"})
        if not image_engine:
            return jsonify({"error": "Image engine not loaded"})
        image, elapsed, message = image_engine.generate(prompt, width=384, height=384, steps=15)
        if image is not None:
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return jsonify({"image_b64": b64, "time": f"{elapsed:.1f}"})
        return jsonify({"error": message})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/health")
def health():
    return jsonify({"status": "ok", "text_engine": text_engine is not None, "image_engine": image_engine is not None})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
