"""Path 03 — Launch a Demo UI."""
import random
import datetime
import os
import streamlit as st
from modules.config import FAST_DEMO_CITIES, FAST_DEMO_STATION_COUNT, __version__
from modules.utilities import get_themed_logo_base64, get_transparent_product_base64


def render():
    """Render Path 03 UI: Launch a Demo card."""
st.markdown(f"""
<div class="path-card" style="--accent:#FFD700;">
    <span class="pc-icon">⚡</span>
    <div class="pc-tag">Path 03</div>
    <div class="pc-title">Launch a<br>Demo</div>
    <div class="pc-desc">Instantly spin up a fully pre-configured scenario for a major US city. Ideal for live stakeholder presentations and platform walkthroughs.</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

if st.button("⚡ Launch Random Demo City", width="stretch", key="demo_btn", help="Load a random US city with simulated 911 call data to demo the full DFR deployment workflow."):
    random.seed(datetime.datetime.now().microsecond + os.getpid())
    already_used = st.session_state.get('_last_demo_city', '')
    candidates = [c for c in FAST_DEMO_CITIES if c[0] != already_used]
    rcity, rstate = random.choice(candidates)
    st.session_state['_last_demo_city'] = rcity
    st.session_state['target_cities'] = [{"city": rcity, "state": rstate}]
    st.session_state.city_count = 1
    for i in range(10):
        st.session_state.pop(f"c_{i}", None)
        st.session_state.pop(f"s_{i}", None)
    st.session_state['trigger_sim'] = True
    st.session_state['demo_mode_used'] = True
    st.rerun()

city_chips = "  ·  ".join([f"{c}" for c, _ in FAST_DEMO_CITIES])
st.markdown(f"""
<div class="demo-cities">
    <b>Available Cities</b><br>
    {city_chips}
</div>
<div class="demo-check">
    <span>✓</span>Real Census boundaries<br>
    <span>✓</span>Clustered 911 simulation<br>
    <span>✓</span>{FAST_DEMO_STATION_COUNT} preloaded station candidates<br>
    <span>✓</span>Full optimization & export
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align:center; margin-top:8px;">
<div style="font-family:'IBM Plex Mono',monospace; font-size:0.68rem; letter-spacing:0.08em; color:#4b5563; margin-bottom:8px;">
    © v {__version__}
</div>
<div style="font-size:0.63rem; color:#2a2a2a;">
    BRINC Drones, Inc. · <a href="https://brincdrones.com" target="_blank"
    style="color:#333; text-decoration:none;">brincdrones.com</a>
    · All coverage estimates are for planning purposes only.
</div>
</div>
""", unsafe_allow_html=True)
_live_admin_dashboard_fragment()
_render_in_app_faq()

if submit_demo or st.session_state.get('trigger_sim', False):
if st.session_state.get('trigger_sim', False):
    st.session_state['trigger_sim'] = False
    # trigger_sim is set by the demo button — mark accordingly
    if not st.session_state.get('demo_mode_used', False):
        st.session_state['demo_mode_used'] = True

active_targets = [
    {
        'city': str(loc.get('city', '') or '').strip(),
        'state': str(loc.get('state', '') or '').strip().upper(),
    }
    for loc in st.session_state['target_cities']
    if (
        str(loc.get('city', '') or '').strip()
        or (
            st.session_state.get('highway_patrol_mode', False)
            and str(loc.get('state', '') or '').strip().upper() in STATE_FIPS
        )
    )
]
if not active_targets:
    _pre_sim_station_file, _, _ = split_simulation_optional_files(
        st.session_state.get('sim_optional_uploader') or [],
        _is_boundary_sidecar,
        _looks_like_stations,
    )
    if _pre_sim_station_file is not None:
        _inferred_targets, _inferred_notice = infer_simulation_targets_from_station_file(
            _pre_sim_station_file,
            forward_geocode,
            reverse_geocode_state,
            US_STATES_ABBR,
            default_state=st.session_state.get('active_state', ''),
        )
        if _inferred_targets:
            active_targets = _inferred_targets
            st.session_state['target_cities'] = list(_inferred_targets)
            st.session_state['active_city'] = _inferred_targets[0]['city']
            st.session_state['active_state'] = _inferred_targets[0]['state']
            if _inferred_notice:
                st.toast(_inferred_notice)
if not active_targets:
    st.error("Please enter at least one valid city, county, or state.")
    st.stop()

_abbr_to_full = {abbr: name for name, abbr in US_STATES_ABBR.items()}
if len(active_targets) == 1:
    _target_city = str(active_targets[0]['city']).title()
    if not _target_city:
        _target_city = _abbr_to_full.get(active_targets[0]['state'], active_targets[0]['state'])
    st.session_state['active_city']  = _target_city
    st.session_state['active_state'] = active_targets[0]['state']
else:
    _target_city = str(active_targets[0]['city']).title()
    if not _target_city:
        _target_city = _abbr_to_full.get(active_targets[0]['state'], active_targets[0]['state'])
    st.session_state['active_city']  = f"{_target_city} & {len(active_targets)-1} others"
    st.session_state['active_state'] = active_targets[0]['state']

# ── Fetch real population for upload path ─────────────────────────────
try:
    _upload_pop = 0
    for _t in active_targets:
        _fips = STATE_FIPS.get(_t.get('state', ''), '')
        if _fips:
            _p = fetch_census_population(_fips, _t.get('city', ''))
            if _p:
                _upload_pop += _p
    if _upload_pop > 0:
        st.session_state['estimated_pop'] = _upload_pop
except Exception:
    pass

# ── Flight-path loading overlay ───────────────────────────────────────
_swarm_city = st.session_state.get('active_city', 'Jurisdiction') if active_targets else "Jurisdiction"
_swarm_logo_b64 = get_themed_logo_base64("logo.png", theme="dark") or ""
_swarm_gigs_b64 = get_transparent_product_base64("gigs.png") or ""
_swarm_city_js  = _swarm_city.upper().replace('"', '').replace("'", '')
_swarm_state_js = str(active_targets[0].get('state', 'US')).upper().replace('"', '').replace("'", '') if active_targets else "US"
_swarm_map_svg = '<svg id="fl-svg" viewBox="0 0 600 360" xmlns="http://www.w3.org/2000/svg"></svg>'
try:
    _swarm_map_svg = Path('usa.svg').read_text(encoding='utf-8')
    _swarm_map_svg = re.sub(r'^\s*<\?xml[^>]*>\s*', '', _swarm_map_svg, count=1)
    _swarm_map_svg = re.sub(r'^\s*<!--.*?-->\s*', '', _swarm_map_svg, count=1, flags=re.S)
    _swarm_map_svg = re.sub(r'<svg\b', '<svg id="fl-svg" class="fl-us-map" preserveAspectRatio="xMidYMid meet"', _swarm_map_svg, count=1)
except Exception:
    pass
_swarm_overlay_html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;overflow:hidden}}
#flo{{
  position:fixed;top:0;left:0;width:100vw;height:100vh;
  background:rgba(4,7,16,0.97);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  z-index:2147483647;font-family:'IBM Plex Mono',monospace;
}}
.fl-panels{{display:flex;align-items:center;justify-content:center;width:100%;max-width:940px;gap:24px;padding:0 24px}}
.fl-side{{width:150px;flex-shrink:0;display:flex;align-items:center;justify-content:center}}
.fl-side img{{max-width:140px;max-height:90px;object-fit:contain;opacity:0.92}}
.fl-map{{flex:1;min-width:0}}
.fl-map svg{{width:100%;height:auto;display:block}}
.fl-footer{{margin-top:20px;text-align:center;max-width:760px;padding:0 18px}}
.fl-city{{font-size:20px;font-weight:900;letter-spacing:3px;color:#fff}}
.fl-stline{{font-size:10px;letter-spacing:2px;color:rgba(0,210,255,0.7);text-transform:uppercase;margin-top:7px}}
.fl-made{{margin-top:12px;font-size:11px;font-weight:800;letter-spacing:2.6px;color:rgba(255,255,255,0.92);text-transform:uppercase}}
.fl-copy{{margin-top:8px;font-size:11px;line-height:1.55;color:rgba(255,255,255,0.62)}}
.fl-tribute-tag{{margin-top:14px;font-size:10px;font-weight:700;letter-spacing:2.8px;color:rgba(255,255,255,0.72);text-transform:uppercase}}
.fl-tribute-line{{margin-top:7px;font-size:10px;line-height:1.5;color:rgba(255,255,255,0.5);min-height:15px;transition:opacity 0.5s ease}}
.fl-dots::after{{content:'';animation:dots 1.4s steps(4,end) infinite}}
@keyframes dots{{0%{{content:''}}25%{{content:'.'}}50%{{content:'..'}}75%{{content:'...'}}}}
</style>
</head><body>
<div id="flo">
  <div class="fl-panels">
    <div class="fl-side"><img src="data:image/png;base64,{_swarm_logo_b64}" alt="BRINC"></div>
    <div class="fl-map">
      {_swarm_map_svg}
    </div>
    <div class="fl-side"><img src="data:image/png;base64,{_swarm_gigs_b64}" alt="Fleet"></div>
  </div>
  <div class="fl-footer">
    <div class="fl-city">{_swarm_city_js}</div>
    <div class="fl-stline" id="fl-stl">DEPLOYING FLEET<span class="fl-dots"></span></div>
    <div class="fl-made">MADE IN THE USA</div>
    <div class="fl-copy">American-built drone infrastructure supporting domestic jobs, resilient supply chains, and the communities they protect.</div>
    <div class="fl-tribute-tag">ONE OCTOBER</div>
    <div class="fl-tribute-line" id="fl-tribute">For those we remember. For those we can still protect.</div>
  </div>
</div>
<script>
(function(){{
  var doc = parent.document;
  /* clean up any previous overlay + injected styles */
  var _old = doc.getElementById('brinc-flo');
  if(_old && _old.parentNode) _old.parentNode.removeChild(_old);
  var _olds = doc.getElementById('brinc-flo-css');
  if(_olds && _olds.parentNode) _olds.parentNode.removeChild(_olds);
  /* inject CSS into parent document — iframe <style> rules don't transfer on cloneNode */
  var _css = doc.createElement('style');
  _css.id = 'brinc-flo-css';
  _css.textContent =
    '#brinc-flo{{position:fixed!important;top:0!important;left:0!important;width:100vw!important;height:100vh!important;'
    +'background:rgba(4,7,16,0.97)!important;display:flex!important;flex-direction:column!important;'
    +'align-items:center!important;justify-content:center!important;'
    +'z-index:2147483647!important;font-family:"IBM Plex Mono",monospace!important}}'
    +'#brinc-flo .fl-panels{{display:flex;align-items:center;justify-content:center;width:100%;max-width:940px;gap:24px;padding:0 24px}}'
    +'#brinc-flo .fl-side{{width:150px;flex-shrink:0;display:flex;align-items:center;justify-content:center}}'
    +'#brinc-flo .fl-side img{{max-width:140px;max-height:90px;object-fit:contain;opacity:0.92}}'
    +'#brinc-flo .fl-map{{flex:1;min-width:0}}'
    +'#brinc-flo .fl-map svg{{width:100%;height:auto;display:block}}'
    +'#brinc-flo .fl-footer{{margin-top:20px;text-align:center;max-width:760px;padding:0 18px}}'
    +'#brinc-flo .fl-city{{font-size:20px;font-weight:900;letter-spacing:3px;color:#fff}}'
    +'#brinc-flo .fl-stline{{font-size:10px;letter-spacing:2px;color:rgba(0,210,255,0.7);text-transform:uppercase;margin-top:7px}}'
    +'#brinc-flo .fl-made{{margin-top:12px;font-size:11px;font-weight:800;letter-spacing:2.6px;color:rgba(255,255,255,0.92);text-transform:uppercase}}'
    +'#brinc-flo .fl-copy{{margin-top:8px;font-size:11px;line-height:1.55;color:rgba(255,255,255,0.62)}}'
    +'#brinc-flo .fl-tribute-tag{{margin-top:14px;font-size:10px;font-weight:700;letter-spacing:2.8px;color:rgba(255,255,255,0.72);text-transform:uppercase}}'
    +'#brinc-flo .fl-tribute-line{{margin-top:7px;font-size:10px;line-height:1.5;color:rgba(255,255,255,0.5);min-height:15px;transition:opacity 0.5s ease}}'
    +'#brinc-flo .fl-us-map{{width:100%;height:auto;display:block}}'
    +'#brinc-flo .fl-state{{fill:rgba(255,255,255,0.03);stroke:rgba(255,255,255,0.15);stroke-width:1.1;transition:fill .25s ease,stroke .25s ease,filter .25s ease}}'
    +'#brinc-flo .fl-state-active{{fill:rgba(0,210,255,0.18)!important;stroke:rgba(0,210,255,0.95)!important;stroke-width:2.1!important;filter:url(#brinc-state-glow)}}'
    +'#brinc-flo .fl-dots::after{{content:"";animation:brinc-flo-dots 1.4s steps(4,end) infinite}}'
    +'@keyframes brinc-flo-dots{{0%{{content:""}}25%{{content:"."}}50%{{content:".."}}75%{{content:"..."}}}}';
  (doc.head || doc.body).appendChild(_css);
  var el = document.getElementById('flo');
  var clone = el.cloneNode(true);
  clone.id = 'brinc-flo';
  doc.body.appendChild(clone);
  el.style.display = 'none';
  var P = doc.getElementById('brinc-flo');
  if(!P) return;
  var pStatus = P.querySelector('#fl-stl');
  var pTribute = P.querySelector('#fl-tribute');
  var TRIBUTES = [
    'For those we remember. For those we can still protect.',
    'In memory, and in service to lives still depending on time.',
    'Built for the moments when faster response can save a life.',
    'A quiet promise to protect more families, officers, and communities.'
  ];
  if(pTribute){{
    var tributeIdx = 0;
    parent.setInterval(function(){{
      tributeIdx = (tributeIdx + 1) % TRIBUTES.length;
      pTribute.style.opacity = '0';
      parent.setTimeout(function(){{
pTribute.textContent = TRIBUTES[tributeIdx];
pTribute.style.opacity = '1';
      }}, 260);
    }}, 4200);
  }}
  var mapSvg = P.querySelector('#fl-svg') || P.querySelector('svg');
  if(!mapSvg) return;
  mapSvg.setAttribute('id', 'fl-svg');
  var svgNS = mapSvg.namespaceURI || 'http://www.w3.org/2000/svg';
  var vb = (mapSvg.getAttribute('viewBox') || '0 0 600 360').trim().split(/\\s+/).map(Number);
  if(vb.length !== 4 || vb.some(function(v){{ return !isFinite(v); }})) vb = [0, 0, 600, 360];
  var vx = vb[0], vy = vb[1], vw = vb[2], vh = vb[3];
  var stateCode = '{_swarm_state_js}'.replace(/[^A-Z]/g, '');
  var stateId = stateCode ? 'US-' + stateCode : '';
  var statePaths = Array.from(mapSvg.querySelectorAll('path[id^="US-"]'));
  function addSvgEl(tag, attrs, parent){{
    var el = doc.createElementNS(svgNS, tag);
    Object.keys(attrs || {{}}).forEach(function(k){{ el.setAttribute(k, attrs[k]); }});
    if(parent) parent.appendChild(el);
    return el;
  }}
  var defs = mapSvg.querySelector('defs') || addSvgEl('defs', {{}}, mapSvg);
  var oldClip = mapSvg.querySelector('#brinc-us-clip');
  if(oldClip && oldClip.parentNode) oldClip.parentNode.removeChild(oldClip);
  var oldGlow = mapSvg.querySelector('#brinc-state-glow');
  if(oldGlow && oldGlow.parentNode) oldGlow.parentNode.removeChild(oldGlow);
  var clip = addSvgEl('clipPath', {{id:'brinc-us-clip'}}, defs);
  statePaths.forEach(function(path){{
    clip.appendChild(path.cloneNode(true));
    path.classList.add('fl-state');
  }});
  var glow = addSvgEl('filter', {{id:'brinc-state-glow', x:'-30%', y:'-30%', width:'160%', height:'160%'}}, defs);
  addSvgEl('feGaussianBlur', {{stdDeviation:'4.5', result:'blur'}}, glow);
  addSvgEl('feColorMatrix', {{type:'matrix', values:'0 0 0 0 0  0 0 0 0 0.82  0 0 0 0 1  0 0 0 0.9 0'}}, glow);
  var merge = addSvgEl('feMerge', {{}}, glow);
  addSvgEl('feMergeNode', {{in:'blur'}}, merge);
  addSvgEl('feMergeNode', {{in:'SourceGraphic'}}, merge);
  var flagLayer = mapSvg.querySelector('#brinc-flag-layer');
  if(flagLayer && flagLayer.parentNode) flagLayer.parentNode.removeChild(flagLayer);
  flagLayer = addSvgEl('g', {{id:'brinc-flag-layer', 'clip-path':'url(#brinc-us-clip)', opacity:'0.18'}}, mapSvg);
  mapSvg.insertBefore(flagLayer, mapSvg.firstChild);
  addSvgEl('rect', {{x:vx, y:vy, width:vw, height:vh, fill:'rgba(255,255,255,0.045)'}}, flagLayer);
  var stripeH = vh / 13;
  for (var si = 0; si < 13; si++) {{
    addSvgEl('rect', {{x:vx, y:(vy + si * stripeH), width:vw, height:stripeH, fill:(si % 2 === 0 ? 'rgba(191,10,48,0.55)' : 'rgba(255,255,255,0.05)')}}, flagLayer);
  }}
  var cantonW = vw * 0.42, cantonH = stripeH * 7;
  addSvgEl('rect', {{x:vx, y:vy, width:cantonW, height:cantonH, fill:'rgba(0,40,104,0.72)'}}, flagLayer);
  for (var row = 0; row < 4; row++) {{
    for (var col = 0; col < 5; col++) {{
      addSvgEl('circle', {{cx:(vx + 18 + col * (cantonW / 5.8)), cy:(vy + 16 + row * (cantonH / 4.7)), r:'2.1', fill:'rgba(255,255,255,0.78)'}}, flagLayer);
    }}
  }}
  var gridLayer = mapSvg.querySelector('#brinc-grid-layer');
  if(gridLayer && gridLayer.parentNode) gridLayer.parentNode.removeChild(gridLayer);
  gridLayer = addSvgEl('g', {{id:'brinc-grid-layer', opacity:'0.18'}}, mapSvg);
  mapSvg.insertBefore(gridLayer, flagLayer.nextSibling);
  for (var gy = 1; gy < 5; gy++) addSvgEl('line', {{x1:vx, y1:(vy + gy * vh / 5), x2:(vx + vw), y2:(vy + gy * vh / 5), stroke:'rgba(0,210,255,0.22)', 'stroke-width':'0.6'}}, gridLayer);
  for (var gx = 1; gx < 6; gx++) addSvgEl('line', {{x1:(vx + gx * vw / 6), y1:vy, x2:(vx + gx * vw / 6), y2:(vy + vh), stroke:'rgba(0,210,255,0.16)', 'stroke-width':'0.6'}}, gridLayer);
  var targetState = statePaths.find(function(path){{ return path.id === stateId; }}) || null;
  if(targetState) targetState.classList.add('fl-state-active');
  var arcLayer = mapSvg.querySelector('#fl-arc');
  if(arcLayer && arcLayer.parentNode) arcLayer.parentNode.removeChild(arcLayer);
  var dronesLayer = mapSvg.querySelector('#fl-drones');
  if(dronesLayer && dronesLayer.parentNode) dronesLayer.parentNode.removeChild(dronesLayer);
  var markerLayer = mapSvg.querySelector('#fl-markers');
  if(markerLayer && markerLayer.parentNode) markerLayer.parentNode.removeChild(markerLayer);
  var pArc = addSvgEl('path', {{id:'fl-arc', fill:'none', stroke:'rgba(0,210,255,0.26)', 'stroke-width':'1.8', 'stroke-dasharray':'5 4'}}, mapSvg);
  var pDrones = addSvgEl('g', {{id:'fl-drones'}}, mapSvg);
  var startX = vx + vw * 0.12;
  var startY = vy + vh * 0.28;
  var launchState = statePaths.find(function(path){{ return path.id === 'US-WA'; }}) || null;
  if(launchState) {{
    var launchBox = launchState.getBBox();
    startX = launchBox.x + launchBox.width * 0.30;
    startY = launchBox.y + launchBox.height * 0.36;
  }}
  var tx = vx + vw * 0.68;
  var ty = vy + vh * 0.48;
  if(targetState) {{
    var bbox = targetState.getBBox();
    tx = bbox.x + bbox.width / 2;
    ty = bbox.y + bbox.height / 2;
  }}
  tx = Math.max(vx + 18, Math.min(vx + vw - 18, tx));
  ty = Math.max(vy + 18, Math.min(vy + vh - 18, ty));
  var cpx = startX + (tx - startX) * 0.52;
  var cpy = Math.min(startY, ty) - vh * 0.18;
  pArc.setAttribute('d', 'M ' + startX + ',' + startY + ' Q ' + cpx + ',' + cpy + ' ' + tx + ',' + ty);
  function bPt(t,x0,y0,x1,y1,x2,y2){{
    var m=1-t; return [m*m*x0+2*m*t*x1+t*t*x2, m*m*y0+2*m*t*y1+t*t*y2];
  }}
  function bAng(t,x0,y0,x1,y1,x2,y2){{
    var m=1-t, dx=2*(m*(x1-x0)+t*(x2-x1)), dy=2*(m*(y1-y0)+t*(y2-y1));
    return Math.atan2(dy,dx)*180/Math.PI;
  }}
  function eio(t){{ return t<0.5?2*t*t:-1+(4-2*t)*t; }}
  var NS = svgNS;
  var NDRONES=4, STAGGER=1800, FLY=9000;
  var drones=[];
  function makeDrone(col){{
    var g=doc.createElementNS(NS,'g');
    var bg=doc.createElementNS(NS,'circle');
    bg.setAttribute('r','7'); bg.setAttribute('fill','rgba(0,210,255,0.08)');
    g.appendChild(bg);
    [[-3,-3,-8,-8],[3,-3,8,-8],[-3,3,-8,8],[3,3,8,8]].forEach(function(a){{
      var ln=doc.createElementNS(NS,'line');
      ln.setAttribute('x1',a[0]); ln.setAttribute('y1',a[1]);
      ln.setAttribute('x2',a[2]); ln.setAttribute('y2',a[3]);
      ln.setAttribute('stroke',col); ln.setAttribute('stroke-width','1.5');
      ln.setAttribute('stroke-linecap','round'); g.appendChild(ln);
    }});
    [[-8,-8],[8,-8],[-8,8],[8,8]].forEach(function(r){{
      var ci=doc.createElementNS(NS,'circle');
      ci.setAttribute('cx',r[0]); ci.setAttribute('cy',r[1]); ci.setAttribute('r','2.5');
      ci.setAttribute('stroke',col); ci.setAttribute('stroke-width','1');
      ci.setAttribute('fill','rgba(0,210,255,0.2)'); g.appendChild(ci);
    }});
    var rect=doc.createElementNS(NS,'rect');
    rect.setAttribute('x','-3'); rect.setAttribute('y','-3');
    rect.setAttribute('width','6'); rect.setAttribute('height','6');
    rect.setAttribute('rx','1'); rect.setAttribute('fill',col); g.appendChild(rect);
    return g;
  }}
  for(var i=0;i<NDRONES;i++){{
    var dEl=makeDrone('#00D2FF');
    pDrones.appendChild(dEl);
    drones.push({{el:dEl,arrived:false,delay:i*STAGGER,arrT:0}});
  }}
  var arrivedN=0, allDone=false, t0=null;
  var MSGS=['INITIALIZING MISSION BRIEF','FETCHING BOUNDARY DATA','MODELING 911 CALLS','OPTIMIZING STATION GRID','DEPLOYING FLEET'];
  var mi=0;
  function nextMsg(){{ if(mi<MSGS.length && pStatus) pStatus.innerHTML=MSGS[mi++]+'<span class="fl-dots"></span>'; }}
  /* All timers run in parent window context — they survive iframe replacement on Streamlit rerender */
  nextMsg(); parent.setInterval(nextMsg,3000);
  function frame(now){{
    if(!t0) t0=now;
    var elapsed=now-t0;
    drones.forEach(function(d,i){{
      var e=elapsed-d.delay;
      if(e<0){{ d.el.setAttribute('transform','translate('+startX+','+startY+')'); return; }}
      if(d.arrived){{
var ht=(now-d.arrT)/900;
var hx=tx+Math.cos(ht+i*1.6)*4, hy=ty+Math.sin(ht*1.3+i)*3-5;
d.el.setAttribute('transform','translate('+hx+','+hy+')'); return;
      }}
      var t=Math.min(e/FLY,1), te=eio(t);
      var pt=bPt(te,startX,startY,cpx,cpy,tx,ty);
      var ang=bAng(te,startX,startY,cpx,cpy,tx,ty);
      d.el.setAttribute('transform','translate('+pt[0]+','+pt[1]+') rotate('+ang+',0,0)');
      if(t>=1 && !d.arrived){{
d.arrived=true; d.arrT=now; arrivedN++;
var bgEl=d.el.querySelector('circle');
if(bgEl){{ bgEl.setAttribute('r','12'); bgEl.setAttribute('fill','rgba(0,210,255,0.4)'); }}
parent.setTimeout(function(dd){{
  var b=dd.el.querySelector('circle');
  if(b){{ b.setAttribute('r','7'); b.setAttribute('fill','rgba(0,210,255,0.08)'); }}
}}.bind(null,d), 350);
if(arrivedN===NDRONES && pStatus)
  pStatus.innerHTML='<span style="color:#00D2FF;font-weight:900">&#10003; FLEET DEPLOYED &#8212; LAUNCHING</span>';
      }}
    }});
    if(!allDone) parent.requestAnimationFrame(frame);
  }}
  parent.requestAnimationFrame(frame);
  /* watchdog runs in parent context — survives iframe teardown on Streamlit rerender */
  if(parent._brincFloWd) parent.clearInterval(parent._brincFloWd);
  parent._brincFloWd = null;
  function removeFlo(){{
    allDone=true;
    if(parent._brincFloWd){{ parent.clearInterval(parent._brincFloWd); parent._brincFloWd=null; }}
    var el=doc.getElementById('brinc-flo');
    if(el){{ el.style.transition='opacity 0.5s ease'; el.style.opacity='0'; }}
    parent.setTimeout(function(){{
      var el2=doc.getElementById('brinc-flo'); if(el2&&el2.parentNode) el2.parentNode.removeChild(el2);
      var s=doc.getElementById('brinc-flo-css'); if(s&&s.parentNode) s.parentNode.removeChild(s);
    }},520);
  }}
  parent.setTimeout(function(){{
    parent._brincFloWd=parent.setInterval(function(){{
      var hasChart=
doc.querySelector('[data-testid="stPlotlyChart"]')||
doc.querySelector('.js-plotly-plot')||
doc.querySelector('.stPlotlyChart')||
doc.querySelector('[class*="js-plotly"]')||
doc.querySelector('.mapboxgl-canvas')||
doc.querySelector('.maplibregl-canvas')||
doc.querySelector('[data-testid="stPlotly"]')||
doc.querySelector('.plot-container');
      if(hasChart) removeFlo();
    }},400);
  }},2500);
  /* safety net: hard-remove after 30s */
  parent.setTimeout(removeFlo, 30000);
}})();
</script>
</body></html>
"""
_swarm_overlay_html = (
    _swarm_overlay_html
    .replace("{_swarm_logo_b64}", _swarm_logo_b64)
    .replace("{_swarm_gigs_b64}", _swarm_gigs_b64)
    .replace("{_swarm_map_svg}", _swarm_map_svg)
    .replace("{_swarm_city_js}", _swarm_city_js)
    .replace("{_swarm_state_js}", _swarm_state_js)
    .replace("{{", "{")
    .replace("}}", "}")
)
components.html(_swarm_overlay_html, height=0, scrolling=False)
prog = st.progress(0, text="🫡 Preparing tools worthy of those who serve…")
all_gdfs = []
total_estimated_pop = 0
_sim_station_file, _sim_boundary_files, _sim_unused_files = split_simulation_optional_files(
    st.session_state.get('sim_optional_uploader') or [],
    _is_boundary_sidecar,
    _looks_like_stations,
)
if _sim_unused_files:
    st.info("Path 01 ignored non-station files: " + ", ".join(_sim_unused_files))
if _sim_boundary_files:
    try:
        _overlay_file = load_simulation_boundary_overlay(
            st.session_state,
            _sim_boundary_files,
            _load_uploaded_boundary_overlay,
        )
        st.toast(f"Custom boundary overlay loaded: {_overlay_file}")
    except Exception as _overlay_exc:
        prog.empty()
        st.error(f"Boundary shapefile error: {_overlay_exc}")
        st.stop()




# ── Corridor mode vs. Census boundary mode ───────────────────────
_hw_exec = st.session_state.get('highway_patrol_mode', False)
_active_hw = st.session_state.get('active_highway')
_hw_state = active_targets[0]['state'] if active_targets else None
_corridor_mode = _hw_exec and bool(_active_hw) and bool(_hw_state)

if _corridor_mode:
    prog.progress(20, text=f"🛣️ Fetching {_active_hw} route geometry…")
    _hw_gdf = fetch_highway_geometry(_active_hw, _hw_state)
    if _hw_gdf is None:
        prog.empty()
        st.error(
            f"❌ Could not fetch route geometry for {_active_hw} in {_hw_state}. "
            "Check the highway reference (e.g. I-80) and try again."
        )
        st.stop()
    prog.progress(38, text=f"📐 Building {_active_hw} corridor boundary…")
    _corridor_poly, _corridor_line, _corridor_miles = build_corridor_polygon(_hw_gdf)
    city_poly = _corridor_poly
    _corridor_label = f"{_active_hw} Corridor"
    _corridor_override = gpd.GeoDataFrame(
        {
            'DISPLAY_NAME': [_corridor_label],
            'data_count': [1],
        },
        geometry=[_corridor_poly],
        crs="EPSG:4326",
    )
    st.session_state['master_gdf_override'] = _corridor_override
    st.session_state['saved_jurisdiction_names'] = [_corridor_label]
    st.session_state['population_reference_targets'] = [_corridor_label]
    st.session_state['active_city'] = _corridor_label
    st.session_state['active_state'] = _hw_state
    st.session_state['estimated_pop'] = 0
    st.session_state['_pop_resolved'] = False
    prog.progress(55, text=f"🚔 Modeling patrol calls along {_corridor_miles:.0f} miles of {_active_hw}…")
    annual_cfs = estimate_corridor_calls(_corridor_miles)
    df_demo, annual_cfs, simulated_points_count = build_corridor_demo(
        _corridor_line, _corridor_poly, annual_cfs, generate_random_points_in_polygon
    )
    st.toast(f"✅ {_active_hw} · {_hw_state} · {_corridor_miles:.0f} mi · {annual_cfs:,} calls/yr")

else:
    fast_demo_target_set = {(city, state) for city, state in FAST_DEMO_CITIES}
    is_fast_demo_path = bool(active_targets) and all(
        (str(loc.get('city', '') or '').strip(), str(loc.get('state', '') or '').strip().upper())
        in fast_demo_target_set
        for loc in active_targets
    )
    if is_fast_demo_path:
        city_name = str(active_targets[0].get('city', '') or '').strip()
        state_name = str(active_targets[0].get('state', '') or '').strip().upper()
        fast_payload = load_fast_demo_payload(city_name, state_name)
        if not fast_payload:
            prog.empty()
            components.html("""<!DOCTYPE html><html><head></head><body><script>
(function(){
  var doc=parent.document;
  if(parent._brincFloWd){parent.clearInterval(parent._brincFloWd);parent._brincFloWd=null;}
  var el=doc.getElementById('brinc-flo');
  if(el){el.style.transition='opacity 0.35s ease';el.style.opacity='0';
    parent.setTimeout(function(){
      var e=doc.getElementById('brinc-flo');if(e&&e.parentNode)e.parentNode.removeChild(e);
      var s=doc.getElementById('brinc-flo-css');if(s&&s.parentNode)s.parentNode.removeChild(s);
    },360);}
})();
</script></body></html>""", height=0, scrolling=False)
            st.error("❌ Could not load the preloaded demo boundaries.")
            st.stop()
        all_gdfs = fast_payload['all_gdfs']
        boundary_records = fast_payload['boundary_records']
        total_estimated_pop = fast_payload['total_estimated_pop']
        boundary_messages = fast_payload['boundary_messages']
        boundary_warnings = fast_payload['boundary_warnings']
        rerun_demo_target = fast_payload['rerun_demo_target']
        all_populations_verified = fast_payload['all_populations_verified']
