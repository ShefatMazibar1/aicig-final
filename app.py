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
    # Try file first
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except:
            pass
    # Try environment variable as backup (survives redeploys on Render)
    env_users = os.environ.get("USERS_DATA", "")
    if env_users:
        try:
            return json.loads(env_users)
        except:
            pass
    return {}

def save_users(users):
    # Save to file
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except:
        pass
    # Also save to a persistent backup file in /tmp which survives longer
    try:
        with open("/tmp/aicig_users.json", "w") as f:
            json.dump(users, f, indent=2)
    except:
        pass

def load_users_all():
    users = {}
    # Load from all sources and merge
    for path in [USERS_FILE, "/tmp/aicig_users.json"]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                    users.update(data)
            except:
                pass
    env_users = os.environ.get("USERS_DATA", "")
    if env_users:
        try:
            users.update(json.loads(env_users))
        except:
            pass
    return users

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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--p:#9333ea;--p2:#7c3aed;--g:#d97706;--g2:#fbbf24;--c:#06b6d4;--pk:#ec4899;--bg:#02020a;--bg2:#05050f;--bg3:#0a0a1a}
html{scroll-behavior:smooth}
body{font-family:'Rajdhani',sans-serif;background:var(--bg);color:#fff;overflow-x:hidden;line-height:1.6}
canvas.bg{position:fixed;inset:0;z-index:0;pointer-events:none}
nav{position:fixed;top:0;left:0;right:0;z-index:100;height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 48px;background:#02020acc;backdrop-filter:blur(20px);border-bottom:1px solid #9333ea20}
.logo{font-family:'Orbitron',sans-serif;font-size:16px;font-weight:700;background:linear-gradient(90deg,#9333ea,#d97706);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:.06em;text-decoration:none}
.nav-links{display:flex;gap:28px}
.nav-links a{font-size:13px;color:#6b7280;text-decoration:none;letter-spacing:.04em;transition:color .15s}
.nav-links a:hover{color:#d97706}
.nav-r{display:flex;gap:10px}
.nb1{padding:7px 18px;border:1px solid #9333ea30;border-radius:4px;background:transparent;color:#9ca3af;font-size:13px;cursor:pointer;font-family:'Rajdhani',sans-serif;letter-spacing:.04em;transition:all .2s;text-decoration:none;display:inline-flex;align-items:center}
.nb1:hover{border-color:#d97706;color:#d97706}
.nb2{padding:7px 18px;border:none;border-radius:4px;background:linear-gradient(135deg,#7c3aed,#9333ea);color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:'Rajdhani',sans-serif;letter-spacing:.06em;transition:all .2s;text-decoration:none;display:inline-flex;align-items:center;position:relative;overflow:hidden}
.nb2::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,transparent,#ffffff20,transparent);transform:translateX(-100%);transition:transform .4s}
.nb2:hover::after{transform:translateX(100%)}
.hero{position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:80px 24px 40px;overflow:hidden}
.vibranium-ring{position:absolute;width:600px;height:600px;border-radius:50%;border:1px solid #9333ea15;left:50%;top:50%;transform:translate(-50%,-50%);animation:ringrot 20s linear infinite;pointer-events:none}
.ring2{width:900px;height:900px;border:1px solid #9333ea08;animation-duration:35s}
.ring3{width:300px;height:300px;border:1px solid #d9770620;animation-duration:12s;animation-direction:reverse}
@keyframes ringrot{from{transform:translate(-50%,-50%) rotate(0deg)}to{transform:translate(-50%,-50%) rotate(360deg)}}
.wakanda-badge{display:inline-flex;align-items:center;gap:8px;padding:6px 16px;border:1px solid #d9770640;border-radius:2px;font-size:11px;color:#d97706;letter-spacing:.14em;text-transform:uppercase;margin-bottom:32px;background:#d9770808;position:relative;animation:fadeUp .8s ease both}
.wakanda-badge::before,.wakanda-badge::after{content:'';position:absolute;width:6px;height:6px;border:1px solid #d97706}
.wakanda-badge::before{top:-1px;left:-1px;border-right:none;border-bottom:none}
.wakanda-badge::after{bottom:-1px;right:-1px;border-left:none;border-top:none}
.wdot{width:5px;height:5px;background:#d97706;box-shadow:0 0 10px #d97706;animation:wglow 2s infinite}
@keyframes wglow{0%,100%{opacity:1;box-shadow:0 0 8px #d97706}50%{opacity:.3;box-shadow:0 0 20px #d97706}}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.hero h1{font-family:'Orbitron',sans-serif;font-size:clamp(32px,6vw,72px);font-weight:900;letter-spacing:-.01em;line-height:1.05;margin-bottom:16px;text-transform:uppercase;animation:fadeUp .8s .1s ease both}
.line2{background:linear-gradient(90deg,#9333ea,#d97706,#06b6d4,#9333ea);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;background-size:300%;animation:cshift 6s linear infinite}
@keyframes cshift{0%{background-position:0%}100%{background-position:300%}}
.hero-sub{font-size:17px;color:#9ca3af;max-width:600px;line-height:1.7;margin:0 auto 40px;letter-spacing:.02em;animation:fadeUp .8s .2s ease both}
.hero-ctas{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;animation:fadeUp .8s .3s ease both}
.hc1{display:inline-flex;align-items:center;gap:8px;padding:14px 32px;background:linear-gradient(135deg,#7c3aed,#9333ea);color:#fff;font-size:14px;font-weight:700;border-radius:4px;cursor:pointer;border:none;font-family:'Rajdhani',sans-serif;letter-spacing:.08em;text-transform:uppercase;transition:all .2s;text-decoration:none;position:relative;overflow:hidden;box-shadow:0 0 30px #9333ea30}
.hc1:hover{transform:translateY(-2px);box-shadow:0 0 50px #9333ea50}
.hc1::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#ffffff60,transparent)}
.hc2{display:inline-flex;align-items:center;gap:8px;padding:14px 32px;border:1px solid #d9770640;color:#d97706;font-size:14px;font-weight:600;border-radius:4px;cursor:pointer;background:transparent;font-family:'Rajdhani',sans-serif;letter-spacing:.08em;text-transform:uppercase;transition:all .2s;text-decoration:none}
.hc2:hover{border-color:#d97706;background:#d9770808;box-shadow:0 0 20px #d9770620}
.hero-note{margin-top:20px;font-size:11px;color:#374151;letter-spacing:.1em;text-transform:uppercase;animation:fadeUp .8s .4s ease both}
.cards-row{position:relative;z-index:2;display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-top:56px;padding:0 24px;animation:fadeUp .8s .5s ease both}
.vcard{background:#05050f;border:1px solid #9333ea20;border-radius:6px;padding:20px;width:210px;position:relative;overflow:hidden;animation:cardfloat 5s ease-in-out infinite}
.vcard::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#9333ea,transparent)}
.vcard::after{content:'';position:absolute;top:0;left:0;width:1px;height:100%;background:linear-gradient(180deg,#9333ea,transparent)}
@keyframes cardfloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
.vcard:nth-child(2){animation-delay:1s;animation-duration:6s;border-color:#d9770625}
.vcard:nth-child(3){animation-delay:2s;animation-duration:4.5s;border-color:#06b6d425}
.vcard:nth-child(4){animation-delay:.5s;animation-duration:5.5s;border-color:#ec489925}
.vc-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.vc-icon{width:30px;height:30px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:13px}
.vc-live{display:flex;align-items:center;gap:4px;font-size:9px;color:#10b981;letter-spacing:.08em;text-transform:uppercase}
.vc-live-dot{width:4px;height:4px;border-radius:50%;background:#10b981;animation:wglow 1.5s infinite}
.vc-label{font-size:9px;color:#4b5563;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px}
.vc-val{font-family:'Orbitron',sans-serif;font-size:16px;font-weight:700;background:linear-gradient(90deg,#9333ea,#d97706);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.vc-bar{height:2px;background:#0a0a1a;border-radius:1px;margin-top:10px;overflow:hidden}
.vc-fill{height:100%;animation:barfill 3s ease-in-out infinite alternate}
@keyframes barfill{0%{width:30%}100%{width:92%}}
.out-lines{display:flex;flex-direction:column;gap:4px}
.ol{height:3px;border-radius:1px;animation:olshine 2s ease infinite}
.ol:nth-child(1){background:linear-gradient(90deg,#9333ea30,#9333ea80)}
.ol:nth-child(2){background:linear-gradient(90deg,#9333ea20,#d9770660);width:80%;animation-delay:.3s}
.ol:nth-child(3){background:linear-gradient(90deg,#9333ea30,#06b6d460);width:90%;animation-delay:.6s}
.ol:nth-child(4){background:linear-gradient(90deg,#9333ea20,#9333ea50);width:65%;animation-delay:.9s}
@keyframes olshine{0%,100%{opacity:.4}50%{opacity:1}}
.img-frame{width:100%;height:60px;background:#0a0a1a;border-radius:4px;position:relative;overflow:hidden;margin-top:8px;border:1px solid #9333ea15}
.scan-line{position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#d97706,transparent);animation:scandown 2s linear infinite}
@keyframes scandown{0%{top:0;opacity:1}100%{top:100%;opacity:.3}}
.px-grid{display:grid;grid-template-columns:repeat(10,1fr);gap:1px;padding:3px;height:100%}
.px{border-radius:1px;opacity:.3;animation:pxanim 3s infinite}
@keyframes pxanim{0%,100%{opacity:.15}50%{opacity:.8}}
.score-ring{width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;position:relative;margin:8px auto 0}
.score-ring svg{position:absolute;top:0;left:0;transform:rotate(-90deg)}
.score-val{font-family:'Orbitron',sans-serif;font-size:10px;font-weight:700;color:#d97706;position:relative;z-index:1}
.marquee-wrap{position:relative;z-index:1;border-top:1px solid #9333ea15;border-bottom:1px solid #9333ea15;padding:14px 0;overflow:hidden;background:linear-gradient(90deg,#9333ea05,#05050f,#9333ea05)}
.mq-track{display:flex;gap:48px;animation:mq 22s linear infinite;white-space:nowrap}
.mq-item{display:flex;align-items:center;gap:8px;font-size:11px;color:#374151;letter-spacing:.08em;text-transform:uppercase;flex-shrink:0}
.mq-dot{width:4px;height:4px;background:#d97706;box-shadow:0 0 6px #d97706}
@keyframes mq{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.stats-section{position:relative;z-index:1;padding:60px 48px;background:#05050f;border-bottom:1px solid #9333ea15}
.stats-inner{max-width:1000px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);gap:0}
@media(max-width:700px){.stats-inner{grid-template-columns:repeat(2,1fr)}}
.st{text-align:center;padding:24px;border-right:1px solid #9333ea15}
.st:last-child{border-right:none}
.sn{font-family:'Orbitron',sans-serif;font-size:42px;font-weight:900;background:linear-gradient(135deg,#9333ea,#d97706);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1}
.sl{font-size:11px;color:#4b5563;margin-top:8px;letter-spacing:.08em;text-transform:uppercase}
.features-section{position:relative;z-index:1;padding:80px 48px;max-width:1100px;margin:0 auto}
.eyebrow{font-size:10px;font-weight:700;color:#d97706;text-transform:uppercase;letter-spacing:.18em;margin-bottom:12px;display:flex;align-items:center;gap:10px}
.eyebrow::before{content:'';display:inline-block;width:20px;height:1px;background:#d97706}
.sec-h{font-family:'Orbitron',sans-serif;font-size:clamp(22px,3.5vw,38px);font-weight:700;text-transform:uppercase;letter-spacing:.02em;margin-bottom:12px;line-height:1.1}
.sec-p{font-size:15px;color:#6b7280;max-width:480px;line-height:1.7;margin-bottom:40px}
.feat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#9333ea15;border:1px solid #9333ea15}
@media(max-width:700px){.feat-grid{grid-template-columns:1fr}}
.fc{background:#05050f;padding:28px;transition:all .2s;position:relative;overflow:hidden}
.fc::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#9333ea40,transparent);opacity:0;transition:opacity .3s}
.fc:hover{background:#07071a}.fc:hover::before{opacity:1}
.fi{width:38px;height:38px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:17px;margin-bottom:14px}
.feat-icon-wrap{width:48px;height:48px;margin-bottom:16px;position:relative}
.feat-icon-wrap svg{filter:drop-shadow(0 0 8px var(--ic,#9333ea));transition:filter .3s}
.fc:hover .feat-icon-wrap svg{filter:drop-shadow(0 0 16px var(--ic,#9333ea)) drop-shadow(0 0 4px var(--ic,#9333ea))}
.ft{font-family:'Orbitron',sans-serif;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;color:#d97706}
.fd{font-size:13px;color:#6b7280;line-height:1.65}
.demo-section{position:relative;z-index:1;padding:80px 48px;max-width:1100px;margin:0 auto}
.demo-card{background:#05050f;border:1px solid #9333ea20;border-radius:6px;overflow:hidden;position:relative}
.demo-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#d97706,#9333ea,transparent)}
.demo-grid{display:grid;grid-template-columns:1fr 1fr}
@media(max-width:700px){.demo-grid{grid-template-columns:1fr}}
.dl{padding:28px;border-right:1px solid #9333ea15}
.dr{padding:28px;display:flex;flex-direction:column;gap:14px}
.df-label{font-size:9px;color:#4b5563;text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px}
.demo-ta{width:100%;background:#02020a;border:1px solid #9333ea25;border-radius:4px;padding:12px;font-size:13px;font-family:'Rajdhani',sans-serif;color:#fff;resize:none;min-height:80px;outline:none;line-height:1.5;letter-spacing:.02em;transition:border-color .2s}
.demo-ta:focus{border-color:#9333ea}.demo-ta::placeholder{color:#374151}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip{font-size:10px;padding:4px 10px;border:1px solid #9333ea20;color:#6b7280;cursor:pointer;letter-spacing:.04em;transition:all .15s;background:transparent;font-family:'Rajdhani',sans-serif;border-radius:2px}
.chip:hover{border-color:#d97706;color:#d97706;background:#d9770808}
.demo-btn{width:100%;padding:12px;margin-top:16px;border:none;border-radius:4px;background:linear-gradient(135deg,#7c3aed,#9333ea);color:#fff;font-size:12px;font-weight:700;cursor:pointer;font-family:'Orbitron',sans-serif;letter-spacing:.06em;text-transform:uppercase;transition:all .2s;position:relative;overflow:hidden}
.demo-btn:hover{transform:translateY(-1px);box-shadow:0 8px 30px #9333ea40}
.demo-btn:disabled{opacity:.4;cursor:wait;transform:none}
.demo-btn::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#ffffff40,transparent)}
.dprog{height:2px;background:#0a0a1a;margin-top:12px;display:none;overflow:hidden}
.dpf{height:100%;background:linear-gradient(90deg,#9333ea,#d97706,#06b6d4);width:0%;transition:width .5s}
.dstat{font-size:11px;color:#4b5563;margin-top:8px;display:none;align-items:center;gap:6px;letter-spacing:.04em}
.dstat.show{display:flex}
.spin{width:10px;height:10px;border:1.5px solid #9333ea;border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.demo-imgwrap{flex:1;background:#02020a;border:1px solid #9333ea20;border-radius:4px;min-height:200px;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.demo-imgwrap img{width:100%;height:100%;object-fit:cover;border-radius:4px;display:none}
.demo-empty{display:flex;flex-direction:column;align-items:center;gap:8px;color:#374151}
.demo-empty svg{opacity:.2}.demo-empty p{font-size:10px;text-transform:uppercase;letter-spacing:.1em}
.steps-section{position:relative;z-index:1;background:#05050f;border-top:1px solid #9333ea15;padding:80px 48px}
.steps-inner{max-width:1100px;margin:0 auto}
.steps-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-top:48px}
@media(max-width:700px){.steps-grid{grid-template-columns:1fr 1fr}}
.step{padding:24px;border-right:1px solid #9333ea15}
.step:last-child{border-right:none}
.snum{font-family:'Orbitron',sans-serif;font-size:10px;font-weight:700;color:#9333ea;letter-spacing:.1em;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.snum::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,#9333ea30,transparent)}
.stitle{font-family:'Orbitron',sans-serif;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px;color:#d97706}
.sdesc{font-size:13px;color:#6b7280;line-height:1.65}
.cta-banner{position:relative;z-index:1;margin:60px 48px;border-radius:6px;overflow:hidden;padding:72px 48px;text-align:center;border:1px solid #9333ea20}
.cta-bg{position:absolute;inset:0;background:linear-gradient(135deg,#0d0520,#1a0520,#050d1a);z-index:0}
.cta-glow1{position:absolute;top:-80px;left:30%;width:300px;height:200px;background:radial-gradient(ellipse,#9333ea25,transparent 70%);pointer-events:none}
.cta-glow2{position:absolute;bottom:-60px;right:25%;width:250px;height:180px;background:radial-gradient(ellipse,#d9770620,transparent 70%);pointer-events:none}
.cta-content{position:relative;z-index:1}
.cta-h{font-family:'Orbitron',sans-serif;font-size:clamp(24px,4vw,42px);font-weight:900;text-transform:uppercase;letter-spacing:.02em;margin-bottom:12px;line-height:1.1}
.cta-p{font-size:16px;color:#6b7280;margin-bottom:32px;letter-spacing:.02em}
.cta-btns{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
footer{position:relative;z-index:1;border-top:1px solid #9333ea15;padding:32px 48px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.flogo{font-family:'Orbitron',sans-serif;font-size:14px;font-weight:700;background:linear-gradient(90deg,#9333ea,#d97706);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.ftext{font-size:11px;color:#374151;letter-spacing:.04em}
</style>
</head>
<body>
<canvas class="bg" id="bgc"></canvas>
<nav>
  <a href="/" class="logo">AICIG Studio</a>
  <div class="nav-links">
    <a href="#features">Features</a><a href="#demo">Live Demo</a><a href="#how">How It Works</a>
  </div>
  <div class="nav-r">
    <a href="/login" class="nb1">Sign In</a>
    <a href="/signup" class="nb2">Get Started →</a>
  </div>
</nav>
<section class="hero">
  <div class="vibranium-ring"></div>
  <div class="vibranium-ring ring2"></div>
  <div class="vibranium-ring ring3"></div>
  <div style="position:relative;z-index:2;width:100%;max-width:1100px">
    <div class="wakanda-badge"><span class="wdot"></span>University of Westminster · Final Year Project</div>
    <h1 style="display:block"><span style="display:block">Stop Searching.</span><span class="line2">Start Generating.</span></h1>
    <p class="hero-sub">AICIG Studio fuses cutting-edge language models with AI image synthesis — transforming your prompts into powerful content in seconds. Free. Always.</p>
    <div class="hero-ctas">
      <a href="/signup" class="hc1"><svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M6.5 1v11M1 6.5h11" stroke="white" stroke-width="2.2" stroke-linecap="round"/></svg>Activate Studio</a>
      <a href="#demo" class="hc2">View Demo →</a>
    </div>
    <div class="hero-note">No credit card · Free forever · Open source</div>
    <div class="cards-row">
      <div class="vcard">
        <div class="vc-top"><div class="vc-icon" style="background:#9333ea15;border:1px solid #9333ea30">✍️</div><div class="vc-live"><span class="vc-live-dot"></span>Live</div></div>
        <div class="vc-label">Text generation</div>
        <div class="out-lines"><div class="ol"></div><div class="ol"></div><div class="ol"></div><div class="ol"></div></div>
        <div class="vc-bar"><div class="vc-fill" style="background:linear-gradient(90deg,#9333ea,#d97706)"></div></div>
      </div>
      <div class="vcard">
        <div class="vc-top"><div class="vc-icon" style="background:#d9770615;border:1px solid #d9770630">🖼️</div><div class="vc-live" style="color:#d97706"><span class="vc-live-dot" style="background:#d97706"></span>Gen</div></div>
        <div class="vc-label">Image synthesis</div>
        <div class="img-frame"><div class="scan-line"></div><div class="px-grid" id="pxg"></div></div>
      </div>
      <div class="vcard">
        <div class="vc-top"><div class="vc-icon" style="background:#06b6d415;border:1px solid #06b6d430">📊</div><div class="vc-live" style="color:#06b6d4"><span class="vc-live-dot" style="background:#06b6d4"></span>Score</div></div>
        <div class="vc-label">BLEU quality score</div>
        <div class="score-ring"><svg width="48" height="48" viewBox="0 0 48 48"><circle cx="24" cy="24" r="19" fill="none" stroke="#0a0a1a" stroke-width="4"/><circle cx="24" cy="24" r="19" fill="none" stroke="url(#sg)" stroke-width="4" stroke-dasharray="119.4" stroke-dashoffset="20" stroke-linecap="round"/><defs><linearGradient id="sg" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#9333ea"/><stop offset="100%" stop-color="#d97706"/></linearGradient></defs></svg><span class="score-val">84%</span></div>
        <div class="vc-bar" style="margin-top:10px"><div class="vc-fill" style="background:linear-gradient(90deg,#06b6d4,#9333ea)"></div></div>
      </div>
      <div class="vcard">
        <div class="vc-top"><div class="vc-icon" style="background:#ec489915;border:1px solid #ec489930">⚡</div><div class="vc-live" style="color:#ec4899"><span class="vc-live-dot" style="background:#ec4899"></span>Both</div></div>
        <div class="vc-label">Generate both mode</div>
        <div class="out-lines"><div class="ol" style="background:linear-gradient(90deg,#ec489930,#ec489980)"></div><div class="ol" style="background:linear-gradient(90deg,#ec489920,#9333ea60);width:75%"></div></div>
        <div class="img-frame" style="height:36px;margin-top:8px"><div class="scan-line" style="background:linear-gradient(90deg,transparent,#ec4899,transparent)"></div><div class="px-grid" id="pxg2"></div></div>
      </div>
    </div>
  </div>
</section>
<div class="marquee-wrap">
  <div class="mq-track">
    <div class="mq-item"><span class="mq-dot"></span>Text Generation</div><div class="mq-item"><span class="mq-dot"></span>Image Synthesis</div><div class="mq-item"><span class="mq-dot"></span>BLEU Evaluation</div><div class="mq-item"><span class="mq-dot"></span>Llama 3.1 · Qwen 2.5</div><div class="mq-item"><span class="mq-dot"></span>Pollinations.ai</div><div class="mq-item"><span class="mq-dot"></span>Generation History</div><div class="mq-item"><span class="mq-dot"></span>Dark · Light Mode</div><div class="mq-item"><span class="mq-dot"></span>Real-Time Analytics</div>
    <div class="mq-item"><span class="mq-dot"></span>Text Generation</div><div class="mq-item"><span class="mq-dot"></span>Image Synthesis</div><div class="mq-item"><span class="mq-dot"></span>BLEU Evaluation</div><div class="mq-item"><span class="mq-dot"></span>Llama 3.1 · Qwen 2.5</div><div class="mq-item"><span class="mq-dot"></span>Pollinations.ai</div><div class="mq-item"><span class="mq-dot"></span>Generation History</div><div class="mq-item"><span class="mq-dot"></span>Dark · Light Mode</div><div class="mq-item"><span class="mq-dot"></span>Real-Time Analytics</div>
  </div>
</div>
<div class="stats-section">
  <div class="stats-inner">
    <div class="st"><div class="sn" id="sn1">0</div><div class="sl">AI Models</div></div>
    <div class="st"><div class="sn" id="sn2">0%</div><div class="sl">Free Forever</div></div>
    <div class="st"><div class="sn" id="sn3">0s</div><div class="sl">Avg Generation</div></div>
    <div class="st"><div class="sn">∞</div><div class="sl">Generations</div></div>
  </div>
</div>
<section id="features" class="features-section">
  <div class="eyebrow">Capabilities</div>
  <div class="sec-h">The Full Arsenal</div>
  <div class="sec-p">Every tool you need to generate, evaluate, and track AI content — all in one platform, completely free.</div>
  <div class="feat-grid">
    <div class="fc">
      <div class="feat-icon-wrap" style="--ic:#9333ea">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="8" fill="#9333ea15"/>
          <rect x="1" y="1" width="46" height="46" rx="7" stroke="#9333ea" stroke-width="1" stroke-opacity=".3"/>
          <rect x="12" y="14" width="24" height="3" rx="1.5" fill="#9333ea" opacity=".9">
            <animate attributeName="width" values="24;20;24" dur="3s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values=".9;.4;.9" dur="3s" repeatCount="indefinite"/>
          </rect>
          <rect x="12" y="20" width="18" height="3" rx="1.5" fill="#d97706" opacity=".7">
            <animate attributeName="width" values="18;22;18" dur="2.5s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values=".7;1;.7" dur="2.5s" repeatCount="indefinite"/>
          </rect>
          <rect x="12" y="26" width="21" height="3" rx="1.5" fill="#9333ea" opacity=".6">
            <animate attributeName="width" values="21;16;21" dur="3.5s" repeatCount="indefinite"/>
          </rect>
          <rect x="12" y="32" width="14" height="3" rx="1.5" fill="#d97706" opacity=".5">
            <animate attributeName="width" values="14;19;14" dur="2s" repeatCount="indefinite"/>
          </rect>
          <circle cx="36" cy="33" r="1.5" fill="#9333ea">
            <animate attributeName="opacity" values="1;0;1" dur=".8s" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>
      <div class="ft">Text Generation</div>
      <div class="fd">Articles, blogs and summaries with Llama 3.1 via Groq — lightning fast responses on free tier.</div>
    </div>
    <div class="fc">
      <div class="feat-icon-wrap" style="--ic:#d97706">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="8" fill="#d9770615"/>
          <rect x="1" y="1" width="46" height="46" rx="7" stroke="#d97706" stroke-width="1" stroke-opacity=".3"/>
          <rect x="10" y="10" width="28" height="20" rx="3" stroke="#d97706" stroke-width="1.2" fill="none" opacity=".6"/>
          <circle cx="16" cy="17" r="3" fill="#d97706" opacity=".8">
            <animate attributeName="r" values="3;2.5;3" dur="2s" repeatCount="indefinite"/>
          </circle>
          <polyline points="10,30 18,22 24,26 30,19 38,30" stroke="#9333ea" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <animate attributeName="stroke-dasharray" values="0,100;60,100" dur="2s" fill="freeze"/>
          </polyline>
          <line x1="10" y1="38" x2="38" y2="38" stroke="#d97706" stroke-width="1" opacity=".3"/>
          <line x1="10" y1="34" x2="38" y2="34" stroke="#d97706" stroke-width="1" opacity=".3"/>
          <rect x="10" y="30" width="28" height="8" rx="2" fill="#d97706" fill-opacity=".06"/>
        </svg>
      </div>
      <div class="ft">Image Synthesis</div>
      <div class="fd">Stunning AI images from any prompt via Pollinations.ai — completely free, unlimited generations.</div>
    </div>
    <div class="fc">
      <div class="feat-icon-wrap" style="--ic:#06b6d4">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="8" fill="#06b6d415"/>
          <rect x="1" y="1" width="46" height="46" rx="7" stroke="#06b6d4" stroke-width="1" stroke-opacity=".3"/>
          <rect x="9" y="13" width="13" height="22" rx="2" stroke="#9333ea" stroke-width="1.2" fill="#9333ea08"/>
          <rect x="26" y="13" width="13" height="22" rx="2" stroke="#06b6d4" stroke-width="1.2" fill="#06b6d408"/>
          <line x1="22" y1="24" x2="26" y2="24" stroke="#d97706" stroke-width="1.5" stroke-linecap="round">
            <animate attributeName="stroke-opacity" values="1;0;1" dur="1.2s" repeatCount="indefinite"/>
          </line>
          <polygon points="25,21 29,24 25,27" fill="#d97706" opacity=".8">
            <animate attributeName="opacity" values=".8;0;.8" dur="1.2s" repeatCount="indefinite"/>
          </polygon>
          <rect x="12" y="18" width="7" height="2" rx="1" fill="#9333ea" opacity=".7">
            <animate attributeName="width" values="7;5;7" dur="2s" repeatCount="indefinite"/>
          </rect>
          <rect x="12" y="22" width="5" height="2" rx="1" fill="#9333ea" opacity=".5">
            <animate attributeName="width" values="5;7;5" dur="1.8s" repeatCount="indefinite"/>
          </rect>
          <rect x="29" y="18" width="7" height="2" rx="1" fill="#06b6d4" opacity=".7">
            <animate attributeName="width" values="7;5;7" dur="2.2s" repeatCount="indefinite"/>
          </rect>
          <rect x="29" y="22" width="5" height="2" rx="1" fill="#06b6d4" opacity=".5">
            <animate attributeName="width" values="5;7;5" dur="1.6s" repeatCount="indefinite"/>
          </rect>
        </svg>
      </div>
      <div class="ft">Generate Both</div>
      <div class="fd">Run text and image generation simultaneously from a single prompt — parallel AI power.</div>
    </div>
    <div class="fc">
      <div class="feat-icon-wrap" style="--ic:#10b981">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="8" fill="#10b98115"/>
          <rect x="1" y="1" width="46" height="46" rx="7" stroke="#10b981" stroke-width="1" stroke-opacity=".3"/>
          <circle cx="24" cy="24" r="13" stroke="#10b981" stroke-width="1" fill="none" opacity=".2"/>
          <circle cx="24" cy="24" r="13" stroke="#10b981" stroke-width="2.5" fill="none" stroke-dasharray="81.7" stroke-dashoffset="20" stroke-linecap="round" transform="rotate(-90 24 24)">
            <animate attributeName="stroke-dashoffset" values="82;18;82" dur="4s" repeatCount="indefinite" ease="ease-in-out"/>
            <animate attributeName="stroke" values="#10b981;#d97706;#10b981" dur="4s" repeatCount="indefinite"/>
          </circle>
          <text x="24" y="21" text-anchor="middle" fill="#10b981" font-size="8" font-weight="700" font-family="monospace">BLEU</text>
          <text x="24" y="30" text-anchor="middle" fill="#d97706" font-size="9" font-weight="700" font-family="monospace">0.84</text>
        </svg>
      </div>
      <div class="ft">BLEU Scoring</div>
      <div class="fd">Automatic BLEU-4 evaluation on every output — measure quality and track improvement over time.</div>
    </div>
    <div class="fc">
      <div class="feat-icon-wrap" style="--ic:#f59e0b">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="8" fill="#f59e0b15"/>
          <rect x="1" y="1" width="46" height="46" rx="7" stroke="#f59e0b" stroke-width="1" stroke-opacity=".3"/>
          <rect x="10" y="20" width="28" height="4" rx="2" fill="#f59e0b" fill-opacity=".15" stroke="#f59e0b" stroke-width=".8" stroke-opacity=".3"/>
          <rect x="10" y="28" width="28" height="4" rx="2" fill="#9333ea" fill-opacity=".1" stroke="#9333ea" stroke-width=".8" stroke-opacity=".3"/>
          <rect x="10" y="12" width="28" height="4" rx="2" fill="#06b6d4" fill-opacity=".1" stroke="#06b6d4" stroke-width=".8" stroke-opacity=".3"/>
          <rect x="10" y="12" width="20" height="4" rx="2" fill="#06b6d4" opacity=".6">
            <animate attributeName="width" values="20;26;16;20" dur="3s" repeatCount="indefinite"/>
          </rect>
          <rect x="10" y="20" width="16" height="4" rx="2" fill="#f59e0b" opacity=".8">
            <animate attributeName="width" values="16;22;12;16" dur="2.5s" repeatCount="indefinite"/>
          </rect>
          <rect x="10" y="28" width="24" height="4" rx="2" fill="#9333ea" opacity=".7">
            <animate attributeName="width" values="24;18;26;24" dur="3.5s" repeatCount="indefinite"/>
          </rect>
          <circle cx="38" cy="36" r="5" fill="#f59e0b" fill-opacity=".15" stroke="#f59e0b" stroke-width="1"/>
          <line x1="36" y1="36" x2="40" y2="36" stroke="#f59e0b" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="38" y1="34" x2="38" y2="38" stroke="#f59e0b" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="ft">Full Control</div>
      <div class="fd">Tune temperature, tokens, profiles. Balanced, creative, precise, or fast — you decide.</div>
    </div>
    <div class="fc">
      <div class="feat-icon-wrap" style="--ic:#ec4899">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="8" fill="#ec489915"/>
          <rect x="1" y="1" width="46" height="46" rx="7" stroke="#ec4899" stroke-width="1" stroke-opacity=".3"/>
          <rect x="10" y="10" width="20" height="6" rx="1.5" fill="#ec4899" fill-opacity=".7"/>
          <rect x="10" y="19" width="28" height="3" rx="1.5" fill="#9333ea" opacity=".5">
            <animate attributeName="opacity" values=".5;.9;.5" dur="2s" repeatCount="indefinite"/>
          </rect>
          <rect x="10" y="24" width="22" height="3" rx="1.5" fill="#d97706" opacity=".5">
            <animate attributeName="opacity" values=".5;.9;.5" dur="2.4s" repeatCount="indefinite"/>
          </rect>
          <rect x="10" y="29" width="25" height="3" rx="1.5" fill="#ec4899" opacity=".4">
            <animate attributeName="opacity" values=".4;.8;.4" dur="1.8s" repeatCount="indefinite"/>
          </rect>
          <rect x="10" y="34" width="18" height="3" rx="1.5" fill="#06b6d4" opacity=".5">
            <animate attributeName="opacity" values=".5;.9;.5" dur="2.2s" repeatCount="indefinite"/>
          </rect>
          <circle cx="33" cy="13" r="4" fill="none" stroke="#ec4899" stroke-width="1.2">
            <animate attributeName="r" values="4;5;4" dur="1.5s" repeatCount="indefinite"/>
            <animate attributeName="stroke-opacity" values="1;.3;1" dur="1.5s" repeatCount="indefinite"/>
          </circle>
          <circle cx="33" cy="13" r="2" fill="#ec4899">
            <animate attributeName="opacity" values="1;.4;1" dur="1.5s" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>
      <div class="ft">History & Analytics</div>
      <div class="fd">Every generation logged with timestamps, metrics, and model info. Full personal session history.</div>
    </div>
  </div>
</section>
<section id="demo" class="demo-section">
  <div class="eyebrow">Live Demo</div>
  <div class="sec-h">Try It. Right Now.</div>
  <div class="sec-p">No account needed. Generate a real AI image from any prompt — powered by Pollinations.ai.</div>
  <div class="demo-card">
    <div class="demo-grid">
      <div class="dl">
        <div class="df-label">Your Prompt</div>
        <textarea class="demo-ta" id="dp" placeholder="A vibranium-powered AI city at night..." rows="3"></textarea>
        <div class="df-label" style="margin-top:16px">Quick Examples</div>
        <div class="chips">
          <button class="chip" onclick="setP('A vibranium-powered neon city at night')">Vibranium City</button>
          <button class="chip" onclick="setP('A panther made of purple energy and light')">Energy Panther</button>
          <button class="chip" onclick="setP('A futuristic African kingdom with purple crystals')">Crystal Kingdom</button>
          <button class="chip" onclick="setP('An AI robot with glowing purple circuits')">AI Robot</button>
          <button class="chip" onclick="setP('A space station orbiting Earth with purple aurora')">Space Station</button>
        </div>
        <button class="demo-btn" id="dgb" onclick="demoGen()">Generate Image →</button>
        <div class="dprog" id="dprog"><div class="dpf" id="dpf"></div></div>
        <div class="dstat" id="dstat"></div>
      </div>
      <div class="dr">
        <div class="df-label">Generated Image</div>
        <div class="demo-imgwrap" id="diw">
          <div class="demo-empty" id="dem"><svg width="44" height="44" viewBox="0 0 44 44" fill="none"><rect x="4" y="4" width="36" height="36" rx="4" stroke="currentColor" stroke-width="1.2"/><circle cx="14" cy="15" r="3" fill="currentColor" opacity=".4"/><path d="M4 30l10-10 8 8 7-8 15 10" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg><p>Image renders here</p></div>
          <img id="dimg" alt="Generated">
        </div>
        <div style="font-size:10px;color:#374151;letter-spacing:.06em;text-transform:uppercase">Sign up for text generation + history →</div>
      </div>
    </div>
  </div>
</section>
<section id="how" class="steps-section">
  <div class="steps-inner">
    <div class="eyebrow">Protocol</div>
    <div class="sec-h">Activation Sequence</div>
    <div class="steps-grid">
      <div class="step"><div class="snum">01 <span style="color:#4b5563;font-weight:400;font-size:9px">Account</span></div><div class="stitle">Create Account</div><div class="sdesc">Sign up in 30 seconds. No credit card, no subscription. Username, email, password — done.</div></div>
      <div class="step"><div class="snum">02 <span style="color:#4b5563;font-weight:400;font-size:9px">Prompt</span></div><div class="stitle">Write Prompt</div><div class="sdesc">Describe what you need — an article, an image, or both. Natural language, any topic.</div></div>
      <div class="step"><div class="snum">03 <span style="color:#4b5563;font-weight:400;font-size:9px">Configure</span></div><div class="stitle">Set Parameters</div><div class="sdesc">Choose your model, tune temperature and tokens — or use smart defaults and generate.</div></div>
      <div class="step"><div class="snum">04 <span style="color:#4b5563;font-weight:400;font-size:9px">Output</span></div><div class="stitle">Generate & Review</div><div class="sdesc">Instant results. BLEU-scored text, rendered images. Everything saved to your history.</div></div>
    </div>
  </div>
</section>
<div class="cta-banner">
  <div class="cta-bg"></div><div class="cta-glow1"></div><div class="cta-glow2"></div>
  <div class="cta-content">
    <div class="cta-h">Ready to Generate?</div>
    <div class="cta-p">Join AICIG Studio today. Free forever, no credit card needed.</div>
    <div class="cta-btns">
      <a href="/signup" class="hc1">Activate Free Account →</a>
      <a href="/login" class="hc2">Sign In</a>
    </div>
  </div>
</div>
<footer>
  <div class="flogo">AICIG Studio</div>
  <div class="ftext">Shefat Mazibar · W1967304 · University of Westminster · Supervisor: Jeffrey Ferguson</div>
</footer>
<script>
const bgc=document.getElementById('bgc');
const ctx=bgc.getContext('2d');
let W,H,pts=[],hexes=[];
function resize(){W=bgc.width=innerWidth;H=bgc.height=Math.max(document.body.scrollHeight,innerHeight);}
setTimeout(resize,300);window.addEventListener('resize',resize);
class Pt{constructor(){this.reset()}reset(){this.x=Math.random()*W;this.y=Math.random()*H;this.vx=(Math.random()-.5)*.18;this.vy=(Math.random()-.5)*.18;this.r=Math.random()*1.2+.3;this.col=['#9333ea','#7c3aed','#d97706','#06b6d4','#ec4899'][~~(Math.random()*5)];this.a=Math.random()*.28+.06;this.p=Math.random()*Math.PI*2;}tick(){this.x+=this.vx;this.y+=this.vy;this.p+=.01;if(this.x<0||this.x>W)this.vx*=-1;if(this.y<0||this.y>H)this.vy*=-1;}draw(){ctx.globalAlpha=this.a*(0.5+0.5*Math.sin(this.p));ctx.fillStyle=this.col;ctx.beginPath();ctx.arc(this.x,this.y,this.r,0,Math.PI*2);ctx.fill();}}
class Hex{constructor(){this.x=Math.random()*W;this.y=Math.random()*H;this.size=Math.random()*22+8;this.rot=Math.random()*Math.PI*2;this.vr=(Math.random()-.5)*.003;this.a=Math.random()*.07+.02;this.col=Math.random()>.5?'#9333ea':'#d97706';}tick(){this.rot+=this.vr;}draw(){ctx.globalAlpha=this.a;ctx.strokeStyle=this.col;ctx.lineWidth=.5;ctx.beginPath();for(let i=0;i<6;i++){const a=this.rot+i*Math.PI/3;i===0?ctx.moveTo(this.x+this.size*Math.cos(a),this.y+this.size*Math.sin(a)):ctx.lineTo(this.x+this.size*Math.cos(a),this.y+this.size*Math.sin(a));}ctx.closePath();ctx.stroke();}}
for(let i=0;i<120;i++)pts.push(new Pt());
for(let i=0;i<70;i++)hexes.push(new Hex());
function frame(){ctx.clearRect(0,0,W,H);hexes.forEach(h=>{h.tick();h.draw();});for(let i=0;i<pts.length;i++){for(let j=i+1;j<pts.length;j++){const dx=pts[i].x-pts[j].x,dy=pts[i].y-pts[j].y,d=Math.sqrt(dx*dx+dy*dy);if(d<90){ctx.globalAlpha=(1-d/90)*.06;ctx.strokeStyle='#9333ea';ctx.lineWidth=.5;ctx.beginPath();ctx.moveTo(pts[i].x,pts[i].y);ctx.lineTo(pts[j].x,pts[j].y);ctx.stroke();}}}pts.forEach(p=>{p.tick();p.draw();});ctx.globalAlpha=1;requestAnimationFrame(frame);}
frame();
const pxcols=['#9333ea','#7c3aed','#d97706','#06b6d4','#ec4899','#02020a','#05050f'];
['pxg','pxg2'].forEach(id=>{const el=document.getElementById(id);if(!el)return;const n=60;for(let i=0;i<n;i++){const d=document.createElement('div');d.className='px';d.style.background=pxcols[~~(Math.random()*pxcols.length)];d.style.animationDelay=(Math.random()*2.5)+'s';d.style.animationDuration=(1.5+Math.random()*2)+'s';el.appendChild(d);}});
setInterval(()=>{document.querySelectorAll('.px').forEach(p=>{if(Math.random()>.7)p.style.background=pxcols[~~(Math.random()*pxcols.length)];});},600);
function countUp(el,target,suf,dur){const s=performance.now();function step(now){const prog=Math.min((now-s)/dur,1);const e=1-Math.pow(1-prog,3);el.textContent=Math.round(e*target)+suf;if(prog<1)requestAnimationFrame(step);}requestAnimationFrame(step);}
setTimeout(()=>{countUp(document.getElementById('sn1'),3,'',1400);countUp(document.getElementById('sn2'),100,'%',1700);countUp(document.getElementById('sn3'),2,'s',1500);},800);
const ro=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){e.target.style.opacity='1';e.target.style.transform='translateY(0)';}});},{threshold:.1});
document.querySelectorAll('.fc,.step,.vcard').forEach(el=>{el.style.opacity='0';el.style.transform='translateY(20px)';el.style.transition='opacity .6s ease,transform .6s ease';ro.observe(el);});
function setP(t){document.getElementById('dp').value=t;}
async function demoGen(){
  const prompt=document.getElementById('dp').value.trim();
  if(!prompt){alert('Enter a prompt or pick an example');return;}
  const btn=document.getElementById('dgb');btn.disabled=true;btn.textContent='Generating...';
  document.getElementById('dprog').style.display='block';
  document.getElementById('dstat').className='dstat show';
  document.getElementById('dstat').innerHTML='<span class="spin"></span> Calling Pollinations.ai...';
  document.getElementById('dimg').style.display='none';document.getElementById('dem').style.display='flex';
  let p=0;const pi=setInterval(()=>{p=Math.min(p+4,88);document.getElementById('dpf').style.width=p+'%';},400);
  try{
    const resp=await fetch('/demo_image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
    const data=await resp.json();clearInterval(pi);document.getElementById('dpf').style.width='100%';
    if(data.image_b64){const img=document.getElementById('dimg');img.src='data:image/png;base64,'+data.image_b64;img.style.display='block';document.getElementById('dem').style.display='none';document.getElementById('dstat').innerHTML='&#10003; Generated in '+data.time+'s &mdash; <a href="/signup" style="color:#d97706;text-decoration:none;letter-spacing:.04em">Activate Full Access &rarr;</a>';}
    else{document.getElementById('dstat').textContent='Error: '+(data.error||'Unknown');}
  }catch(e){clearInterval(pi);document.getElementById('dstat').textContent='Error: '+e.message;}
  setTimeout(()=>{document.getElementById('dprog').style.display='none';document.getElementById('dpf').style.width='0';},1200);
  btn.disabled=false;btn.textContent='Generate Image \u2192';
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

        users = load_users_all()
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
        users = load_users_all()

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
