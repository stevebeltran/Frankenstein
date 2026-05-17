"""Path 01 — Simulate a Region UI and processing."""
import streamlit as st
from modules.config import accent_color, STATE_FIPS, SIMULATOR_DISCLAIMER_SHORT


def render():
    """Render Path 01 UI: Simulate a Region."""
st.markdown(f"""
<div class="path-card" style="--accent:{accent_color};">
    <span class="pc-icon">🗺</span>
    <div class="pc-tag">Path 01</div>
    <div class="pc-title">Simulate a<br>Region</div>
    <div class="pc-desc">Use this for simulation inputs and optional station files. Real Census boundaries and realistic 911 call distribution are generated automatically.</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── CITY / STATE — simplified single-row inputs ─────────────────────
_state_keys = list(STATE_FIPS.keys())

# Column headers
_h_city, _h_state = st.columns([3, 1])
_h_city.markdown("<div style='font-size:12px;color:#888;padding-bottom:2px'>City or County</div>", unsafe_allow_html=True)
_h_state.markdown("<div style='font-size:12px;color:#888;padding-bottom:2px'>State</div>", unsafe_allow_html=True)

while len(st.session_state['target_cities']) < st.session_state.city_count:
    st.session_state['target_cities'].append({"city": "", "state": st.session_state.get('active_state', 'IL')})

for i in range(st.session_state.city_count):
    c_val = st.session_state['target_cities'][i]['city'] if i < len(st.session_state['target_cities']) else ""
    s_val = st.session_state['target_cities'][i]['state'] if i < len(st.session_state['target_cities']) else "IL"

    col_city, col_state = st.columns([3, 1])

    c_name = col_city.text_input(
        f"city_or_county_{i}", value=c_val,
        placeholder="e.g. Rockford or Winnebago County",
        label_visibility="collapsed",
        key=f"c_{i}",
        help="Official municipality or county name."
    )

    # State input: text field with autocomplete validation
    s_name = col_state.text_input(
        f"state_{i}",
        value=s_val,
        max_chars=2,
        placeholder="CA",
        label_visibility="collapsed",
        key=f"s_{i}",
        help="Two-letter state abbreviation (e.g., CA, TX, NY)."
    ).upper()

    # Validate state abbreviation
    if s_name and s_name not in _state_keys:
        # Try to find a match or use the previous value
        if s_val and s_val in _state_keys:
            s_name = s_val
        elif s_name:
            # Show warning but allow the user to continue
            pass

    if i < len(st.session_state['target_cities']):
        st.session_state['target_cities'][i] = {"city": c_name, "state": s_name}
    else:
        st.session_state['target_cities'].append({"city": c_name, "state": s_name})

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# Move "+ City" and "Deploy" buttons up (before file uploader and download button)
st.markdown("""
<style>
[data-testid="stBaseButton-primary"], button[kind="primary"] {
    background: #00D2FF !important;
    background-color: #00D2FF !important;
    border-color: #00D2FF !important;
    color: #000 !important;
    font-weight: 800 !important;
}
[data-testid="stBaseButton-primary"]:hover, button[kind="primary"]:hover {
    background: #33DEFF !important;
    background-color: #33DEFF !important;
    border-color: #33DEFF !important;
    color: #000 !important;
}
</style>
""", unsafe_allow_html=True)
col_add, col_run = st.columns([1, 1])
if st.session_state.city_count < 10:
    if col_add.button("＋ City", width="stretch", key="add_city_btn"):
        st.session_state.city_count += 1
        st.rerun()
submit_demo = col_run.button("Deploy", width="stretch", key="run_sim_btn",
                             type="primary",
                             help="Fetch boundaries and launch the simulation.")

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Highway / State Police Mode ───────────────────────────────────
_hw_mode_ui = st.checkbox(
    "Highway / State Police Mode",
    key="highway_patrol_mode",
    help="Route calls along specific interstate corridors instead of jurisdiction boundaries. Each highway runs as an independent deployment plan.",
)
if _hw_mode_ui:
    _hw_ui_states = list(dict.fromkeys(
        loc['state'] for loc in st.session_state['target_cities']
        if loc.get('state') in STATE_FIPS
    ))
    _hw_ui_state = _hw_ui_states[0] if _hw_ui_states else None
    if _hw_ui_state:
        _default_hws = STATE_PRIMARY_INTERSTATES.get(_hw_ui_state, [])
        _hw_src = st.radio(
            "Corridors",
            ["Primary interstates (auto)", "Custom"],
            horizontal=True,
            key="hw_source_radio",
            help="Choose whether to deploy along the state's primary interstates automatically, or enter custom corridor names.",
        )
        if _hw_src == "Primary interstates (auto)":
            st.caption(
                f"Will deploy: {', '.join(_default_hws)}" if _default_hws
                else "No primary interstates defined for this state."
            )
            st.session_state['selected_highways'] = _default_hws
        else:
            _custom_hw_str = st.text_input(
                "Highways (comma-separated)",
                placeholder="e.g. I-80, I-29",
                key="custom_highways_input",
                help="Enter interstate or highway designations separated by commas. Each corridor runs as an independent deployment plan.",
            )
            st.session_state['selected_highways'] = [
                h.strip() for h in _custom_hw_str.split(',') if h.strip()
            ]
        _avail_hws = st.session_state.get('selected_highways', [])
        if len(_avail_hws) > 1:
            st.session_state['active_highway'] = st.selectbox(
                "Run plan for:",
                _avail_hws,
                key="active_highway_select",
                help="Select which corridor to run the active deployment plan against. Switch between corridors to compare coverage.",
            )
        elif len(_avail_hws) == 1:
            st.session_state['active_highway'] = _avail_hws[0]
        else:
            st.session_state['active_highway'] = None
    else:
        st.caption("Enter a state abbreviation above first.")
        st.session_state['selected_highways'] = []
        st.session_state['active_highway'] = None

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

st.file_uploader(
    "Optional: Station + boundary overlay files",
    accept_multiple_files=True,
    type=['csv', 'xlsx', 'xls', 'xlsb', 'xlsm', 'numbers', 'brinc', 'json', 'txt', 'shp', 'shx', 'dbf', 'prj'],
    key="sim_optional_uploader",
    help="Drop a custom station file plus optional shapefile sidecars (.shp/.shx/.dbf/.prj). Path 01 ignores CAD and .brinc files if included."
)


station_template_bytes = base64.b64decode(
    "TkFNRSxUWVBFLEFERFJFU1MsQ0FQQUNJVFksTk9URVMsTEFULExPTgpTYW1wbGUgMSBQb2xpY2UgU3RhdGlvbixQb2xpY2UsIjQyMCBXIFN0YXRlIFN0LCBSb2NrZm9yZCwgSUwgNjExMDEiLDIsUHJpbWFyeSBkb3dudG93biBkaXNwYXRjaCBodWIsNDIuMjcxMSwtODkuMDk0MApTYW1wbGUgMiBQb2xpY2UgU3RhdGlvbixQb2xpY2UsIjM0MDEgTiBNYWluIFN0LCBSb2NrZm9yZCwgSUwgNjExMDMiLDIsTm9ydGggc2lkZSBwYXRyb2wgYmFzZSw0Mi4zMTA1LC04OS4wODg3ClNhbXBsZSAzIFBvbGljZSBTdGF0aW9uLFBvbGljZSwiMTcwNyBTIE11bGZvcmQgUmQsIFJvY2tmb3JkLCBJTCA2MTEwOCIsMSxTb3V0aGVhc3QgY29ycmlkb3IgY292ZXJhZ2UsNDIuMjQ4OCwtODguOTk5OApTYW1wbGUgNCBQb2xpY2UgU3RhdGlvbixQb2xpY2UsIjQzNDAgVyBTdGF0ZSBTdCwgUm9ja2ZvcmQsIElMIDYxMTAyIiwxLFdlc3Qgc2lkZSByYXBpZCByZXNwb25zZSB1bml0LDQyLjI3MTIsLTg5LjEyNDEKU2FtcGxlIDEgRmlyZSBTdGF0aW9uLEZpcmUsIjcwOCBDbGludG9uIFN0LCBSb2NrZm9yZCwgSUwgNjExMDEiLDIsQ2VudHJhbCBmaXJlIGRpc3BhdGNoIC0gU3RhdGlvbiAxLDQyLjI3MjAsLTg5LjA4OTgKU2FtcGxlIDIgRmlyZSBTdGF0aW9uLEZpcmUsIjE0MDIgTiBDb3VydCBTdCwgUm9ja2ZvcmQsIElMIDYxMTAzIiwxLE5vcnRoIFJvY2tmb3JkIGZpcmUgY292ZXJhZ2UsNDIuMjk1MSwtODkuMDgyNgpTYW1wbGUgMyBGaXJlIFN0YXRpb24sRmlyZSwiMjI1MCBTIEFscGluZSBSZCwgUm9ja2ZvcmQsIElMIDYxMTA4IiwxLFNvdXRoIEFscGluZSBmaXJlIHJlc3BvbnNlLDQyLjI0MDEsLTg4Ljk5NjQKU2FtcGxlIDQgRmlyZSBTdGF0aW9uLEZpcmUsIjUyODUgU2FmZm9yZCBSZCwgUm9ja2ZvcmQsIElMIDYxMTAxIiwxLFdlc3QgZGlzdHJpY3QgZmlyZSBzdGF0aW9uLDQyLjI2OTgsLTg5LjE0MDIKU2FtcGxlIDEgRU1TIFN0YXRpb24sRU1TLCIxNDAxIEUgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwNCIsMixFYXN0IHNpZGUgRU1TIHJhcGlkIHJlc3BvbnNlLDQyLjI2OTQsLTg5LjA2MjEKU2FtcGxlIDIgRU1TIFN0YXRpb24sRU1TLCIzNzIwIENoYXJsZXMgU3QsIFJvY2tmb3JkLCBJTCA2MTEwOCIsMSxTb3V0aGVhc3QgRU1TIGNvdmVyYWdlIHpvbmUsNDIuMjUyMiwtODkuMDA1OApTYW1wbGUgMyBFTVMgU3RhdGlvbixFTVMsIjQ4MjUgTiBCZWxsIFNjaG9vbCBSZCwgUm9ja2ZvcmQsIElMIDYxMTA3IiwxLE5vcnRoZWFzdCBFTVMgcmVzcG9uc2UgaHViLDQyLjMwMjEsLTg4Ljk4OTEKU2FtcGxlIDEgR292IFN0YXRpb24sR292ZXJubWVudCwiNDI1IEUgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwNCIsMSxXaW5uZWJhZ28gQ291bnR5IGFkbWluIGJ1aWxkaW5nLDQyLjI3MTUsLTg5LjA4NDgKU2FtcGxlIDIgR292IFN0YXRpb24sR292ZXJubWVudCwiMzAwIFcgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwMSIsMSxDaXR5IEhhbGwgLSBSb2NrZm9yZCBtdW5pY2lwYWwgY2VudGVyLDQyLjI3MTEsLTg5LjA5NTcKU2FtcGxlIDMgR292IFN0YXRpb24sR292ZXJubWVudCwiNjUwIFcgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwMiIsMSxQdWJsaWMgd29ya3MgYW5kIGVtZXJnZW5jeSBtZ210LDQyLjI3MTMsLTg5LjEwMTgK"
)

st.caption("Upload a station file, optional boundary shapefile sidecars, or download the sample template. If no station file is uploaded, stations will be auto-generated from call data.")
st.caption("Station uploads are intended for small files only, up to 40 rows. Larger coordinate tables will be treated as incident data and routed through Path 02.")

st.download_button(
    label="📥 Sample stations.csv",
    data=station_template_bytes,
    file_name="stations.csv",
    mime="text/csv; charset=utf-8",
    key="download_station_template_btn_compact",
    help="Download sample stations template",
)
components.html("""
    <script>
    (function(){
      var _ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;display:inline-block;vertical-align:middle;">'
+ '<circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>'
+ '<circle cx="12" cy="12" r="5.5" stroke="currentColor" stroke-width="1.2" stroke-dasharray="3 2"/>'
+ '<path d="M12 5.5C9.51 5.5 7.5 7.51 7.5 10C7.5 13.25 12 18.5 12 18.5C12 18.5 16.5 13.25 16.5 10C16.5 7.51 14.49 5.5 12 5.5Z" fill="currentColor"/>'
+ '<circle cx="12" cy="10" r="2" fill="white"/>'
+ '</svg>';

      function style(){
var doc = parent.document;
var btns = doc.querySelectorAll('[data-testid="stButton"] > button');
btns.forEach(function(b){
  var p = b.querySelector('p');
  if(!p || p.textContent.trim() !== 'Deploy') return;
  if(b.getAttribute('data-brinc-deploy')) return;
  b.setAttribute('data-brinc-deploy','1');
  b.style.background   = 'linear-gradient(135deg,#00bcd4 0%,#00D2FF 100%)';
  b.style.color        = '#000';
  b.style.border       = 'none';
  b.style.borderRadius = '8px';
  b.style.fontWeight   = '800';
  b.style.fontSize     = '15px';
  b.style.letterSpacing= '0.4px';
  b.style.boxShadow    = '0 4px 20px rgba(0,210,255,0.55),0 2px 8px rgba(0,0,0,0.28)';
  b.style.transition   = 'all 0.16s ease';
  b.style.display      = 'flex';
  b.style.alignItems   = 'center';
  b.style.justifyContent = 'center';
  b.style.gap          = '7px';
  p.style.margin  = '0';
  p.style.color   = '#000';
  p.style.fontWeight = '800';
  p.style.display = 'flex';
  p.style.alignItems = 'center';
  p.style.gap = '7px';
  var icon = doc.createElement('span');
  icon.innerHTML = _ICON;
  p.insertBefore(icon, p.firstChild);
  b.addEventListener('mouseenter',function(){
b.style.boxShadow  = '0 6px 30px rgba(0,210,255,0.75),0 2px 8px rgba(0,0,0,0.3)';
b.style.transform  = 'translateY(-1px)';
b.style.background = 'linear-gradient(135deg,#00d4ee 0%,#33e0ff 100%)';
  });
  b.addEventListener('mouseleave',function(){
b.style.boxShadow  = '0 4px 20px rgba(0,210,255,0.55),0 2px 8px rgba(0,0,0,0.28)';
b.style.transform  = 'translateY(0)';
b.style.background = 'linear-gradient(135deg,#00bcd4 0%,#00D2FF 100%)';
  });
});
      }

      function bindEnterToDeploy(){
var doc = parent.document;
var targets = Array.from(doc.querySelectorAll('input[type="text"], input:not([type]), textarea'));
targets.forEach(function(input){
  if(!input || input.getAttribute('data-brinc-enter-submit')) return;
  input.setAttribute('data-brinc-enter-submit', '1');
  input.addEventListener('keydown', function(evt){
if(evt.key !== 'Enter' || evt.shiftKey || evt.ctrlKey || evt.altKey || evt.metaKey) return;
var deployBtn = Array.from(doc.querySelectorAll('[data-testid="stButton"] > button')).find(function(btn){
  var p = btn.querySelector('p');
  return p && p.textContent.trim() === 'Deploy';
});
if(!deployBtn) return;
try {
  input.dispatchEvent(new Event('change', {bubbles:true}));
  input.blur();
} catch (e) {}
evt.preventDefault();
setTimeout(function(){ deployBtn.click(); }, 60);
  });
});
      }

      new MutationObserver(function(){
style();
bindEnterToDeploy();
      }).observe(parent.document.body,{childList:true,subtree:true});
      style();
      bindEnterToDeploy();
      setTimeout(style,150);
      setTimeout(style,500);
      setTimeout(bindEnterToDeploy,150);
      setTimeout(bindEnterToDeploy,500);
    })();
    </script>
    """, height=0)

