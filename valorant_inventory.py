import os
import json
import csv
import argparse
import base64
import threading
import webbrowser
import time
import re
import hashlib
import logging
import unicodedata
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache

try:
    import riot_auth
    import requests
    import urllib3
    from flask import Flask, jsonify, request
    from flask_cors import CORS
    from werkzeug.serving import make_server
except ImportError:
    print('Missing dependencies: run START.bat or python -m pip install -r requirements.txt')
    input('Press Enter to quit...')
    raise SystemExit(1)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Valinven</title>
<script defer src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
<script defer src="https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js"></script>
<style>
:root{color-scheme:dark;--bg:#090c10;--panel:#ffffff08;--red:#ff4655;--text:#f2f4f7;--muted:#969ca6;--line:#ffffff15;--green:#9af2c6;--glass:linear-gradient(135deg,#ffffff12,#ffffff04)}
*{box-sizing:border-box;letter-spacing:0}html{scroll-behavior:smooth;scroll-padding-top:110px}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}body:before{content:'';position:fixed;inset:0;z-index:-1;background:linear-gradient(118deg,transparent 25%,#ff46550b 49%,transparent 70%),linear-gradient(165deg,#ffffff06,transparent 38%,#9af2c605);pointer-events:none}
button,input,select{font:inherit;color:var(--text);background:#ffffff07;border:1px solid var(--line);border-radius:12px;padding:11px 15px;transition:background .18s,border-color .18s}button,select{cursor:pointer}button:hover{background:#ffffff13;border-color:#ffffff38}button:disabled{opacity:.4;cursor:wait}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #ff7883;outline-offset:4px}select option{background:#15191e}a{color:inherit}svg{width:19px;height:19px;flex:none}[hidden]{display:none!important}
header{position:sticky;top:0;z-index:20;background:#0d1013b8;backdrop-filter:blur(30px) saturate(150%);border-bottom:1px solid #ffffff13;box-shadow:0 1px #ffffff04}.header-inner{max-width:1504px;margin:auto;min-height:88px;padding:16px 40px;display:flex;align-items:center;gap:36px}.brand{display:flex;align-items:center;gap:13px;text-decoration:none}.brand strong{display:block;font-size:16px;font-weight:650}.brand small{display:block;color:var(--muted);font-size:10px}.logo{width:29px;height:26px;background:var(--red);clip-path:polygon(0 0,48% 60%,100% 0,100% 36%,53% 100%,43% 100%,0 41%);flex:none}
.nav{display:flex;gap:5px;margin:auto;background:var(--glass);border:1px solid #ffffff1c;border-radius:99px;padding:5px;box-shadow:inset 0 1px #ffffff0d,0 8px 24px #0003}.nav a{padding:9px 22px;display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);text-decoration:none;border-radius:99px}.nav a.active{background:#ffffff14;color:white;box-shadow:inset 0 1px #ffffff1f,0 2px 5px #0003}.header-actions{display:flex;align-items:center;gap:13px}.region{font-size:10px;font-weight:650;border:1px solid #9af2c628;color:var(--green);border-radius:99px;padding:6px 10px;background:#9af2c60b}.region:before{content:'';display:inline-block;width:5px;height:5px;background:currentColor;border-radius:50%;margin-right:7px}.icon-button{height:40px;width:40px;padding:10px;display:grid;place-items:center;border-radius:50%;background:var(--glass);box-shadow:inset 0 1px #ffffff12}.updated{font-size:11px;font-variant-numeric:tabular-nums}.muted{color:var(--muted)}
main{max-width:1504px;margin:auto;padding:38px 40px}.page-title{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:0 0 35px}.eyebrow,.label{font-size:10px;text-transform:uppercase;color:var(--muted)}.eyebrow{color:#ff7f89;display:flex;align-items:center;gap:9px;margin-bottom:10px}.eyebrow:before{content:'';width:20px;height:1px;background:var(--red)}h1{font-size:34px;line-height:1.2;margin:0;font-weight:600}h1 span{color:var(--muted);font-weight:350}h2{font-size:20px;line-height:1.3;font-weight:550;margin:0}h3{font-weight:550}.local-note{display:flex;gap:8px;align-items:center;color:var(--muted);font-size:11px}
.summary{display:grid;grid-template-columns:1.05fr .62fr 1.4fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-bottom:15px;background:linear-gradient(100deg,#ffffff03,transparent)}.stat{padding:30px 28px;min-width:0;border-right:1px solid var(--line)}.stat:first-child{padding-left:0}.stat:last-child{border:0;padding-right:0}.label{margin-bottom:14px;display:flex;align-items:center;gap:8px}.label svg{width:15px;height:15px;color:#c7cbd0}.total{font-size:44px;line-height:1.1;font-weight:550;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.total.unavailable{font-size:24px}.eur{color:var(--green)}.amount{font-size:16px;margin-top:13px}.stat .muted{font-size:11px;margin-top:12px}.featured{display:grid;grid-template-columns:1.1fr 1fr;align-items:center;gap:14px;min-height:92px}.featured img{width:100%;height:105px;object-fit:contain;filter:drop-shadow(0 12px 16px #0008)}.featured strong{display:block;font-size:17px;line-height:1.4;overflow-wrap:anywhere}.featured .badge{margin-top:10px}.estimate{font-size:11px;color:var(--muted);margin:0 0 34px;line-height:1.7}
.section-heading{display:flex;align-items:center;justify-content:space-between;gap:20px}.section-heading>div{display:flex;align-items:center;gap:12px}.section-heading .muted{font-size:11px}.count{font-size:11px;color:var(--muted);padding:3px 8px;background:#ffffff0a;border-radius:6px}.view-modes{display:flex;padding:3px;background:var(--glass);border:1px solid var(--line);border-radius:10px;gap:3px}.view-modes button{padding:6px;width:30px;height:30px;display:grid;place-items:center;background:none;border:0;border-radius:7px}.view-modes button[aria-pressed=true]{background:#ffffff16}.view-modes svg{width:16px;height:16px}
.toolbar{display:flex;gap:10px;margin:23px 0 16px}.search-wrap{display:flex;align-items:center;gap:10px;flex:1;min-width:180px;padding-left:14px;background:#ffffff05;border:1px solid var(--line);border-radius:12px}.search-wrap svg{color:var(--muted);width:16px;height:16px}.search{background:none!important;flex:1;min-width:0;border:0;padding-left:0}.toolbar select{font-size:12px}.filters{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:23px}.filters button{font-size:11px;padding:7px 14px;border-radius:99px;border-color:transparent;background:#ffffff05;color:var(--muted)}.filters button[aria-pressed=true]{background:#ff465518;color:#ff8d97;border-color:#ff465550;box-shadow:inset 0 1px #ffb2b21a}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:16px}.skin{position:relative;border:1px solid #ffffff15;border-radius:20px;background:linear-gradient(140deg,#ffffff0c,#ffffff03);box-shadow:inset 0 1px #ffffff12,0 10px 22px #0002;overflow:hidden;transition:transform .25s,border-color .25s,box-shadow .25s;isolation:isolate}.skin:before{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(115deg,transparent 20%,#ffffff06 42%,transparent 55%);opacity:.4;pointer-events:none}.skin:hover{transform:translateY(-5px);border-color:#ff465554;box-shadow:inset 0 1px #ffffff30,0 16px 40px #0005,0 0 24px #ff46550a}.skin-top{display:flex;justify-content:space-between;align-items:center;padding:16px 16px 0}.tier{font-size:9px;color:#b4b7c1;display:flex;align-items:center;gap:6px}.tier:before{content:'';width:5px;height:5px;background:currentColor;transform:rotate(45deg)}.tier[data-tier=Exclusive]{color:#e6b689}.tier[data-tier=Ultra]{color:#f1d68e}.tier[data-tier=Premium]{color:#d5a8e6}.inspect{border:0;background:none;padding:0;width:24px;height:24px;display:grid;place-items:center;color:#7f848c}.inspect:hover{color:white;background:none}.inspect svg{width:14px;height:14px}.skin-media{height:135px;display:flex;align-items:center;justify-content:center;padding:17px 23px;position:relative}.skin-media:after{content:'';position:absolute;bottom:12px;left:20%;right:20%;height:1px;background:linear-gradient(90deg,transparent,#ffffff18,transparent)}.skin img{width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 12px 9px #0008);transition:transform .4s}.skin:hover img{transform:scale(1.08) rotate(-3deg)}.skin-body{padding:9px 17px 17px}.weapon-label{font-size:10px;color:var(--muted)}.skin h3{font-size:14px;line-height:1.45;height:41px;margin:5px 0 15px;overflow-wrap:anywhere}.prices{display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:13px}.badge{display:inline-block;font-size:11px;border-radius:6px;padding:4px 7px;max-width:100%;overflow-wrap:anywhere}.vp{color:#ff8c96;background:#ff46550d}.prices .eur{font-size:10px;background:#9af2c608}.non-retail{font-size:10px;color:var(--muted)}.source-link{font-size:10px;color:var(--muted);text-decoration:none}.source-link:hover{color:white}.source-link:after{content:' ↗'}.grid.compact{grid-template-columns:repeat(auto-fill,minmax(175px,1fr))}.grid.compact .skin-media{height:100px}.grid.compact .skin{border-radius:14px}
.bottom{display:grid;grid-template-columns:1fr 1fr;gap:48px;margin-top:52px;padding-top:32px;border-top:1px solid var(--line)}.bottom>section{min-width:0}.bottom h2{margin-bottom:25px}.chart-wrap{height:365px;width:100%;position:relative}.ranking{padding:0;list-style:none;margin:0}.rank{display:grid;grid-template-columns:25px 65px 1fr auto;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid #ffffff0a;font-size:11px}.rank>*{min-width:0;overflow-wrap:anywhere}.rank-number{color:var(--muted);font-size:10px}.rank:first-child .rank-number{color:var(--red)}.rank img{width:65px;height:35px;object-fit:contain}.rank strong{font-weight:500}.rank-price{text-align:right;font-variant-numeric:tabular-nums}.rank-price span{display:block}.rank-price .eur{font-size:10px}.bars{list-style:none;padding:0}.bars li{margin:18px 0;font-size:12px}.bar{height:6px;background:var(--red);border-radius:99px;margin-top:8px}
.privacy{margin-top:45px;padding-top:22px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}.privacy summary{cursor:pointer}.privacy p{max-width:1000px;line-height:1.9}.privacy a{color:#c6cfdd;text-underline-offset:3px}.center-screen{min-height:70vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:18px}.center-screen .logo{width:80px;height:74px;margin-bottom:18px}.center-screen h2{font-size:29px}.center-screen p{margin:0}.spinner{width:26px;height:26px;border:2px solid var(--line);border-top-color:var(--red);border-radius:50%;animation:spin 1s linear infinite;margin-top:10px}.progress{width:280px;height:3px;background:var(--line);overflow:hidden;margin:18px}.progress:after{content:'';display:block;background:var(--red);height:100%;width:40%;animation:progress 1.3s infinite alternate}.notice{display:flex;justify-content:space-between;align-items:center;gap:15px;padding:14px 18px;margin-bottom:24px;background:#d9b96b10;border:1px solid #d9b96b33;border-radius:14px;font-size:12px}.error{background:#ff46550d;border-color:#ff46553a}.notice button{font-size:11px;padding:7px 12px}.empty{text-align:center;padding:50px;color:var(--muted)}
dialog{border:1px solid #ffffff25;border-radius:28px;color:var(--text);background:linear-gradient(145deg,#242930eb,#12161bf5);backdrop-filter:blur(36px) saturate(140%);box-shadow:inset 0 1px #ffffff1a,0 30px 100px #0009;width:min(650px,calc(100% - 40px));padding:30px}dialog::backdrop{background:#0009;backdrop-filter:blur(9px)}.modal-close{float:right}.modal-image{height:210px;display:flex;align-items:center;justify-content:center;clear:both;padding:20px}.modal-image img{width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 18px 15px #0007)}dialog h2{font-size:26px;margin:12px 0}dialog .prices{margin:20px 0}dialog .prices .badge{font-size:16px}.modal-details{color:var(--muted);font-size:12px;line-height:1.9}.modal-details a{display:inline-block;margin-top:15px}
.skin{backdrop-filter:blur(16px) saturate(130%)}.skin:before{background:linear-gradient(var(--reflection,115deg),transparent 20%,#ffffff0b 42%,transparent 62%);transition:opacity .3s}.skin:hover:before{opacity:1}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes progress{to{transform:translateX(150%)}}@keyframes enter{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}#screen-inventory{animation:enter .4s ease}
@media(max-width:1100px){.header-inner,main{padding-left:24px;padding-right:24px}.updated,.local-note{display:none}.total{font-size:34px}.summary{grid-template-columns:1fr .6fr 1.2fr}.stat{padding:26px 18px}.featured{grid-template-columns:1fr}.featured img{height:70px}.featured strong{font-size:14px}}
@media(max-width:720px){.header-inner{min-height:75px;gap:12px;flex-wrap:wrap}.nav{order:3;width:100%;justify-content:center}.nav a{padding:7px 12px}.header-actions{margin-left:auto}main{padding:26px 16px}.page-title{margin-bottom:24px}h1{font-size:28px}.summary{grid-template-columns:1fr 1fr}.stat:nth-child(2){border:0}.stat:last-child{grid-column:1/-1;border-top:1px solid var(--line);padding-left:0}.featured{grid-template-columns:1fr 1fr}.total{font-size:30px}.toolbar{flex-wrap:wrap}.search-wrap{flex-basis:100%}.toolbar select{flex:1;min-width:0}.grid{grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:12px}.skin{border-radius:16px}.skin-media{height:115px;padding:14px}.skin-body{padding:8px 12px 14px}.skin h3{font-size:12px}.skin-top{padding:12px 12px 0}.bottom{grid-template-columns:1fr;gap:30px}.rank{grid-template-columns:20px 45px 1fr auto;gap:8px}.rank img{width:45px}.chart-wrap{height:320px}.notice{flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{animation:none!important;transition:none!important}}
</style></head><body>
<header><div class="header-inner">
<a class="brand" href="#screen-inventory"><div class="logo" aria-hidden="true"></div><div><strong>VALORANT</strong><small>INVENTORY / LOCAL</small></div></a>
<nav class="nav" aria-label="Navigation"><a href="#collection" class="active"><i data-lucide="layers-3"></i>Collection</a><a href="#analytics"><i data-lucide="chart-no-axes-combined"></i>Analytics</a><a href="#ranking-section"><i data-lucide="trophy"></i>Top 10</a></nav>
<div class="header-actions"><span id="updated" class="muted updated"></span><span id="region" class="region">LOCAL</span><button id="refresh" class="icon-button" title="Refresh inventory" aria-label="Refresh inventory" disabled><i data-lucide="refresh-cw">↻</i></button></div>
</div></header>
<main>
<div id="error" class="notice error" role="alert" hidden><span id="error-message"></span><button id="retry">Try again</button></div>
<section id="screen-waiting" class="center-screen"><div class="logo" aria-hidden="true"></div><h2 id="waiting-title">Detecting your Riot session</h2><p class="muted" id="waiting-text">Looking for an existing session...</p><div class="spinner" id="waiting-spinner" aria-label="Detecting"></div><button id="login" hidden>Sign in to Riot</button><p id="connection-status" class="muted" aria-live="polite"></p></section>
<section id="screen-loading" class="center-screen" hidden><div class="logo" aria-hidden="true"></div><h2>Your arsenal is on its way.</h2><div class="progress"></div><p id="loading-message" class="muted" aria-live="polite">Connecting to the session...</p></section>
<section id="screen-disconnected" class="notice" hidden><span id="disconnected-message"></span><button id="detect">Detect again</button></section>
<section id="screen-inventory" hidden>
<div class="page-title"><div><div class="eyebrow">Personal collection</div><h1>Your arsenal. <span>In detail.</span></h1></div><span class="local-note"><i data-lucide="shield-check"></i>Secure local session</span></div>
<div class="summary">
<div class="stat"><div class="label"><i data-lucide="gem"></i>Catalog value of skins</div><div id="total-vp" class="total"></div><div id="total-eur" class="amount eur"></div></div>
<div class="stat"><div class="label"><i data-lucide="layers-3"></i>Skins owned</div><div id="skin-count" class="total"></div><div id="retail-count" class="muted"></div></div>
<div class="stat"><div class="label"><i data-lucide="sparkles"></i>Most valuable piece</div><div id="featured" class="featured"></div></div>
</div>
<p id="estimate" class="estimate"></p>
<section id="collection">
<div class="section-heading"><div><h2>Collection</h2><span id="result-count" class="count"></span></div><div class="view-modes" role="group" aria-label="Grid density"><button id="view-large" title="Comfortable grid" aria-label="Comfortable grid" aria-pressed="true"><i data-lucide="layout-grid"></i></button><button id="view-compact" title="Compact grid" aria-label="Compact grid" aria-pressed="false"><i data-lucide="grid-3x3"></i></button></div></div>
<div class="toolbar"><label class="search-wrap"><i data-lucide="search"></i><input id="search" class="search" type="search" placeholder="Search your arsenal..." aria-label="Search for a skin"></label><select id="price-filter" aria-label="Filter by acquisition"><option value="all">All skins</option><option value="priced">With VP price</option><option value="battlepass">Battle passes</option><option value="bundle_only">Bundle only</option><option value="unknown">Unknown price</option></select><select id="weapon" aria-label="Filter by weapon"><option value="">All weapons</option></select><select id="sort" aria-label="Sort skins"><option value="desc">Price, high to low</option><option value="asc">Price, low to high</option><option value="az">Name: A → Z</option><option value="za">Name: Z → A</option></select></div>
<div id="filters" class="filters" role="group" aria-label="Weapon categories"></div><div id="grid" class="grid"></div><p id="empty" class="empty" hidden>No skin matches this search.</p>
</section>
<div id="analytics" class="bottom"><section><h2>Value, weapon by weapon.</h2><div id="chart-wrap" class="chart-wrap"><canvas id="chart" aria-label="Top 10 weapons by total value" role="img"></canvas></div><ul id="bar-fallback" class="bars" hidden></ul></section><section id="ranking-section"><h2>The centerpieces.</h2><ol id="ranking" class="ranking"></ol></section></div>
</section>
<details id="pricing-details" class="privacy"><summary>Privacy &amp; valuation method</summary>
<p>All account data stays on your PC. The inventory and tokens are kept in memory only. Session tokens are sent to Riot APIs and nowhere else. The catalog and images come from valorant-api.com. Public skin pages are fetched from ValorantInfo without any account id or Riot token; those requests do reveal to that site which pages were requested. Visual libraries are loaded from CDNs.</p>
<p>Individual prices from the Riot v3 store come first. For every other skin, the tool uses the catalog prices published by ValorantInfo, plus sourced references dated 9 September 2026 for entries that are missing or wrong there. These community sources can contain errors. The source of each price is shown on the skin's card. Bundle-only skins are included when a catalog value specific to the skin is documented; the bundle price is never added. Battle passes, contracts and skins with no individual value are excluded from the total. Discounts and upgrades are not included.</p>
<p>Euros are estimated pro rata from the nearest listed tier, using the displayed prices: 475 VP / €5, 1,000 / €10, 2,050 / €20, 3,650 / €35, 5,350 / €50, 11,000 / €100. These tiers vary by region and with current Riot pricing. The total is a catalog value, not your actual spending and not a resale value.</p>
</details>
</main>
<dialog id="skin-dialog" aria-labelledby="modal-name"><button id="close-dialog" class="icon-button modal-close" aria-label="Close" title="Close"><i data-lucide="x"></i></button><div id="modal-image" class="modal-image"></div><div id="modal-tier" class="eyebrow"></div><h2 id="modal-name"></h2><div id="modal-prices" class="prices"></div><div id="modal-details" class="modal-details"></div></dialog>
<script>
const $=id=>document.getElementById(id), nf=new Intl.NumberFormat('en-US'), money=new Intl.NumberFormat('en-US',{style:'currency',currency:'EUR',maximumFractionDigits:2});
let inventory=null,chart=null,busy=false,polling=false,ready=false,currentSession=null,loadedSession=null,category='All',nextRetry=0,generation=0;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const vp=s=>s.price_vp===null?'Price unavailable':nf.format(s.price_vp)+' VP';
const eur=s=>s.price_eur===null?'':('~'+money.format(s.price_eur));
function picture(s){return s.image_url?`<img src="${esc(s.image_url)}" alt="${esc(s.name)}" loading="lazy" referrerpolicy="no-referrer">`:'<span class="muted">Image unavailable</span>'}
function showScreen(name){for(const n of ['waiting','loading','inventory'])$('screen-'+n).hidden=n!==name}
async function api(path){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),120000);try{const r=await fetch(path,{signal:controller.signal,cache:'no-store'});const d=await r.json();if(!r.ok)throw new Error(d.error||'Service unavailable');return d}finally{clearTimeout(timer)}}
function showError(message){$('error-message').textContent=message;$('error').hidden=false}
async function post(path){const r=await fetch(path,{method:'POST',cache:'no-store'});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||'Service unavailable');return d}
async function signIn(){const b=$('login');b.disabled=true;b.textContent='Sign-in window open...';$('error').hidden=true;try{await post('/api/login');loadedSession=null;await pollStatus()}catch(e){showError(e.message)}finally{b.disabled=false;b.textContent='Sign in to Riot'}}
function updateWaiting(status){const b=$('login'),s=$('waiting-spinner'),ti=$('waiting-title'),tx=$('waiting-text');const needed=status==='needs_login';b.hidden=!needed;s.hidden=needed;ti.textContent=needed?'Sign in to your Riot account':'Detecting your Riot session';tx.textContent=needed?'A Riot window will open. Neither the game nor Riot Client is required.':'Looking for an existing session...'}
async function pollStatus(){if(polling)return;polling=true;try{const d=await api('/api/status');ready=d.status==='ready';currentSession=d.session||null;updateWaiting(d.status);$('connection-status').textContent=d.status==='loading'?'Connecting to the Riot session...':'';
if(!ready)loadedSession=null;
if(inventory){$('screen-disconnected').hidden=ready&&loadedSession===currentSession;$('disconnected-message').textContent=(ready?'Syncing the session · Latest data from ':'Riot session unavailable · Data from ')+new Date(inventory.updated_at).toLocaleTimeString('en-US');}
if(ready&&currentSession!==loadedSession&&!busy&&Date.now()>=nextRetry)loadInventory();
}catch(e){ready=false;loadedSession=null;if(inventory){$('screen-disconnected').hidden=false;$('disconnected-message').textContent='Local server unreachable · Last inventory kept';}else $('connection-status').textContent='Local server unreachable. Check the terminal.';}finally{polling=false;$('refresh').disabled=busy||!ready}}
async function loadInventory(refresh=false){if(busy||!ready)return;busy=true;$('refresh').disabled=true;$('error').hidden=true;const session=currentSession,run=++generation;
if(!inventory)showScreen('loading');const messages=['Reading the Riot session...','Fetching tokens...','Loading the inventory...','Computing prices...','Almost ready...'];$('loading-message').textContent=messages[0];const timers=[500,1000,2000,3000,4000].map((ms,i)=>setTimeout(()=>$('loading-message').textContent=messages[Math.min(i+1,4)],ms));
try{const d=await api(refresh?'/api/refresh':'/api/inventory');if(run!==generation||!ready||currentSession!==session)return;inventory=d;loadedSession=session;nextRetry=0;renderInventory(d);$('screen-disconnected').hidden=true;}
catch(e){nextRetry=Date.now()+15000;showError(e.name==='AbortError'?'The fetch took too long. Try again.':e.message);showScreen(inventory?'inventory':'waiting');}
finally{timers.forEach(clearTimeout);busy=false;$('refresh').disabled=!ready;if(!ready&&!inventory)showScreen('waiting')}}
function priceLabel(s) {
  if (s.price_vp !== null) return nf.format(s.price_vp)+' VP';
  return ({battlepass:'Battle pass',contract:'Agent contract',bundle_only:'Bundle exclusive'})[s.acquisition] || 'Price unavailable';
}
function priceBadges(s) {
  return s.price_vp !== null
    ? `<span class="badge vp" title="${esc(priceSource(s))}">${vp(s)}</span><span class="badge eur">${eur(s)}</span>`
    : `<span class="non-retail">${esc(priceLabel(s))}</span>`;
}
function priceSource(s) {
  return ({riot_store:'Individual price reported by Riot',public_catalog:'ValorantInfo catalog price',reference:'Catalog reference verified 2026-09-09'})[s.price_source] || 'No individual price available';
}
function renderInventory(d) {
  $('region').textContent=d.player.shard.toUpperCase();
  $('updated').textContent='Updated at '+new Date(d.updated_at).toLocaleTimeString('en-US');
  $('total-vp').textContent=d.summary.total_vp===null?'Prices unavailable':nf.format(d.summary.total_vp)+' VP';
  $('total-vp').classList.toggle('unavailable',d.summary.total_vp===null);
  $('total-eur').textContent=d.summary.total_eur===null?'Estimate unavailable':'≈ '+money.format(d.summary.total_eur);
  $('skin-count').textContent=nf.format(d.summary.skin_count);
  $('retail-count').textContent=(d.summary.priced_count ?? d.skins.filter(s=>s.price_vp!==null).length)+' skins priced';
  const best=d.summary.most_expensive;
  $('featured').innerHTML=best?picture(best)+`<div><strong>${esc(best.name)}</strong><span class="badge vp">${vp(best)}</span></div>`:'<span class="muted">No individual price available</span>';
  $('estimate').textContent=[
    (d.summary.riot_price_count||0)+' Riot prices',
    (d.summary.catalog_price_count||0)+' catalog prices',
    (d.summary.battlepass_count||0)+' battle pass skins',
    (d.summary.bundle_only_count||0)+' bundle exclusive(s)',
    (d.summary.unknown_count ?? d.summary.unpriced_count)+' unknown prices',
    'Euros estimated · Passes excluded · Bundles not added up'
  ].join(' · ')+(d.warnings.length?' '+d.warnings.join(' '):'');
  const old=$('weapon').value;
  $('weapon').innerHTML='<option value="">All weapons</option>'+[...new Set(d.skins.map(s=>s.weapon))].sort().map(w=>`<option value="${esc(w)}">${esc(w)}</option>`).join('');
  if([...$('weapon').options].some(o=>o.value===old))$('weapon').value=old;
  renderGrid();
  const top=d.skins.filter(s=>s.price_vp!==null).sort((a,b)=>b.price_vp-a.price_vp).slice(0,10);
  $('ranking').innerHTML=top.map((s,i)=>`<li class="rank"><span class="rank-number">${String(i+1).padStart(2,'0')}</span>${picture(s)}<strong>${esc(s.name)}</strong><div class="rank-price"><span>${vp(s)}</span><span class="eur">${eur(s)}</span></div></li>`).join('')||'<li class="muted">No price available</li>';
  showScreen('inventory');
  renderChart(d.skins);
}
function renderGrid() {
  if(!inventory)return;
  const q=normalizedSearch($('search').value),weapon=$('weapon').value,sort=$('sort').value,priceFilter=$('price-filter').value;
  const groups={Rifle:['Vandal','Phantom','Bulldog','Guardian'],Pistol:['Classic','Shorty','Frenzy','Ghost','Sheriff','Bandit']};
  const skins=inventory.skins.filter(s=>
    normalizedSearch(s.name+' '+s.weapon+' '+(s.collection||'')).includes(q)&&
    (!weapon||s.weapon===weapon)&&
    (category==='All'||s.weapon===category||(groups[category]||[]).includes(s.weapon))&&
    (priceFilter==='all'||(priceFilter==='priced'?s.price_vp!==null:priceFilter==='unknown'?s.price_vp===null&&s.acquisition==='unknown':s.acquisition===priceFilter))
  );
  skins.sort((a,b)=>sort==='az'?a.name.localeCompare(b.name,'en'):sort==='za'?b.name.localeCompare(a.name,'en'):a.price_vp===null?(b.price_vp===null?0:1):b.price_vp===null?-1:sort==='asc'?a.price_vp-b.price_vp:b.price_vp-a.price_vp);
  $('result-count').textContent=skins.length+' / '+inventory.skins.length;
  $('empty').hidden=skins.length>0;
  $('grid').innerHTML=skins.map(s=>`<article class="skin" data-skin="${esc(s.uuid)}">
    <div class="skin-top"><span class="tier" data-tier="${esc(s.tier||'Standard')}">${esc(s.tier||'Standard')}</span><button class="inspect" title="Inspect ${esc(s.name)}" aria-label="Inspect ${esc(s.name)}"><i data-lucide="maximize-2"></i></button></div>
    <div class="skin-media">${picture(s)}</div>
    <div class="skin-body"><span class="weapon-label">${esc(s.weapon)}</span><h3>${esc(s.name)}</h3><div class="prices">${priceBadges(s)}</div></div></article>`).join('');
  window.lucide?.createIcons();
}
function normalizedSearch(s){return s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('en')}
function inspectSkin(uuid) {
  const s=inventory?.skins.find(s=>s.uuid===uuid);if(!s)return;
  $('modal-image').innerHTML=picture(s);
  $('modal-name').textContent=s.name;
  $('modal-tier').textContent=[s.weapon,s.tier,s.collection].filter(Boolean).join(' / ');
  $('modal-prices').innerHTML=priceBadges(s);
  const notes={
    battlepass:'Obtained from a battle pass. No individual VP price; excluded from the total.',
    contract:'Contract reward. No individual VP price; excluded from the total.',
    bundle_only:(s.price_vp!==null?'Catalog value of the skin: '+nf.format(s.price_vp)+' VP, included in the total. ':'No documented individual value; excluded from the total. ')+
      'Sold in a bundle depending on the region. Full bundle: '+nf.format(s.bundle_price_vp||0)+' VP, not added to the total. Euros are an estimate.'
  };
  $('modal-details').textContent=notes[s.acquisition]||priceSource(s)+'. Catalog value, excluding discounts and upgrades. Euros are an estimate.';
  if(s.source_url){const a=document.createElement('a');a.href=s.source_url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='View the price source ↗';$('modal-details').append(document.createElement('br'),a);}
  $('skin-dialog').showModal();
}
function renderChart(skins) {
  if (skins.length && skins.every(s=>s.price_vp===null)) {
    if (chart) { chart.destroy(); chart=null; }
    $('chart-wrap').hidden=true;
    $('bar-fallback').hidden=false;
    $('bar-fallback').innerHTML='<li class="muted">Prices unavailable right now.</li>';
    return;
  }
  $('chart-wrap').hidden=false;
  $('bar-fallback').hidden=true;
  const grouped = {};
  for (const s of skins) {
    grouped[s.weapon] ??= {vp:0, count:0};
    grouped[s.weapon].vp += s.price_vp || 0;
    grouped[s.weapon].count++;
  }
  const entries = Object.entries(grouped).sort((a,b)=>b[1].vp-a[1].vp).slice(0,10);
  const labels = entries.map(([w,v])=>`${w}: ${nf.format(v.vp)} VP (${v.count} skins)`);
  if (chart) { chart.destroy(); chart = null; }
  if (!window.Chart) {
    $('chart-wrap').hidden = true;
    $('bar-fallback').hidden = false;
    const max = Math.max(1,...entries.map(e=>e[1].vp));
    $('bar-fallback').innerHTML = entries.map(([w,v],i)=>`<li>${esc(labels[i])}<div class="bar" style="width:${v.vp/max*100}%"></div></li>`).join('');
    return;
  }
  chart = new Chart($('chart'), {
    type: 'bar',
    data: {
      labels: entries.map(e=>e[0]),
      datasets: [{data:entries.map(e=>e[1].vp), backgroundColor:'#ff4655', borderRadius:3, maxBarThickness:20}]
    },
    options: {
      indexAxis:'y', maintainAspectRatio:false,
      plugins: {legend:{display:false}, tooltip:{callbacks:{label:c=>labels[c.dataIndex]}}},
      scales: {
        x:{ticks:{color:'#a7b4bb'}, grid:{color:'#34424a'}},
        y:{ticks:{color:'#eef2f2'}, grid:{display:false}}
      }
    }
  });
  $('chart').setAttribute('aria-label', labels.join('; '));
}
for(const name of ['All','Phantom','Vandal','Operator','Sheriff','Knife','Rifle','Pistol']){const b=document.createElement('button');b.textContent=name;b.setAttribute('aria-pressed',name===category);b.onclick=()=>{category=name;for(const c of $('filters').children)c.setAttribute('aria-pressed',c===b);renderGrid()};$('filters').append(b)}
$('search').oninput=renderGrid;$('weapon').onchange=renderGrid;$('sort').onchange=renderGrid;$('price-filter').onchange=renderGrid;$('refresh').onclick=()=>loadInventory(true);$('retry').onclick=()=>{nextRetry=0;ready?loadInventory(true):pollStatus()};$('detect').onclick=pollStatus;
$('grid').onclick=e=>{const card=e.target.closest('[data-skin]');if(card)inspectSkin(card.dataset.skin)};
$('grid').onpointermove=e=>{if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;const card=e.target.closest('[data-skin]');if(card){const r=card.getBoundingClientRect();card.style.setProperty('--reflection',(100+40*(e.clientX-r.left)/r.width)+'deg')}};
$('close-dialog').onclick=()=>$('skin-dialog').close();
$('skin-dialog').onclick=e=>{if(e.target===$('skin-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close()}};
for(const [id,compact] of [['view-large',false],['view-compact',true]])$(id).onclick=()=>{$('grid').classList.toggle('compact',compact);$('view-large').setAttribute('aria-pressed',!compact);$('view-compact').setAttribute('aria-pressed',compact)};
for(const a of document.querySelectorAll('.nav a'))a.onclick=()=>{for(const n of document.querySelectorAll('.nav a'))n.classList.toggle('active',n===a)};
document.addEventListener('error',e=>{if(e.target.tagName==='IMG'){const label=document.createElement('span');label.className='muted';label.textContent='Image indisponible';e.target.replaceWith(label)}},true);
document.addEventListener('DOMContentLoaded',()=>{window.lucide?.createIcons();$('login').addEventListener('click',signIn);pollStatus();setInterval(pollStatus,2000)});
</script></body></html>'''

app = Flask(__name__)
ORIGINS = {'http://localhost:8888', 'http://127.0.0.1:8888'}
CORS(app, resources={r'/api/*': {'origins': list(ORIGINS)}})
VP_UUID = '85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741'
SKIN_TYPE = 'e7c63390-eda7-46e0-bb7a-a6abdacd2433'
SHARDS = {'eu', 'na', 'ap', 'kr', 'pbe'}
PLATFORM = 'ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9'
VP_PACKS = ((475, 5), (1000, 10), (2050, 20), (3650, 35), (5350, 50), (11000, 100))
_inventory_cache = None
_cache_timestamp = 0
CACHE_DURATION = 300
_state_lock = threading.RLock()
_pipeline_lock = threading.Lock()
_state = {'status': 'waiting', 'session': None}
EXPORT_DIR = Path(__file__).resolve().parent / 'exports'
_credentials = None
_session_expiry = 0.0
_stop = threading.Event()


class ToolError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def get_lockfile():
    local = os.environ.get('LOCALAPPDATA')
    if not local:
        return None
    try:
        raw = (Path(local) / 'Riot Games/Riot Client/Config/lockfile').read_text(encoding='utf-8')
        name, pid, port, password, protocol = raw.strip().split(':')
        if protocol != 'https' or not password or not 1 <= int(port) <= 65535:
            return None
        return dict(name=name, pid=int(pid), port=int(port), password=password, protocol=protocol)
    except (OSError, ValueError, UnicodeError):
        return None


def get_local_headers(lockfile):
    token = base64.b64encode(('riot:' + lockfile['password']).encode()).decode()
    return {'Authorization': 'Basic ' + token}


def fetch_json(url, headers=None, local=False, method='GET'):
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.request(method, url, headers=headers, verify=not local,
                                   **({'json': {}} if method == 'POST' else {}),
                                   timeout=(2, 3) if local else (8, 25), allow_redirects=False)
            if response.status_code in (401, 403):
                raise ToolError('Riot session denied or expired. Sign in again.', 401)
            if response.status_code == 429:
                raise ToolError('Too many requests. Wait a minute before trying again.', 429)
            if response.status_code != 200:
                raise ToolError('An API replied with HTTP %s. Try again shortly.' % response.status_code)
            data = response.json()
            if not isinstance(data, dict):
                raise ToolError('Unexpected API response.')
            return data
    except requests.exceptions.SSLError:
        raise ToolError('Invalid remote HTTPS certificate. Check the system date and connection.') from None
    except (requests.RequestException, ValueError):
        raise ToolError('Cannot reach the API. Check your internet connection.') from None


def get_tokens(lockfile):
    data = fetch_json('https://localhost:%s/entitlements/v1/token' % lockfile['port'],
                      get_local_headers(lockfile), local=True)
    if not all(data.get(k) for k in ('accessToken', 'token', 'subject')):
        raise ToolError('The Riot account connection is still in progress.', 503)
    return data['accessToken'], data['token'], data['subject']


def external_sessions(port, headers):
    return fetch_json('https://localhost:%s/product-session/v1/external-sessions' % port, headers, local=True)


def valorant_sessions(sessions):
    return [s for s in sessions.values() if isinstance(s, dict) and
            (s.get('productId') == 'valorant' or
             'valorant' in str(s.get('launchConfiguration', {}).get('executable', '')).lower())]


def parse_region(sessions):
    region, shard = 'eu', 'eu'
    for session in valorant_sessions(sessions):
        args = session.get('launchConfiguration', {}).get('arguments', [])
        text = ' '.join(args) if isinstance(args, list) else str(args)
        for key in ('region', 'shard'):
            match = re.search(r'--' + key + r'(?:=|\s+)["\']?([a-zA-Z0-9]+)', text)
            if match:
                if key == 'region':
                    region = match[1].lower()
                else:
                    shard = match[1].lower()
        if not re.search(r'--shard(?:=|\s+)', text):
            shard = {'br': 'na', 'latam': 'na'}.get(region, region)
    return region, shard if shard in SHARDS else 'eu'


def get_region(port, headers):
    return parse_region(external_sessions(port, headers))


def _credentials_from_lockfile(lockfile):
    headers = get_local_headers(lockfile)
    sessions = external_sessions(lockfile['port'], headers)
    active_valorant = bool(valorant_sessions(sessions))
    region, shard = parse_region(sessions) if active_valorant else ('eu', 'eu')
    access, entitlement, puuid = get_tokens(lockfile)
    key = hashlib.sha256((lockfile['password'] + puuid + shard).encode()).hexdigest()[:24]
    return (key, access, entitlement, puuid, region, shard), active_valorant


AUTH_ERROR_STATUS = {'refused': 403, 'unavailable': 503, 'cancelled': 503}


def detect_riot_credentials(interactive=False):
    global _session_expiry
    lockfile = get_lockfile()
    if lockfile:
        try:
            result = _credentials_from_lockfile(lockfile)
            _session_expiry = 0.0
            return result
        except ToolError:
            pass
    for visible in ((False, True) if interactive else (False,)):
        try:
            credentials = riot_auth.authenticate(visible)
        except riot_auth.AuthError as error:
            if error.kind in AUTH_ERROR_STATUS:
                raise ToolError(str(error), AUTH_ERROR_STATUS[error.kind]) from None
            continue
        _session_expiry = credentials.expires_at
        return ((credentials.key, credentials.access_token, credentials.entitlements_token,
                 credentials.puuid, credentials.region, credentials.shard), False)
    raise ToolError('Riot session expired. Click Sign in to Riot.', 401)


@lru_cache(maxsize=1)
def get_client_version():
    data = fetch_json('https://valorant-api.com/v1/version')
    version = data.get('data', {}).get('riotClientVersion')
    if not version:
        raise ToolError('Valorant client version unavailable.')
    return version


def get_base_headers(access_token, entitlement_token):
    return {'Authorization': 'Bearer ' + access_token,
            'X-Riot-Entitlements-JWT': entitlement_token,
            'X-Riot-ClientPlatform': PLATFORM,
            'X-Riot-ClientVersion': get_client_version(),
            'User-Agent': 'ShooterGame/13 Windows/10.0.19043.1.256.64bit'}


def pd_url(shard, path):
    if shard not in SHARDS:
        raise ToolError('Unknown Riot shard.', 400)
    return 'https://pd.%s.a.pvp.net%s' % (shard, path)


def get_inventory(puuid, shard, headers):
    if not re.fullmatch(r'[0-9a-fA-F-]{36}', puuid):
        raise ToolError('Invalid Riot session id.')
    data = fetch_json(pd_url(shard, '/store/v1/entitlements/%s/%s' % (puuid, SKIN_TYPE)), headers)
    if not isinstance(data.get('Entitlements'), list):
        raise ToolError('The Riot API did not return the skin list.')
    return list(dict.fromkeys(item['ItemID'].lower() for item in data['Entitlements'] if item.get('ItemID')))


def parse_store_prices(data):
    """Only single-skin, undiscounted VP offers; never a bundle total."""
    prices = {}
    def add_offer(offer):
        price = offer.get('Cost', {}).get(VP_UUID)
        rewards = offer.get('Rewards', [])
        if (type(price) is int and price > 0 and len(rewards) == 1
                and rewards[0].get('ItemTypeID') == SKIN_TYPE
                and not offer.get('WholesaleOnly')):
            item_id = rewards[0].get('ItemID')
            if item_id:
                prices[item_id.lower()] = price
    for offer in data.get('SkinsPanelLayout', {}).get('SingleItemStoreOffers', []):
        add_offer(offer)
    featured = data.get('FeaturedBundle', {})
    for bundle in [featured.get('Bundle') or {}] + featured.get('Bundles', []):
        for entry in bundle.get('ItemOffers', []):
            add_offer(entry.get('Offer') or {})
        for entry in bundle.get('Items', []):
            item = entry.get('Item', {})
            price = entry.get('BasePrice')
            if (entry.get('CurrencyID') == VP_UUID and item.get('ItemTypeID') == SKIN_TYPE
                    and type(price) is int and price > 0 and item.get('ItemID')):
                prices[item['ItemID'].lower()] = price
    for entry in (data.get('BonusStore') or {}).get('BonusStoreOffers', []):
        add_offer(entry.get('Offer') or {})
    def plugins(offers):
        for offer in offers:
            add_offer(offer.get('PurchaseInformation') or {})
            plugins(offer.get('SubOffers') or [])
    for plugin in data.get('PluginStores', []):
        plugins((plugin.get('PluginOffers') or {}).get('StoreOffers', []))
    return prices


def get_skin_prices(shard, headers, puuid=None):
    if not puuid:
        raise ToolError('A session is required to read the store.', 503)
    data = fetch_json(pd_url(shard, '/store/v3/storefront/' + puuid), headers, method='POST')
    if 'SkinsPanelLayout' not in data:
        raise ToolError('The Riot store is unavailable.')
    return parse_store_prices(data)


def normalized_name(value):
    value = unicodedata.normalize('NFKD', value.replace('Ø', 'O').replace('ø', 'o'))
    return ''.join(c for c in value.casefold() if c.isalnum())


class PublicSkinPage(HTMLParser):
    """Read labeled info rows and exact-name links, without executing page scripts."""
    def __init__(self):
        super().__init__()
        self.links, self.rows, self.title = {}, {}, ''
        self.div_depth = 0
        self.row_depth = None
        self.row_text = []
        self.row_vp = False
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('title') and attrs.get('href', '').startswith('/weapons/'):
            self.links[normalized_name(attrs['title'])] = attrs['href']
        if tag == 'h1':
            self.in_title = True
        if tag == 'div':
            self.div_depth += 1
            if self.row_depth is None and attrs.get('class') == 'd-flex':
                self.row_depth = self.div_depth
                self.row_text, self.row_vp = [], False
        if tag == 'img' and self.row_depth is not None and attrs.get('src', '').endswith('/vp.webp'):
            self.row_vp = True

    def handle_data(self, text):
        if self.in_title:
            self.title += text
        if self.row_depth is not None and text.strip():
            self.row_text.append(text.strip())

    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_title = False
        if tag == 'div':
            if self.row_depth == self.div_depth:
                if self.row_text:
                    self.rows[self.row_text[0].rstrip(':')] = (' '.join(self.row_text[1:]), self.row_vp)
                self.row_depth = None
            self.div_depth = max(0, self.div_depth - 1)


@lru_cache(maxsize=1600)
def public_skin_page(path):
    if not re.fullmatch(r'/weapons/[a-z0-9/-]+', path):
        raise ToolError('Invalid catalog address.')
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.get('https://valorantinfo.com' + path, timeout=(5, 12), allow_redirects=False)
            if response.status_code != 200:
                raise ToolError('Public price page unavailable.')
        parser = PublicSkinPage()
        parser.feed(response.text)
        return parser
    except requests.RequestException:
        raise ToolError('Public catalog temporarily unreachable.') from None


def lookup_public_price(skin):
    reference = reference_price(skin['name'])
    if reference:
        return reference
    weapon = 'melee' if skin['weapon'] == 'Couteau' else skin['weapon'].lower()
    try:
        index = public_skin_page('/weapons/' + weapon)
        path = index.links.get(normalized_name(skin['name']))
        if not path:
            return {}
        page = public_skin_page(path)
        if normalized_name(page.title) != normalized_name(skin['name']):
            return {}
        result = {'source_url': 'https://valorantinfo.com' + path,
                  'collection': page.rows.get('Collection', ('', False))[0]}
        if page.rows.get('Battlepass', ('', False))[0].startswith('Yes'):
            return dict(result, acquisition='battlepass')
        if page.rows.get('Contract', ('', False))[0].startswith('Yes'):
            return dict(result, acquisition='contract')
        value, is_vp = page.rows.get('Price', ('', False))
        digits = value.replace(',', '').replace(' ', '').replace('\xa0', '')
        if is_vp and digits.isdigit() and 0 < int(digits) < 30000:
            return dict(result, price_vp=int(digits), price_source='public_catalog')
        return result
    except ToolError:
        return {}


def reference_price(name):
    references = [
        (['Blackthorn Classic', 'Blackthorn Guardian', 'Blackthorn Marshal', 'Blackthorn Vandal'],
         2175, 'Blackthorn', 'https://valorant.fandom.com/wiki/Blackthorn_Collection'),
        (['Blackthorn Blades'], 4350, 'Blackthorn', 'https://valorant.fandom.com/wiki/Blackthorn_Collection'),
        (['Araxys Bio-Atomizers'], 5350, 'Araxys', 'https://dotesports.com/valorant/news/how-much-every-skin-valorant'),
        (['RGX 11z Pro Karambit'], 4350, 'RGX 11z Pro', 'https://bracketseason.com/news/valorant-knife-skins-comprehensive/'),
        (['Reaver Ghost'], 1775, 'Reaver', 'https://valorantstrike.com/valorant-reaver-2-collection/valorant-reaver-2-ghost/'),
        (['Kuronami Ghost', 'Kuronami Phantom', 'Kuronami Guardian', 'Kuronami Operator'],
         2375, 'Kuronami', 'https://games.oneone.com/newsletters/valorant-kuronami-2.0-bundle'),
        (['Radiant Entertainment System Phantom', 'Radiant Entertainment System Bulldog',
          'Radiant Entertainment System Ghost', 'Radiant Entertainment System Operator'],
         2975, 'Radiant Entertainment System', 'https://valorant.fandom.com/wiki/Radiant_Entertainment_System_Collection'),
    ]
    if normalized_name(name) == normalized_name('VCT 2026 Sigil'):
        return {'acquisition': 'bundle_only', 'bundle_price_vp': 5550, 'collection': 'VCT 2026 Season',
                'price_vp': 5350, 'price_source': 'reference', 'reference_date': '2026-09-09',
                'source_url': 'https://valorant.fandom.com/wiki/VCT_2026_Season_Capsule'}
    for names, price, collection, source in references:
        if normalized_name(name) in [normalized_name(n) for n in names]:
            return {'price_vp': price, 'price_source': 'reference', 'collection': collection,
                    'source_url': source, 'reference_date': '2026-09-09'}
    return {}


def get_all_skins_data():
    skins = fetch_json('https://valorant-api.com/v1/weapons/skins').get('data')
    weapons = fetch_json('https://valorant-api.com/v1/weapons').get('data')
    if not isinstance(skins, list) or not isinstance(weapons, list):
        raise ToolError('The skin catalog is unavailable.')
    weapon_map = {}
    for weapon in weapons:
        name = 'Knife' if weapon.get('category') == 'EEquippableCategory::Melee' else weapon.get('displayName', 'Other')
        for skin in weapon.get('skins', []):
            weapon_map[skin['uuid']] = name
    rewards = {}
    try:
        for contract in fetch_json('https://valorant-api.com/v1/contracts').get('data', []):
            content = contract.get('content') or {}
            relation = content.get('relationType')
            if relation not in ('Season', 'Agent'):
                continue
            for chapter in content.get('chapters', []):
                chapter_rewards = [level.get('reward') or {} for level in chapter.get('levels', [])]
                chapter_rewards += chapter.get('freeRewards') or []
                for reward in chapter_rewards:
                    if reward.get('type') == 'EquippableSkinLevel':
                        rewards[reward['uuid'].lower()] = 'battlepass' if relation == 'Season' else 'contract'
    except ToolError:
        pass
    tiers = {'0cebb8be-46d7-c12a-d306-e9907bfc5a25': 'Deluxe',
             'e046854e-406c-37f4-6607-19a9ba8426fc': 'Exclusive',
             '60bca009-4182-7998-dee7-b8a2558dc369': 'Premium',
             '12683d76-48d7-84a3-4e09-6985794f0445': 'Select',
             '411e4a55-4e59-7757-41f0-86a53f101bb5': 'Ultra'}
    result = {}
    for skin in skins:
        levels = skin.get('levels') or []
        if not levels:
            continue
        chromas = skin.get('chromas') or [{}]
        icon = skin.get('displayIcon') or levels[0].get('displayIcon') or chromas[0].get('fullRender')
        if not isinstance(icon, str) or not icon.startswith('https://media.valorant-api.com/'):
            icon = None
        result[levels[0]['uuid'].lower()] = {'name': skin.get('displayName', 'Unknown skin'),
            'weapon': weapon_map.get(skin['uuid'], 'Other'), 'icon': icon,
            'acquisition': rewards.get(levels[0]['uuid'].lower(), 'unknown'),
            'tier': tiers.get(skin.get('contentTierUuid'), 'Standard'),
            'level_uuids': [level['uuid'].lower() for level in levels]}
    return result


def vp_to_eur(vp):
    pack_vp, pack_eur = min(VP_PACKS, key=lambda p: abs(p[0] - vp))
    return round(vp * pack_eur / pack_vp, 2)


def _monitor_tick(now=None):
    global _credentials, _inventory_cache, _cache_timestamp, _session_expiry
    now = time.time() if now is None else now
    lockfile = get_lockfile()
    credentials = None
    if lockfile:
        with _state_lock:
            if _state['status'] != 'ready':
                _state.update({'status': 'loading', 'session': None})
        try:
            credentials, _ = _credentials_from_lockfile(lockfile)
        except Exception:
            credentials = None
    with _state_lock:
        if credentials is None and _credentials is not None and now < _session_expiry - 60:
            return
        state = ({'status': 'ready', 'session': credentials[0]} if credentials
                 else {'status': 'needs_login', 'session': None})
        if state['session'] != _state['session']:
            _inventory_cache = None
            _cache_timestamp = 0
        _state.update(state)
        _credentials = credentials
        if credentials is None:
            _session_expiry = 0.0


def monitor_valorant():
    while not _stop.is_set():
        try:
            _monitor_tick()
        except Exception:
            pass
        _stop.wait(2)


def build_inventory(refresh=False):
    global _inventory_cache, _cache_timestamp
    with _pipeline_lock:
        with _state_lock:
            credentials = _credentials
            if not credentials or _state['status'] != 'ready':
                raise ToolError('No Riot session yet, or the connection is in progress.', 503)
            if refresh:
                _inventory_cache = None
                _cache_timestamp = 0
                get_client_version.cache_clear()
                public_skin_page.cache_clear()
            if _inventory_cache is not None and time.monotonic() - _cache_timestamp < CACHE_DURATION:
                return _inventory_cache
        key, access, entitlement, puuid, region, shard = credentials
        headers = get_base_headers(access, entitlement)
        owned = get_inventory(puuid, shard, headers)
        catalog = get_all_skins_data()
        base_by_level = {level: base for base, skin in catalog.items()
                         for level in skin.get('level_uuids', [base])}
        owned = list(dict.fromkeys(base_by_level.get(uuid, uuid) for uuid in owned))
        warnings = []
        try:
            prices = get_skin_prices(shard, headers, puuid)
        except ToolError as error:
            if error.status == 401:
                raise
            prices = {}
            warnings.append('Riot store unavailable; public catalog prices used where available.')
        candidates = [uuid for uuid in owned if uuid in catalog and uuid not in prices
                      and catalog[uuid].get('acquisition', 'unknown') == 'unknown']
        with ThreadPoolExecutor(max_workers=4) as executor:
            public_prices = dict(zip(candidates, executor.map(lookup_public_price, (catalog[u] for u in candidates))))
        skins = []
        for uuid in owned:
            skin = catalog.get(uuid, {'name': 'Unlisted skin (' + uuid[:8] + ')', 'weapon': 'Other', 'icon': None})
            public = public_prices.get(uuid, {})
            acquisition = public.get('acquisition', skin.get('acquisition', 'unknown'))
            price = prices.get(uuid, public.get('price_vp'))
            skins.append({'uuid': uuid, 'name': skin['name'], 'weapon': skin['weapon'],
                          'price_vp': price, 'price_eur': vp_to_eur(price) if price is not None else None,
                          'price_source': 'riot_store' if uuid in prices else public.get('price_source', 'unavailable'),
                          'source_url': public.get('source_url'), 'acquisition': acquisition,
                          'collection': public.get('collection', ''), 'tier': skin.get('tier', 'Standard'),
                          'bundle_price_vp': public.get('bundle_price_vp'),
                          'reference_date': public.get('reference_date'),
                          'image_url': skin['icon']})
        skins.sort(key=lambda s: (s['price_vp'] is None, -(s['price_vp'] or 0), s['name']))
        priced = [s for s in skins if s['price_vp'] is not None]
        non_retail = sum(s['acquisition'] in ('battlepass', 'contract', 'bundle_only') and s['price_vp'] is None for s in skins)
        best = dict(priced[0], image=priced[0]['image_url']) if priced else None
        data = {'player': {'puuid': puuid, 'region': region, 'shard': shard},
                'summary': {'total_vp': sum(s['price_vp'] for s in priced) if priced or not skins else None,
                            'total_eur': round(sum(s['price_eur'] for s in priced), 2) if priced or not skins else None,
                            'skin_count': len(skins), 'unpriced_count': len(skins) - len(priced),
                            'non_retail_count': non_retail,
                            'battlepass_count': sum(s['acquisition'] == 'battlepass' for s in skins),
                            'bundle_only_count': sum(s['acquisition'] == 'bundle_only' for s in skins),
                            'unknown_count': len(skins) - len(priced) - non_retail,
                            'priced_count': len(priced),
                            'riot_price_count': sum(s['price_source'] == 'riot_store' for s in priced),
                            'catalog_price_count': sum(s['price_source'] in ('public_catalog', 'reference') for s in priced),
                            'most_expensive': best},
                'skins': skins, 'warnings': warnings, 'updated_at': datetime.now(timezone.utc).isoformat()}
        with _state_lock:
            if _state['session'] != key or _state['status'] != 'ready':
                raise ToolError('The Riot session changed. Detecting again.', 409)
            _inventory_cache = data
            _cache_timestamp = time.monotonic()
        return data


def write_inventory_csv(data, path):
    columns = ['name', 'weapon', 'tier', 'price_vp', 'price_eur', 'price_source',
               'acquisition', 'collection', 'uuid', 'source_url', 'image_url']
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data.get('skins', []))


def save_inventory():
    global _credentials, _inventory_cache, _cache_timestamp
    credentials, active_valorant = detect_riot_credentials(interactive=True)
    with _state_lock:
        _credentials = credentials
        _inventory_cache = None
        _cache_timestamp = 0
        _state.update({'status': 'ready', 'session': credentials[0]})
    data = build_inventory(refresh=True)
    EXPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    base = EXPORT_DIR / ('valorant-inventory-' + stamp)
    json_path = base.with_suffix('.json')
    csv_path = base.with_suffix('.csv')
    with json_path.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    write_inventory_csv(data, csv_path)
    return data, json_path, csv_path, active_valorant


@app.before_request
def restrict_local_access():
    if request.host not in {'localhost:8888', '127.0.0.1:8888'}:
        return jsonify(error='Local host required.'), 403
    if request.headers.get('Origin') and request.headers['Origin'] not in ORIGINS:
        return jsonify(error='Origin not allowed.'), 403
    if request.headers.get('Sec-Fetch-Site') == 'cross-site':
        return jsonify(error='External request refused.'), 403


@app.after_request
def response_headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline'; img-src https://media.valorant-api.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
    return response


@app.errorhandler(ToolError)
def tool_error(error):
    return jsonify(error=str(error)), error.status


@app.errorhandler(500)
def internal_error(error):
    return jsonify(error='Internal error while reading the inventory. Restart the tool.'), 500


@app.get('/')
def index():
    return HTML_TEMPLATE


@app.get('/api/status')
def status():
    with _state_lock:
        return jsonify(dict(_state))


@app.get('/api/inventory')
def inventory():
    return jsonify(build_inventory())


@app.get('/api/refresh')
def refresh():
    return jsonify(build_inventory(refresh=True))


@app.post('/api/login')
def login():
    global _credentials, _inventory_cache, _cache_timestamp
    if not _pipeline_lock.acquire(blocking=False):
        raise ToolError('A sign-in is already in progress.', 409)
    try:
        credentials, _ = detect_riot_credentials(interactive=True)
    finally:
        _pipeline_lock.release()
    with _state_lock:
        _credentials = credentials
        _inventory_cache = None
        _cache_timestamp = 0
        _state.update({'status': 'ready', 'session': credentials[0]})
    return jsonify(status='ready')


@app.post('/api/logout')
def logout():
    global _credentials, _inventory_cache, _cache_timestamp
    riot_auth.logout()
    with _state_lock:
        _credentials = None
        _inventory_cache = None
        _cache_timestamp = 0
        _state.update({'status': 'waiting', 'session': None})
    return jsonify(status='waiting')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Local Valorant inventory')
    parser.add_argument('--save-inventory', action='store_true',
                        help='save the inventory without opening the web interface')
    parser.add_argument('--logout', action='store_true',
                        help='forget the saved Riot session')
    args = parser.parse_args()
    print('\nValorant Inventory Tool\n' + '=' * 40)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    if args.logout:
        riot_auth.logout()
        print('Riot session forgotten.')
        raise SystemExit(0)
    if args.save_inventory:
        try:
            data, json_path, csv_path, active_valorant = save_inventory()
        except ToolError as error:
            print('Export failed: %s' % error)
            print('Sign in to your Riot account in the window that opens.')
            input('Press Enter to quit...')
            raise SystemExit(1)
        print('Inventory saved.')
        print('Session source: ' + ('Riot Client' if active_valorant else 'Riot account'))
        print('Account: %s / shard %s' % (data['player']['region'], data['player']['shard']))
        print('Skins: %s' % data['summary']['skin_count'])
        print('Value: %s VP / %s EUR' % (data['summary']['total_vp'], data['summary']['total_eur']))
        print('JSON: %s' % json_path)
        print('CSV:  %s' % csv_path)
        input('Press Enter to quit...')
        raise SystemExit(0)
    try:
        server = make_server('127.0.0.1', 8888, app, threaded=True)
    except (OSError, SystemExit):
        print('Port 8888 is unavailable. Close the other instance or the program using it.')
        input('Press Enter to quit...')
        raise SystemExit(1)
    threading.Thread(target=monitor_valorant, daemon=True).start()

    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:8888')

    threading.Thread(target=open_browser, daemon=True).start()
    print('Server started on http://localhost:8888')
    print('Opening the browser...\nDetecting the Riot session...')
    print('Sign in to your Riot account from the page.\n(Ctrl+C to quit)\n' + '=' * 40)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _stop.set()
        server.server_close()
