"""
Onboarding page rendering for DFR application.

Handles file upload, jurisdiction selection, data validation, and preparation
for the simulation page.
"""

import streamlit as st

from modules.image_utils import get_themed_logo_base64, get_transparent_product_base64


def render_onboarding_page() -> None:
    """Render the onboarding/upload page.
    
    Displays upload interface, file handling, jurisdiction selection,
    and data preparation workflow. Sets st.session_state['csvs_ready']
    when data is ready for simulation page.
    """

    # GRAB THE LOGO FOR THE UPLOAD PAGE
    logo_b64 = get_themed_logo_base64("logo.png", theme="dark")
    hero_logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:72px; margin-bottom:15px;">' if logo_b64 else f'<div style="font-size:2.5rem; font-weight:900; letter-spacing:4px; color:#ffffff; margin-bottom:15px;">BRINC</div>'
    # Upper-right hero image uses gigs.png (the drone product shot)
    gigs_b64 = get_transparent_product_base64("gigs.png")

    st.markdown(f"""
    <style>
    @keyframes pulseGlow {{
        0%, 100% {{ opacity: 0.55; }}
        50%       {{ opacity: 1.0; }}
    }}
    @keyframes fadeUp {{
        from {{ opacity:0; transform:translateY(14px); }}
        to   {{ opacity:1; transform:translateY(0); }}
    }}
    .brinc-hero {{
        position: relative;
        text-align: center;
        padding: 52px 24px 40px;
        margin-bottom: 36px;
        border-radius: 12px;
        background: radial-gradient(ellipse at 50% 0%,
            rgba(0,210,255,0.13) 0%, rgba(0,0,0,0) 68%);
        border-bottom: 1px solid rgba(0,210,255,0.15);
        overflow: hidden;
        animation: fadeUp 0.5s ease both;
    }}
    .brinc-hero::before {{
        content: '';
        position: absolute; inset: 0;
        background:
            repeating-linear-gradient(0deg,
                transparent, transparent 39px,
                rgba(0,210,255,0.025) 39px,
                rgba(0,210,255,0.025) 40px),
            repeating-linear-gradient(90deg,
                transparent, transparent 79px,
                rgba(0,210,255,0.025) 79px,
                rgba(0,210,255,0.025) 80px);
        pointer-events: none;
    }}
    .brinc-eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 4px;
        color: {accent_color};
        text-transform: uppercase;
        opacity: 0.7;
        margin-bottom: 12px;
    }}
    .brinc-h1 {{
        font-family: 'Manrope', sans-serif;
        font-size: clamp(2rem, 4vw, 3rem);
        font-weight: 900;
        color: #ffffff;
        letter-spacing: -0.5px;
        line-height: 1.08;
        margin-bottom: 12px;
    }}
    .brinc-h1 em {{
        font-style: normal;
        color: {accent_color};
    }}
    .brinc-tagline {{
        font-size: 0.88rem;
        color: #666;
        max-width: 500px;
        margin: 0 auto 22px;
        line-height: 1.65;
    }}
    .brinc-badges {{
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 8px;
        margin-top: 4px;
    }}
    .brinc-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(0,210,255,0.07);
        border: 1px solid rgba(0,210,255,0.2);
        border-radius: 100px;
        padding: 4px 13px;
        font-size: 0.64rem;
        font-weight: 700;
        color: {accent_color};
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }}
    .brinc-badge.pulse {{
        animation: pulseGlow 3s ease-in-out infinite;
    }}
    .path-card {{
        background: #080808;
        border: 1px solid #1c1c1c;
        border-radius: 10px;
        padding: 22px 18px 16px;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .path-card::after {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--accent);
        border-radius: 10px 10px 0 0;
    }}
    .path-card:hover {{
        border-color: rgba(255,255,255,0.12);
        box-shadow: 0 0 28px rgba(0,210,255,0.05);
    }}
    .pc-icon  {{ font-size: 1.5rem; display:block; margin-bottom:9px; }}
    .pc-tag   {{ font-size:0.55rem; font-weight:800; letter-spacing:2.5px;
                 text-transform:uppercase; color:var(--accent); margin-bottom:5px; }}
    .pc-title {{ font-size:1rem; font-weight:800; color:#fff;
                 line-height:1.25; margin-bottom:7px; }}
    .pc-desc  {{ font-size:0.7rem; color:#555; line-height:1.6; margin-bottom:0; }}
    .field-footnote {{
        font-size: 0.63rem; color: #3a3a3a; line-height: 1.75;
        margin-top: 10px; border-top: 1px solid #141414;
        padding-top: 10px;
    }}
    .demo-cities {{
        font-size: 0.65rem; color: #444; line-height: 1.9;
        margin-top: 10px;
    }}
    .demo-cities b {{ color: #555; }}
    .demo-check {{
        font-size: 0.63rem; color: #333; line-height: 1.8;
        margin-top: 12px; border-top: 1px solid #141414;
        padding-top: 10px;
    }}
    .demo-check span {{ color: {accent_color}; margin-right: 5px; }}
    </style>

    <div class="brinc-hero" style="display:flex; align-items:center; justify-content:space-between; text-align:left; padding: 48px 48px 40px; gap: 32px; flex-wrap: wrap;">
        <div style="flex:1; min-width:280px;">
            {hero_logo_html}
            <div class="brinc-eyebrow" style="margin-top:6px;">BRINC Drones · DFR Platform</div>
            <div class="brinc-h1">
                Coverage. Operations.<br><em>Savings.</em>
            </div>
            <div class="brinc-tagline" style="margin-left:0; text-align:left;">
                Optimize drone-as-first-responder deployments for any US jurisdiction.
                Model coverage, forecast ROI, and generate grant-ready proposals in minutes.
            </div>
            <div class="brinc-badges" style="justify-content:flex-start;">
                <div class="brinc-badge">🛰 3D Swarm Simulation</div>
                <div class="brinc-badge">🗺 Census Boundaries</div>
                <div class="brinc-badge">📄 Grant Narrative Export</div>
                <div class="brinc-badge">✈️ FAA LAANC Overlay</div>
                <div class="brinc-badge">⚡ MCLP Optimizer</div>
            </div>
        </div>
        <div style="flex:0 0 auto; display:flex; align-items:center; justify-content:center;">
            <img src="data:image/png;base64,{gigs_b64}" style="height:260px; max-width:420px; object-fit:contain; filter: drop-shadow(0 0 32px rgba(0,210,255,0.35)) drop-shadow(0 0 8px rgba(0,150,255,0.2));" alt="BRINC COS Drone Station">
        </div>
    </div>
    """, unsafe_allow_html=True)

    path_sim_col, path_upload_col, path_demo_col = st.columns(3, gap="medium")

    with path_sim_col:
        st.markdown(f"""
        <div class="path-card" style="--accent:{accent_color};">
            <span class="pc-icon">🗺</span>
            <div class="pc-tag">Path 01</div>
            <div class="pc-title">Simulate Any<br>US Region</div>
            <div class="pc-desc">No data needed. Real Census boundaries + realistic 911 call distribution generated automatically. Stack multiple jurisdictions in one run.</div>
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
            "Optional: Stations + boundary overlay files",
            accept_multiple_files=True,
            type=['csv', 'xlsx', 'xls', 'xlsb', 'xlsm', 'brinc', 'json', 'txt', 'shp', 'shx', 'dbf', 'prj'],
            key="sim_optional_uploader",
            help="Drop a custom stations CSV/Excel plus optional shapefile sidecars (.shp/.shx/.dbf/.prj). Path 01 ignores CAD and .brinc files if included."
        )


        station_template_bytes = base64.b64decode(
            "TkFNRSxUWVBFLEFERFJFU1MsQ0FQQUNJVFksTk9URVMsTEFULExPTgpTYW1wbGUgMSBQb2xpY2UgU3RhdGlvbixQb2xpY2UsIjQyMCBXIFN0YXRlIFN0LCBSb2NrZm9yZCwgSUwgNjExMDEiLDIsUHJpbWFyeSBkb3dudG93biBkaXNwYXRjaCBodWIsNDIuMjcxMSwtODkuMDk0MApTYW1wbGUgMiBQb2xpY2UgU3RhdGlvbixQb2xpY2UsIjM0MDEgTiBNYWluIFN0LCBSb2NrZm9yZCwgSUwgNjExMDMiLDIsTm9ydGggc2lkZSBwYXRyb2wgYmFzZSw0Mi4zMTA1LC04OS4wODg3ClNhbXBsZSAzIFBvbGljZSBTdGF0aW9uLFBvbGljZSwiMTcwNyBTIE11bGZvcmQgUmQsIFJvY2tmb3JkLCBJTCA2MTEwOCIsMSxTb3V0aGVhc3QgY29ycmlkb3IgY292ZXJhZ2UsNDIuMjQ4OCwtODguOTk5OApTYW1wbGUgNCBQb2xpY2UgU3RhdGlvbixQb2xpY2UsIjQzNDAgVyBTdGF0ZSBTdCwgUm9ja2ZvcmQsIElMIDYxMTAyIiwxLFdlc3Qgc2lkZSByYXBpZCByZXNwb25zZSB1bml0LDQyLjI3MTIsLTg5LjEyNDEKU2FtcGxlIDEgRmlyZSBTdGF0aW9uLEZpcmUsIjcwOCBDbGludG9uIFN0LCBSb2NrZm9yZCwgSUwgNjExMDEiLDIsQ2VudHJhbCBmaXJlIGRpc3BhdGNoIC0gU3RhdGlvbiAxLDQyLjI3MjAsLTg5LjA4OTgKU2FtcGxlIDIgRmlyZSBTdGF0aW9uLEZpcmUsIjE0MDIgTiBDb3VydCBTdCwgUm9ja2ZvcmQsIElMIDYxMTAzIiwxLE5vcnRoIFJvY2tmb3JkIGZpcmUgY292ZXJhZ2UsNDIuMjk1MSwtODkuMDgyNgpTYW1wbGUgMyBGaXJlIFN0YXRpb24sRmlyZSwiMjI1MCBTIEFscGluZSBSZCwgUm9ja2ZvcmQsIElMIDYxMTA4IiwxLFNvdXRoIEFscGluZSBmaXJlIHJlc3BvbnNlLDQyLjI0MDEsLTg4Ljk5NjQKU2FtcGxlIDQgRmlyZSBTdGF0aW9uLEZpcmUsIjUyODUgU2FmZm9yZCBSZCwgUm9ja2ZvcmQsIElMIDYxMTAxIiwxLFdlc3QgZGlzdHJpY3QgZmlyZSBzdGF0aW9uLDQyLjI2OTgsLTg5LjE0MDIKU2FtcGxlIDEgRU1TIFN0YXRpb24sRU1TLCIxNDAxIEUgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwNCIsMixFYXN0IHNpZGUgRU1TIHJhcGlkIHJlc3BvbnNlLDQyLjI2OTQsLTg5LjA2MjEKU2FtcGxlIDIgRU1TIFN0YXRpb24sRU1TLCIzNzIwIENoYXJsZXMgU3QsIFJvY2tmb3JkLCBJTCA2MTEwOCIsMSxTb3V0aGVhc3QgRU1TIGNvdmVyYWdlIHpvbmUsNDIuMjUyMiwtODkuMDA1OApTYW1wbGUgMyBFTVMgU3RhdGlvbixFTVMsIjQ4MjUgTiBCZWxsIFNjaG9vbCBSZCwgUm9ja2ZvcmQsIElMIDYxMTA3IiwxLE5vcnRoZWFzdCBFTVMgcmVzcG9uc2UgaHViLDQyLjMwMjEsLTg4Ljk4OTEKU2FtcGxlIDEgR292IFN0YXRpb24sR292ZXJubWVudCwiNDI1IEUgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwNCIsMSxXaW5uZWJhZ28gQ291bnR5IGFkbWluIGJ1aWxkaW5nLDQyLjI3MTUsLTg5LjA4NDgKU2FtcGxlIDIgR292IFN0YXRpb24sR292ZXJubWVudCwiMzAwIFcgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwMSIsMSxDaXR5IEhhbGwgLSBSb2NrZm9yZCBtdW5pY2lwYWwgY2VudGVyLDQyLjI3MTEsLTg5LjA5NTcKU2FtcGxlIDMgR292IFN0YXRpb24sR292ZXJubWVudCwiNjUwIFcgU3RhdGUgU3QsIFJvY2tmb3JkLCBJTCA2MTEwMiIsMSxQdWJsaWMgd29ya3MgYW5kIGVtZXJnZW5jeSBtZ210LDQyLjI3MTMsLTg5LjEwMTgK"
        )

        st.caption("Upload a stations CSV/Excel, optional boundary shapefile sidecars, or download the sample template. If no stations file is uploaded, stations will be auto-generated from call data.")

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

    with path_upload_col:
        st.markdown(f"""
        <div class="path-card" style="--accent:#39FF14;">
            <span class="pc-icon">📂</span>
            <div class="pc-tag">Path 02</div>
            <div class="pc-title">Upload CAD<br>or .brinc Save</div>
            <div class="pc-desc">
                Drop <b>any</b> CAD export CSV — no renaming needed.
                Or, drop a previously saved <b>.brinc</b> file to instantly restore your deployment.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Drop CAD calls + optional stations + optional boundary shapefile files",
            accept_multiple_files=True,
            type=['csv', 'xlsx', 'xls', 'xlsb', 'xlsm', 'brinc', 'json', 'txt', 'shp', 'shx', 'dbf', 'prj'],
            label_visibility="collapsed",
            help="Upload real CAD calls, optional stations, and optional shapefile sidecars (.shp/.shx/.dbf/.prj) for a display-only boundary overlay. OR drop a .brinc file to restore a previous session."
        )

        st.markdown("""
        <div class="field-footnote">
            <b style='color:#555;'>1 file</b> — any CAD export (CSV or Excel); stations auto-built from OSM<br>
            <b style='color:#555;'>Multiple CAD files</b> — drop several spreadsheets; they are combined automatically<br>
            <b style='color:#555;'>CAD + stations</b> — include a file with "station" in the name to supply custom stations<br>
            <b style='color:#39FF14;'>.brinc file</b> — instantly restore a saved deployment<br>
            Max 25,000 calls (sampled) · 100 stations
        </div>
        """, unsafe_allow_html=True)

        def _looks_like_stations(fname):
            n = fname.lower()
            return any(k in n for k in ['station','facility','loc'])

        def _is_boundary_sidecar(fname):
            return Path(fname).suffix.lower() in {'.shp', '.shx', '.dbf', '.prj'}

        current_upload_signature = _uploaded_files_signature(uploaded_files)
        if current_upload_signature and st.session_state.get('census_source_signature') and current_upload_signature != st.session_state.get('census_source_signature'):
            _reset_census_state(st.session_state)

        census_result_files = None
        if st.session_state.get('census_pending'):
            _census_summary = st.session_state.get('census_summary') or {}
            _rows_ready = int(_census_summary.get('rows_ready', 0) or 0)
            _rows_missing = int(_census_summary.get('rows_missing', 0) or 0)
            st.warning(
                f"Census batch conversion is waiting for results. "
                f"{_rows_ready:,} rows are ready for Census formatting and {_rows_missing:,} rows still need address cleanup."
            )
            st.caption(
                "Download the prepared batch files, run them through the Census batch geocoder, "
                "then upload the returned result CSVs here. The prepared data is only kept for this browser session."
            )
            st.info(
                "What is happening now: the app identified that this upload does not contain recoverable coordinates and switched to the Census batch workflow. "
                "Preparing the batch files should usually take a few seconds to about 30 seconds. "
                "After that, total turnaround depends on how quickly the Census files are uploaded there and returned here."
            )
            if st.session_state.get('census_sample_bytes'):
                st.download_button(
                    "⬇️ Download Census Sample Batch",
                    data=st.session_state['census_sample_bytes'],
                    file_name=st.session_state.get('census_sample_name') or "census_sample_batch.csv",
                    mime="text/csv",
                    key="download_census_sample_batch_btn",
                    width="stretch",
                )
            if st.session_state.get('census_batch_zip_bytes'):
                st.download_button(
                    "⬇️ Download Census Batch ZIP",
                    data=st.session_state['census_batch_zip_bytes'],
                    file_name=st.session_state.get('census_batch_zip_name') or "census_batches.zip",
                    mime="application/zip",
                    key="download_census_batch_zip_btn",
                    width="stretch",
                )
            census_result_files = st.file_uploader(
                "Upload returned Census result CSVs",
                accept_multiple_files=True,
                type=['csv', 'txt'],
                key='census_result_files_uploader',
                help="Upload the CSV result files returned by the Census batch geocoder. The app will stitch them together and continue into the stations workflow.",
            )

            if census_result_files:
                with st.spinner("🛰 Stitching Census results back into the CAD file…"):
                    result_df = parse_census_result_files(census_result_files)
                    partial_calls_df = st.session_state.get('census_partial_calls_df')
                    original_df = st.session_state.get('census_original_df')
                    if partial_calls_df is None or original_df is None or result_df.empty:
                        st.error("❌ Census result upload failed: missing prepared session data or no valid result rows were found.")
                        st.stop()

                    merged_full_df, merged_ready_df, merge_summary = merge_census_results(
                        partial_calls_df,
                        result_df,
                        validate_outputs=False,
                    )
                    if merged_ready_df is None or merged_ready_df.empty:
                        st.error("❌ Census result upload failed: no valid coordinates were recovered from the returned result files.")
                        st.stop()

                    _export_started_at = time.perf_counter()
                    corrected_export_df = build_corrected_export_from_merged(merged_full_df)
                    corrected_csv = corrected_export_df.to_csv(index=False).encode('utf-8')
                    _push_upload_log(
                        f"Census corrected export built in {_format_wait(time.perf_counter() - _export_started_at)}."
                    )
                    st.session_state['census_corrected_bytes'] = corrected_csv
                    st.session_state['census_corrected_name'] = "cad_calls_census_corrected.csv"
                    st.session_state['census_conversion_summary'] = merge_summary
                    st.session_state['census_download_notice'] = True

                    df_c_full = merged_ready_df.reset_index(drop=True).copy()
                    if len(df_c_full) > 25000:
                        df_c = df_c_full.sample(25000, random_state=42).reset_index(drop=True)
                        st.toast(f"⚠️ Optimization modeled with {len(df_c):,} representative calls out of {len(df_c_full):,} geocoded incidents.")
                    else:
                        df_c = df_c_full.copy()

                    call_files_current, station_file_current, boundary_files_current = split_uploaded_files(
                        uploaded_files or [],
                        _is_boundary_sidecar,
                        _looks_like_stations,
                    )

                    if station_file_current is not None:
                        with st.spinner("🔍 Reading stations file…"):
                            try:
                                df_s, osm_note = load_station_file(station_file_current)
                                st.session_state['stations_user_uploaded'] = True
                            except Exception as e:
                                df_s, osm_note = None, f"Failed: {e}"
                        if df_s is None or df_s.empty:
                            st.error(f"❌ Stations file error: {osm_note}")
                            st.stop()
                    else:
                        st.session_state['stations_user_uploaded'] = False
                        with st.spinner("🌐 No stations file detected — querying OpenStreetMap for police, fire & schools; this can take 10-20 seconds…"):
                            df_s, osm_note = generate_stations_from_calls(df_c)
                        if df_s is None or df_s.empty:
                            df_s = _make_random_stations(df_c, n=40)
                            osm_note = "⚠️ Could not reach any map source — using estimated station positions from call data."
                            st.warning(osm_note)
                        else:
                            st.toast(f"✅ {osm_note}")

                    if len(df_s) > 100:
                        df_s = df_s.sample(100, random_state=42).reset_index(drop=True)

                    with st.spinner("🛰 Census coordinates restored — resolving jurisdiction…"):
                        detected_city, detected_state, detection_source = detect_location_from_calls(
                            df_c,
                            STATE_FIPS,
                            US_STATES_ABBR,
                            reverse_geocode_state,
                        )
                        if detected_city and detected_state:
                            st.session_state['active_city'] = str(detected_city).title()
                            st.session_state['active_state'] = detected_state
                            st.session_state['target_cities'] = [{"city": detected_city, "state": detected_state}]
                            st.session_state['location_detection_source'] = detection_source
                        elif detected_state:
                            st.session_state['active_state'] = detected_state
                            st.session_state['location_detection_source'] = detection_source

                    st.session_state['df_calls'] = df_c
                    st.session_state['df_calls_full'] = df_c_full
                    st.session_state['df_stations'] = df_s
                    st.session_state['total_original_calls'] = int(merge_summary.get('rows_total', len(df_c_full)) or len(df_c_full))
                    st.session_state['total_modeled_calls'] = len(df_c)

                    with st.spinner(get_jurisdiction_message()):
                        resolve_uploaded_boundaries(
                            st,
                            st.session_state,
                            df_c,
                            df_c_full,
                            STATE_FIPS,
                            find_jurisdictions_by_coordinates,
                            _select_best_boundary_for_calls,
                            save_boundary_gdf,
                        )

                    try:
                        _refresh_reference_population(st.session_state)
                    except Exception:
                        pass

                    st.session_state['data_source'] = 'cad_upload'
                    st.session_state['demo_mode_used'] = False
                    st.session_state['sim_mode_used'] = False
                    st.session_state['map_build_logged'] = False
                    st.session_state['csvs_ready'] = True
                    st.toast("✅ Census batch conversion completed. The corrected calls file is ready for download in the sidebar.")
                    _reset_census_state(st.session_state)
                    st.session_state['census_corrected_bytes'] = corrected_csv
                    st.session_state['census_corrected_name'] = "cad_calls_census_corrected.csv"
                    st.session_state['census_conversion_summary'] = merge_summary
                    st.session_state['census_download_notice'] = True
                    st.rerun()

        if uploaded_files and len(uploaded_files) >= 1 and not (
            st.session_state.get('census_pending') and
            current_upload_signature == st.session_state.get('census_source_signature') and
            not census_result_files
        ):
            _upload_logo_b64 = get_themed_logo_base64("logo.png", theme="dark") or ""
            _upload_gigs_b64 = get_transparent_product_base64("gigs.png") or ""
            _upload_overlay_html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
    <script>
    (function(){{
      var doc = parent.document;
      var old = doc.getElementById('brinc-flo');
      if(old && old.parentNode) old.parentNode.removeChild(old);
      var oldCss = doc.getElementById('brinc-flo-css');
      if(oldCss && oldCss.parentNode) oldCss.parentNode.removeChild(oldCss);
      var css = doc.createElement('style');
      css.id = 'brinc-flo-css';
      css.textContent =
        '#brinc-flo{{position:fixed!important;top:0!important;left:0!important;width:100vw!important;height:100vh!important;background:rgba(4,7,16,0.97)!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;z-index:2147483647!important;font-family:"IBM Plex Mono",monospace!important}}'
        +'#brinc-flo .fl-panels{{display:flex;align-items:center;justify-content:center;width:100%;max-width:940px;gap:24px;padding:0 24px}}'
        +'#brinc-flo .fl-side{{width:150px;flex-shrink:0;display:flex;align-items:center;justify-content:center}}'
        +'#brinc-flo .fl-side img{{max-width:140px;max-height:90px;object-fit:contain;opacity:0.92}}'
        +'#brinc-flo .fl-map{{flex:1;min-width:0;display:flex;align-items:center;justify-content:center}}'
        +'#brinc-flo .fl-footer{{margin-top:20px;text-align:center;max-width:760px;padding:0 18px}}'
        +'#brinc-flo .fl-city{{font-size:20px;font-weight:900;letter-spacing:3px;color:#fff}}'
        +'#brinc-flo .fl-stline{{font-size:10px;letter-spacing:2px;color:rgba(0,210,255,0.7);text-transform:uppercase;margin-top:7px}}'
        +'#brinc-flo .fl-made{{margin-top:12px;font-size:11px;font-weight:800;letter-spacing:2.6px;color:rgba(255,255,255,0.92);text-transform:uppercase}}'
        +'#brinc-flo .fl-copy{{margin-top:8px;font-size:11px;line-height:1.55;color:rgba(255,255,255,0.62)}}'
        +'#brinc-flo .fl-prog-wrap{{margin:14px auto 0;max-width:520px}}'
        +'#brinc-flo .fl-prog-meta{{display:flex;justify-content:space-between;gap:12px;font-size:10px;letter-spacing:1.6px;color:rgba(255,255,255,0.62);text-transform:uppercase}}'
        +'#brinc-flo .fl-prog{{margin-top:6px;height:7px;border-radius:999px;background:rgba(255,255,255,0.08);overflow:hidden;border:1px solid rgba(255,255,255,0.08)}}'
        +'#brinc-flo .fl-prog-bar{{height:100%;width:4%;background:linear-gradient(90deg,#00D2FF,#39FF14);box-shadow:0 0 18px rgba(0,210,255,0.35);transition:width .28s ease}}'
        +'#brinc-flo .fl-log{{margin:14px auto 0;max-width:620px;min-height:86px;max-height:132px;overflow:auto;text-align:left;padding:12px 14px;border:1px solid rgba(255,255,255,0.08);border-radius:12px;background:rgba(255,255,255,0.03);font-size:11px;line-height:1.5;color:rgba(255,255,255,0.72);white-space:pre-wrap}}'
        +'#brinc-flo .fl-log.error{{border-color:rgba(255,99,99,0.45);background:rgba(110,20,20,0.22);color:rgba(255,215,215,0.95)}}'
        +'#brinc-flo .fl-loader{{position:relative;width:280px;height:180px}}'
        +'#brinc-flo .fl-radar{{position:absolute;inset:18px;border:1px solid rgba(0,210,255,0.22);border-radius:50%}}'
        +'#brinc-flo .fl-radar::before,#brinc-flo .fl-radar::after{{content:"";position:absolute;border:1px solid rgba(0,210,255,0.18);border-radius:50%}}'
        +'#brinc-flo .fl-radar::before{{inset:22px}}'
        +'#brinc-flo .fl-radar::after{{inset:44px}}'
        +'#brinc-flo .fl-sweep{{position:absolute;left:50%;top:50%;width:120px;height:2px;transform-origin:left center;background:linear-gradient(90deg,rgba(0,210,255,0.95),rgba(0,210,255,0));animation:brinc-upload-spin 2.2s linear infinite}}'
        +'#brinc-flo .fl-core{{position:absolute;left:50%;top:50%;width:12px;height:12px;margin-left:-6px;margin-top:-6px;border-radius:50%;background:#00D2FF;box-shadow:0 0 20px rgba(0,210,255,0.65)}}'
        +'#brinc-flo .fl-blip{{position:absolute;width:10px;height:10px;border-radius:50%;background:rgba(0,210,255,0.85);box-shadow:0 0 14px rgba(0,210,255,0.5);animation:brinc-upload-blip 1.8s ease-in-out infinite alternate}}'
        +'#brinc-flo .fl-blip.b1{{left:58px;top:42px;animation-delay:0.1s}}'
        +'#brinc-flo .fl-blip.b2{{right:64px;top:58px;animation-delay:0.5s}}'
        +'#brinc-flo .fl-blip.b3{{left:96px;bottom:38px;animation-delay:0.9s}}'
        +'#brinc-flo .fl-dots::after{{content:"";animation:brinc-flo-dots 1.4s steps(4,end) infinite}}'
        +'@keyframes brinc-flo-dots{{0%{{content:""}}25%{{content:"."}}50%{{content:".."}}75%{{content:"..."}}}}'
        +'@keyframes brinc-upload-spin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}'
        +'@keyframes brinc-upload-blip{{from{{transform:scale(0.7);opacity:0.45}}to{{transform:scale(1.15);opacity:1}}}}';
      (doc.head || doc.body).appendChild(css);
      var wrap = doc.createElement('div');
      wrap.id = 'brinc-flo';
      wrap.innerHTML = '<div class="fl-panels">'
        + '<div class="fl-side"><img src="data:image/png;base64,{_upload_logo_b64}" alt="BRINC"></div>'
        + '<div class="fl-map"><div class="fl-loader"><div class="fl-radar"></div><div class="fl-sweep"></div><div class="fl-core"></div><div class="fl-blip b1"></div><div class="fl-blip b2"></div><div class="fl-blip b3"></div></div></div>'
        + '<div class="fl-side"><img src="data:image/png;base64,{_upload_gigs_b64}" alt="Fleet"></div>'
        + '</div>'
        + '<div class="fl-footer">'
        + '<div class="fl-city">CAD UPLOAD</div>'
        + '<div class="fl-stline" id="fl-stl">INGESTING INCIDENT DATA<span class="fl-dots"></span></div>'
        + '<div class="fl-made">MADE IN THE USA</div>'
        + '<div class="fl-copy">Parsing calls, resolving boundaries, and preparing deployment analysis.</div>'
        + '<div class="fl-prog-wrap"><div class="fl-prog-meta"><span id="fl-prog-label">Progress</span><span id="fl-prog-pct">0%</span></div><div class="fl-prog"><div class="fl-prog-bar" id="fl-prog-bar"></div></div></div>'
        + '<div class="fl-log" id="fl-log">Waiting to start…</div>'
        + '</div>';
      doc.body.appendChild(wrap);
      var statusEl = wrap.querySelector('#fl-stl');
      var msgs = ['INGESTING INCIDENT DATA','CHECKING FOR LAT/LON','DETECTING COLUMN TYPES','PREPARING CENSUS BATCH IF NEEDED','RESOLVING JURISDICTION','BUILDING STATION GRID','PREPARING ANALYSIS'];
      var mi = 0;
      if(parent._brincFloMsgs) parent.clearInterval(parent._brincFloMsgs);
      parent._brincFloMsgs = parent.setInterval(function(){{
        mi = (mi + 1) % msgs.length;
        if(statusEl) statusEl.innerHTML = msgs[mi] + '<span class="fl-dots"></span>';
      }}, 2400);
    }})();
    </script>
    </body></html>"""
            _upload_overlay_html = (
                _upload_overlay_html
                .replace("{_upload_logo_b64}", _upload_logo_b64)
                .replace("{_upload_gigs_b64}", _upload_gigs_b64)
                .replace("{{", "{")
                .replace("}}", "}")
            )
            components.html(_upload_overlay_html, height=0, scrolling=False)

            def _clear_upload_overlay():
                components.html("""<!DOCTYPE html><html><head></head><body><script>
    (function(){
      var doc = parent.document;
      if(parent._brincFloWd){ parent.clearInterval(parent._brincFloWd); parent._brincFloWd = null; }
      if(parent._brincFloMsgs){ parent.clearInterval(parent._brincFloMsgs); parent._brincFloMsgs = null; }
      var el = doc.getElementById('brinc-flo');
      if(el){
        el.style.transition = 'opacity 0.25s ease';
        el.style.opacity = '0';
      }
      parent.setTimeout(function(){
        var e = doc.getElementById('brinc-flo');
        if(e && e.parentNode) e.parentNode.removeChild(e);
        var s = doc.getElementById('brinc-flo-css');
        if(s && s.parentNode) s.parentNode.removeChild(s);
      }, 280);
    })();
    </script></body></html>""", height=0, scrolling=False)

            def _set_upload_overlay_status(title="", status="", copy="", progress=None, logs=None, error=False):
                _title_js = json.dumps(str(title or ""))
                _status_js = json.dumps(str(status or ""))
                _copy_js = json.dumps(str(copy or ""))
                _progress_val = max(0, min(100, int(progress if progress is not None else 0)))
                _logs_js = json.dumps([str(x) for x in (logs or [])][-8:])
                _error_js = 'true' if error else 'false'
                _upload_overlay_status_html = """<!DOCTYPE html><html><head></head><body><script>
    (function(){{
      var doc = parent.document;
      var el = doc.getElementById('brinc-flo');
      if(!el) return;
      var titleEl = el.querySelector('.fl-city');
      var statusEl = el.querySelector('#fl-stl');
      var copyEl = el.querySelector('.fl-copy');
      var progBar = el.querySelector('#fl-prog-bar');
      var progPct = el.querySelector('#fl-prog-pct');
      var logEl = el.querySelector('#fl-log');
      if(titleEl && {_title_js}) titleEl.textContent = {_title_js};
      if(statusEl && {_status_js}) statusEl.innerHTML = {_status_js} + '<span class="fl-dots"></span>';
      if(copyEl && {_copy_js}) copyEl.textContent = {_copy_js};
      if(progBar) progBar.style.width = '{_progress_val}%';
      if(progPct) progPct.textContent = '{_progress_val}%';
      if(logEl){{
        var _lines = {_logs_js};
        logEl.innerHTML = _lines && _lines.length ? _lines.join('<br>') : 'Waiting to start…';
        if({_error_js}) logEl.classList.add('error'); else logEl.classList.remove('error');
      }}
      if(parent._brincFloMsgs){{ parent.clearInterval(parent._brincFloMsgs); parent._brincFloMsgs = null; }}
    }})();
    </script></body></html>"""
                _upload_overlay_status_html = (
                    _upload_overlay_status_html
                    .replace("{_title_js}", _title_js)
                    .replace("{_status_js}", _status_js)
                    .replace("{_copy_js}", _copy_js)
                    .replace("{_progress_val}", str(_progress_val))
                    .replace("{_logs_js}", _logs_js)
                    .replace("{_error_js}", _error_js)
                    .replace("{{", "{")
                    .replace("}}", "}")
                )
                components.html(_upload_overlay_status_html, height=0, scrolling=False)

            _upload_logs = []

            def _push_upload_log(message):
                _upload_logs.append(str(message))
                return list(_upload_logs[-8:])

            # --- 1. INTELLIGENTLY CHECK FOR .BRINC FILE ---
            # Browsers sometimes append .json to .brinc files on download
            brinc_file = detect_brinc_file(uploaded_files)

            if brinc_file:
                with st.spinner("💾 Restoring saved deployment..."):
                    try:
                        save_data = load_brinc_save_data(brinc_file)
                        restore_brinc_session(st.session_state, save_data)
                        st.toast("✅ Deployment restored successfully!")
                        st.rerun()
                    except Exception as e:
                        _clear_upload_overlay()
                        st.error(f"❌ Error loading .brinc file: {e}")
                        st.stop()

            else:
                # --- 2. OTHERWISE, PROCESS AS NORMAL CSV CAD DATA ---
                st.session_state['active_city'] = ""
                st.session_state['active_state'] = ""
                st.session_state['target_cities'] = []

                call_files, station_file, boundary_files = split_uploaded_files(
                    uploaded_files,
                    _is_boundary_sidecar,
                    _looks_like_stations,
                )
                st.session_state['boundary_overlay_gdf'] = None
                st.session_state['boundary_overlay_name'] = ''
                st.session_state['boundary_overlay_file'] = ''

                if call_files:
                    census_auto_processed = False
                    _push_upload_log("Starting coordinate inspection.")
                    _set_upload_overlay_status(
                        title="CAD UPLOAD",
                        status="CHECKING FOR COORDINATES",
                        copy="Inspecting headers and cell values for usable latitude and longitude fields. This usually takes a few seconds.",
                        progress=8,
                        logs=_upload_logs,
                    )
                    with st.spinner("🔍 Detecting column types in CAD export…"):
                        df_c = aggressive_parse_calls(call_files)
                    for _pq_item in st.session_state.get('parse_quality', []):
                        _pq_in = _pq_item.get('input_rows', 0)
                        _pq_out = _pq_item.get('output_rows', 0)
                        if _pq_item.get('status') == 'error':
                            _push_upload_log(f"⚠ {_pq_item['file']}: parse failed — {_pq_item.get('error', '')[:100]}")
                        elif _pq_in > 0:
                            _pq_yield = round(100 * _pq_out / _pq_in)
                            _push_upload_log(f"{_pq_item['file']}: {_pq_in:,} rows in → {_pq_out:,} usable ({_pq_yield}%)")

                    if df_c is None or df_c.empty:
                        _push_upload_log("No usable coordinates found. Switching to automated Census batch geocoding.")
                        _set_upload_overlay_status(
                            title="CENSUS REQUIRED",
                            status="COORDINATES NOT FOUND",
                            copy="No usable latitude/longitude values were found in the upload. Preparing automated Census batch geocoding now.",
                            progress=18,
                            logs=_upload_logs,
                        )
                        with st.spinner("🛰 No recoverable coordinates found — preparing Census batch conversion; this usually takes a few seconds…"):
                            _push_upload_log("Building partial call frame for merge-back.")
                            _set_upload_overlay_status(
                                title="CENSUS REQUIRED",
                                status="BUILDING STAGING DATA",
                                copy="Preparing source rows and merge keys before Census submission.",
                                progress=24,
                                logs=_upload_logs,
                            )
                            df_c_partial = aggressive_parse_calls(call_files, require_valid_coordinates=False)
                            _push_upload_log("Extracting street, city, state, and ZIP fields for Census formatting.")
                            _set_upload_overlay_status(
                                title="CENSUS REQUIRED",
                                status="EXTRACTING ADDRESSES",
                                copy="Deriving Census-ready address fields from the uploaded CAD export.",
                                progress=32,
                                logs=_upload_logs,
                            )
                            census_stage_df, census_original_df, census_summary = build_census_staging(call_files)
                            if (
                                df_c_partial is None or
                                df_c_partial.empty or
                                '_source_row_id' not in df_c_partial.columns
                            ):
                                _push_upload_log(
                                    "Structured CAD parsing was unavailable for merge-back. Falling back to staged source rows for the Census merge."
                                )
                                df_c_partial = census_original_df.copy()
                                if '_source_row_id' not in df_c_partial.columns:
                                    df_c_partial['_source_row_id'] = [
                                        f"fallback:{idx}" for idx in range(len(df_c_partial))
                                    ]
                                if '_source_file' not in df_c_partial.columns:
                                    df_c_partial['_source_file'] = call_files[0].name if call_files else ''
                                if 'priority' not in df_c_partial.columns:
                                    df_c_partial['priority'] = 3
                                if 'agency' not in df_c_partial.columns:
                                    df_c_partial['agency'] = 'police'
                                _set_upload_overlay_status(
                                    title="CENSUS REQUIRED",
                                    status="USING MERGE FALLBACK",
                                    copy="The upload did not produce a structured CAD dataframe, so the app is preserving the staged source rows and merging coordinates back onto them directly.",
                                    progress=34,
                                    logs=_upload_logs,
                                )
                            if census_stage_df is None or census_stage_df.empty or int(census_summary.get('rows_ready', 0) or 0) == 0:
                                _clear_upload_overlay()
                                st.error("❌ Calls file error: no valid coordinates were found and the app could not assemble enough address data for Census batch geocoding.")
                                st.stop()

                            for _file_diag in (census_summary.get('files') or [])[:4]:
                                _diag_bits = []
                                if _file_diag.get('street_cols'):
                                    _diag_bits.append(f"street={','.join(_file_diag['street_cols'][:3])}")
                                if _file_diag.get('city_col'):
                                    _diag_bits.append(f"city={_file_diag['city_col']}")
                                if _file_diag.get('state_col'):
                                    _diag_bits.append(f"state={_file_diag['state_col']}")
                                if _file_diag.get('zip_col'):
                                    _diag_bits.append(f"zip={_file_diag['zip_col']}")
                                _push_upload_log(
                                    f"{_file_diag.get('file','file')}: {_file_diag.get('ready_rows',0):,}/{_file_diag.get('rows',0):,} rows ready"
                                    + (f" ({'; '.join(_diag_bits)})" if _diag_bits else "")
                                )
                            _set_upload_overlay_status(
                                title="CENSUS REQUIRED",
                                status="ADDRESS EXTRACTION COMPLETE",
                                copy="Address extraction finished. Preparing Census batches from the rows with complete street, city, state, and ZIP data.",
                                progress=38,
                                logs=_upload_logs,
                            )

                            census_chunks = make_census_batch_chunks(census_stage_df, chunk_size=5000)
                            census_timeout_sec = 180
                            census_retries = 3
                            census_stall_warn_sec = 600
                            census_started_at = st.session_state.get('_census_batch_started_at')
                            if not isinstance(census_started_at, (int, float)):
                                census_started_at = time.time()
                                st.session_state['_census_batch_started_at'] = census_started_at

                            def _format_wait(seconds):
                                seconds = max(0, int(seconds))
                                mins, secs = divmod(seconds, 60)
                                return f"{mins}m {secs:02d}s" if mins else f"{secs}s"

                            theoretical_max_wait = (
                                census_timeout_sec * census_retries
                                + sum(min(6, attempt * 2) for attempt in range(1, census_retries))
                            )
                            _push_upload_log(
                                f"Prepared {int(census_summary.get('rows_ready', 0) or 0):,} Census-ready rows across {len(census_chunks)} Census chunk(s)."
                            )
                            _push_upload_log(
                                "Census wait guidance: each POST waits up to "
                                f"{census_timeout_sec}s, total worst-case per chunk is about "
                                f"{_format_wait(theoretical_max_wait)}, and a chunk that still has not completed after "
                                f"{_format_wait(census_stall_warn_sec)} should be treated as stalled."
                            )
                            _set_upload_overlay_status(
                                title="CENSUS AUTOMATION",
                                status="SUBMITTING BATCHES",
                                copy=(
                                    "Sending chunked address batches directly to the Census geocoder. "
                                    f"Elapsed since Census submit started: {_format_wait(time.time() - census_started_at)}. "
                                    f"Each attempt can wait up to {_format_wait(census_timeout_sec)}; a healthy worst-case per chunk is about {_format_wait(theoretical_max_wait)}. "
                                    f"If the same chunk is still waiting after {_format_wait(census_stall_warn_sec)}, treat it as stalled and cancel/retry."
                                ),
                                progress=42,
                                logs=_upload_logs,
                            )

                            def _save_census_state_for_manual():
                                st.session_state['census_pending'] = True
                                st.session_state['census_source_signature'] = current_upload_signature
                                st.session_state['census_partial_calls_df'] = df_c_partial
                                st.session_state['census_original_df'] = census_original_df
                                st.session_state['census_summary'] = census_summary
                                _zip = make_census_batch_zip(census_chunks)
                                st.session_state['census_batch_zip_bytes'] = _zip
                                st.session_state['census_batch_zip_name'] = 'census_batches.zip'
                                _samp = make_sample_census_batch(census_stage_df)
                                if _samp:
                                    st.session_state['census_sample_bytes'] = _samp['csv_bytes']
                                    st.session_state['census_sample_name'] = _samp['filename']

                            census_result_parts = []
                            chunk_queue = list(census_chunks)
                            completed_chunks = 0
                            total_chunks = max(1, len(chunk_queue))
                            while chunk_queue:
                                chunk = chunk_queue.pop(0)
                                chunk_idx = completed_chunks + 1
                                _push_upload_log(
                                    f"Submitting chunk {chunk_idx}/{total_chunks} with {chunk['rows']:,} rows to Census."
                                )
                                _set_upload_overlay_status(
                                    title="CENSUS AUTOMATION",
                                    status=f"SUBMITTING CHUNK {chunk_idx} OF {total_chunks}",
                                    copy=(
                                        f"Waiting for the Census batch endpoint to return the geocoded CSV for chunk {chunk_idx} of {total_chunks}. "
                                        f"Elapsed since Census submit started: {_format_wait(time.time() - census_started_at)}. "
                                        f"If nothing returns after {_format_wait(census_stall_warn_sec)}, it is probably stalled."
                                    ),
                                    progress=42 + int(completed_chunks / max(1, total_chunks) * 34),
                                    logs=_upload_logs,
                                )
                                def _submit_census_chunk():
                                    try:
                                        return submit_census_batch_chunk(
                                            chunk['csv_bytes'],
                                            chunk['filename'],
                                            timeout=census_timeout_sec,
                                            retries=census_retries,
                                            attempt_logger=_push_upload_log,
                                        )
                                    except TypeError as exc:
                                        if "unexpected keyword argument 'attempt_logger'" in str(exc):
                                            _push_upload_log(
                                                "Live Census module is still using the older submit_census_batch_chunk signature; "
                                                "retrying without per-attempt logs."
                                            )
                                            return submit_census_batch_chunk(
                                                chunk['csv_bytes'],
                                                chunk['filename'],
                                                timeout=census_timeout_sec,
                                                retries=census_retries,
                                            )
                                        raise

                                _census_pool = ThreadPoolExecutor(max_workers=1)
                                try:
                                    _chunk_future = _census_pool.submit(_submit_census_chunk)
                                    _chunk_wait_started_at = time.time()
                                    _chunk_last_heartbeat_at = _chunk_wait_started_at
                                    while True:
                                        try:
                                            chunk_result_df, _chunk_resp = _chunk_future.result(timeout=5)
                                            break
                                        except cf.TimeoutError:
                                            _chunk_elapsed = time.time() - _chunk_wait_started_at
                                            if _chunk_elapsed > census_stall_warn_sec:
                                                _push_upload_log(
                                                    f"Chunk {chunk_idx}/{total_chunks} stalled after {_format_wait(_chunk_elapsed)}."
                                                    " Switching to manual Census batch workflow."
                                                )
                                                _census_pool.shutdown(wait=False)
                                                _save_census_state_for_manual()
                                                _clear_upload_overlay()
                                                st.warning(
                                                    "⚠️ The Census geocoder did not respond in time. "
                                                    "Download the batch files below, submit them at "
                                                    "geocoding.geo.census.gov/geocoder, and upload the returned CSVs here to continue."
                                                )
                                                st.rerun()
                                            if _chunk_elapsed - _chunk_last_heartbeat_at >= 15:
                                                _chunk_last_heartbeat_at = _chunk_elapsed
                                                _push_upload_log(
                                                    f"Chunk {chunk_idx}/{total_chunks} is still waiting after {_format_wait(_chunk_elapsed)}."
                                                )
                                            _set_upload_overlay_status(
                                                title="CENSUS AUTOMATION",
                                                status=f"SUBMITTING CHUNK {chunk_idx} OF {total_chunks}",
                                                copy=(
                                                    f"Waiting for the Census batch endpoint to return the geocoded CSV for chunk {chunk_idx} of {total_chunks}. "
                                                    f"Elapsed since this chunk started: {_format_wait(_chunk_elapsed)}. "
                                                    f"If the same chunk is still waiting after {_format_wait(census_stall_warn_sec)}, it is probably stalled."
                                                ),
                                                progress=min(
                                                    76,
                                                    42 + int(
                                                        min(_chunk_elapsed, census_stall_warn_sec)
                                                        / max(1, census_stall_warn_sec)
                                                        * 34
                                                    ),
                                                ),
                                                logs=_upload_logs,
                                            )
                                            continue
                                except Exception as exc:
                                    _census_pool.shutdown(wait=False)
                                    if chunk['rows'] > 1000 and chunk.get('frame') is not None:
                                        _push_upload_log(
                                            f"Chunk {chunk_idx}/{total_chunks} failed: {exc}. Splitting into smaller batches and retrying."
                                        )
                                        split_frame = chunk['frame']
                                        mid = max(1, len(split_frame) // 2)
                                        left = split_frame.iloc[:mid].copy().reset_index(drop=True)
                                        right = split_frame.iloc[mid:].copy().reset_index(drop=True)
                                        retry_chunks = [
                                            build_census_chunk_payload(
                                                left,
                                                chunk_index=chunk['index'],
                                                filename=chunk['filename'].replace('.csv', '_a.csv'),
                                            ),
                                            build_census_chunk_payload(
                                                right,
                                                chunk_index=chunk['index'],
                                                filename=chunk['filename'].replace('.csv', '_b.csv'),
                                            ),
                                        ]
                                        chunk_queue = retry_chunks + chunk_queue
                                        total_chunks += 1
                                        _set_upload_overlay_status(
                                            title="CENSUS AUTOMATION",
                                            status=f"RETRYING CHUNK {chunk_idx}",
                                            copy="The Census endpoint rejected the larger batch. Splitting it into smaller chunks and retrying automatically.",
                                            progress=42 + int(completed_chunks / max(1, total_chunks) * 34),
                                            logs=_upload_logs,
                                        )
                                        continue

                                    _push_upload_log(f"Chunk {chunk_idx}/{total_chunks} failed: {exc}")
                                    _save_census_state_for_manual()
                                    _clear_upload_overlay()
                                    st.warning(
                                        f"⚠️ Automated Census geocoding failed on chunk {chunk_idx} of {total_chunks}. "
                                        "Download the batch files below, submit them at "
                                        "geocoding.geo.census.gov/geocoder, and upload the returned CSVs here to continue."
                                    )
                                    st.rerun()
                                else:
                                    _census_pool.shutdown(wait=False)

                                _matched_rows = int((chunk_result_df['lat'].notna() & chunk_result_df['lon'].notna()).sum())
                                _push_upload_log(
                                    f"Chunk {chunk_idx}/{total_chunks} completed. Returned {_matched_rows:,} rows with coordinates."
                                )
                                completed_chunks += 1
                                _set_upload_overlay_status(
                                    title="CENSUS AUTOMATION",
                                    status=f"CHUNK {chunk_idx} COMPLETE",
                                    copy="Chunk returned successfully. Parsing and appending results before the next submission.",
                                    progress=42 + int(completed_chunks / max(1, total_chunks) * 34),
                                    logs=_upload_logs,
                                )
                                census_result_parts.append(chunk_result_df)

                            result_df = pd.concat(census_result_parts, ignore_index=True) if census_result_parts else pd.DataFrame()
                            result_df = result_df.drop_duplicates(subset=['source_id'], keep='first') if not result_df.empty else result_df
                            _push_upload_log("All Census chunks returned. Merging coordinates back into the source calls file.")
                            _set_upload_overlay_status(
                                title="CENSUS AUTOMATION",
                                status="MERGING RESULTS",
                                copy=(
                                    f"Combining all Census chunk responses and restoring coordinates into the original dataset. "
                                    f"Total Census wait so far: {_format_wait(time.time() - census_started_at)}."
                                ),
                                progress=80,
                                logs=_upload_logs,
                            )

                            def _merge_census_outputs():
                                _merge_export_started_at = time.perf_counter()
                                merged_full_df, merged_ready_df, merge_summary = merge_census_results(
                                    df_c_partial,
                                    result_df,
                                    validate_outputs=False,
                                )
                                _push_upload_log(
                                    f"Census merge helper finished in {_format_wait(time.perf_counter() - _merge_export_started_at)} "
                                    f"using {merge_summary.get('merge_backend', 'unknown')}."
                                )
                                if merged_ready_df is None or merged_ready_df.empty:
                                    return merged_full_df, merged_ready_df, merge_summary, None
                                _corrected_export_started_at = time.perf_counter()
                                corrected_export_df = build_corrected_export_from_merged(merged_full_df)
                                corrected_csv = corrected_export_df.to_csv(index=False).encode('utf-8')
                                _push_upload_log(
                                    f"Census corrected export built in {_format_wait(time.perf_counter() - _corrected_export_started_at)}."
                                )
                                return merged_full_df, merged_ready_df, merge_summary, corrected_csv

                            _push_upload_log("Merging Census coordinates back into the source calls file.")
                            _set_upload_overlay_status(
                                title="CENSUS AUTOMATION",
                                status="MERGING RESULTS",
                                copy=(
                                    f"Combining all Census chunk responses and restoring coordinates into the original dataset. "
                                    f"Elapsed since Census submit started: {_format_wait(time.time() - census_started_at)}."
                                ),
                                progress=80,
                                logs=_upload_logs,
                            )
                            merged_full_df, merged_ready_df, merge_summary, corrected_csv = _merge_census_outputs()

                            _push_upload_log("Census merge completed. Restoring coordinates into the working dataset.")

                            if merged_ready_df is None or merged_ready_df.empty:
                                _push_upload_log("Census returned no valid coordinates after chunk processing.")
                                _set_upload_overlay_status(
                                    title="CENSUS ERROR",
                                    status="NO VALID RESULTS",
                                    copy="Census responded, but the returned data did not contain any usable coordinates.",
                                    progress=84,
                                    logs=_upload_logs,
                                    error=True,
                                )
                                st.error("❌ Automated Census geocoding completed, but no valid coordinates were returned.")
                                st.stop()

                            st.session_state['census_corrected_bytes'] = corrected_csv
                            st.session_state['census_corrected_name'] = "cad_calls_census_corrected.csv"
                            st.session_state['census_conversion_summary'] = merge_summary
                            st.session_state['census_download_notice'] = True

                            df_c_full = merged_ready_df.reset_index(drop=True).copy()
                            if len(df_c_full) > 25000:
                                df_c = df_c_full.sample(25000, random_state=42).reset_index(drop=True)
                                st.toast(f"⚠️ Optimization modeled with {len(df_c):,} representative calls out of {len(df_c_full):,} geocoded incidents.")
                            else:
                                df_c = df_c_full.copy()

                            _push_upload_log(
                                f"Merged Census results. {int(merge_summary.get('rows_ready', len(df_c_full)) or len(df_c_full)):,} rows now have coordinates."
                            )
                            _set_upload_overlay_status(
                                title="CENSUS AUTOMATION",
                                status="GEOCODING COMPLETE",
                                copy=(
                                    f"Coordinates restored. Finalizing station discovery and jurisdiction setup now. "
                                    f"Total Census time: {_format_wait(time.time() - census_started_at)}."
                                ),
                                progress=88,
                                logs=_upload_logs,
                            )
                            census_auto_processed = True

                    if census_auto_processed:
                        df_c_full = df_c_full.reset_index(drop=True).copy()
                    else:
                        df_c_full = df_c.reset_index(drop=True).copy()

                    if len(df_c_full) > 25000:
                        df_c = df_c_full.sample(25000, random_state=42).reset_index(drop=True)
                        st.toast(f"⚠️ Optimization modeled with {len(df_c):,} representative calls out of {len(df_c_full):,} total incidents.")
                    else:
                        df_c = df_c_full.copy()

                    st.session_state.update({
                        'total_original_calls': len(df_c_full),
                        'total_modeled_calls': len(df_c),
                    })

                    if station_file is not None:
                        _push_upload_log("Loading uploaded stations file.")
                        _set_upload_overlay_status(
                            title="UPLOAD PROCESSING",
                            status="READING STATIONS FILE",
                            copy="Reading the uploaded stations file and validating station coordinates.",
                            progress=91,
                            logs=_upload_logs,
                        )
                        with st.spinner("🔍 Reading stations file…"):
                            try:
                                df_s, osm_note = load_station_file(station_file)
                                st.session_state['stations_user_uploaded'] = True
                            except Exception as e:
                                df_s, osm_note = None, f"Failed: {e}"
                        if df_s is None or df_s.empty:
                            _clear_upload_overlay()
                            st.error(f"❌ Stations file error: {osm_note}")
                            st.stop()
                    else:
                        _push_upload_log("No stations file provided. Building stations automatically from call data.")
                        _set_upload_overlay_status(
                            title="UPLOAD PROCESSING",
                            status="BUILDING STATIONS",
                            copy="No stations file was uploaded, so station candidates are being generated from the call data.",
                            progress=91,
                            logs=_upload_logs,
                        )
                        st.session_state['stations_user_uploaded'] = False
                        with st.spinner("🌐 No stations file detected — querying OpenStreetMap for police, fire & schools; this can take 10-20 seconds…"):
                            df_s, osm_note = generate_stations_from_calls(df_c)
                        if df_s is None or df_s.empty:
                            # Final safety net: scatter stations across call bounding box
                            df_s = _make_random_stations(df_c, n=40)
                            osm_note = "⚠️ Could not reach any map source — using estimated station positions from call data."
                            st.warning(osm_note)
                        else:
                            st.toast(f"✅ {osm_note}")

                    if len(df_s) > 100:
                        df_s = df_s.sample(100, random_state=42).reset_index(drop=True)

                    _push_upload_log("Detecting jurisdiction from call locations.")
                    _set_upload_overlay_status(
                        title="UPLOAD PROCESSING",
                        status="DETECTING JURISDICTION",
                        copy="Using the restored coordinates to identify the active city/state and resolve the deployment area.",
                        progress=95,
                        logs=_upload_logs,
                    )
                    with st.spinner(get_jurisdiction_message()):
                        detected_city, detected_state, detection_source = detect_location_from_calls(
                            df_c,
                            STATE_FIPS,
                            US_STATES_ABBR,
                            reverse_geocode_state,
                        )

                        if detected_city and detected_state:
                            st.session_state['active_city'] = str(detected_city).title()
                            st.session_state['active_state'] = detected_state
                            st.session_state['target_cities'] = [{"city": detected_city, "state": detected_state}]
                            st.session_state['location_detection_source'] = detection_source
                            st.toast(f"📍 Detected: {detected_city}, {detected_state}")
                        elif detected_state:
                            # We have state but no city — store state and let boundary
                            # selection use the FCC county name as a county lookup
                            st.session_state['active_state'] = detected_state
                            st.session_state['location_detection_source'] = detection_source

                    # Keep uploaded calls intact here. Boundary validation should be the first real geographic filter.
                    st.session_state['df_calls'] = df_c
                    st.session_state['df_calls_full'] = df_c_full
                    st.session_state['df_stations'] = df_s
                    st.session_state['total_original_calls'] = len(df_c_full)
                    st.session_state['total_modeled_calls'] = len(df_c)

                    _push_upload_log("Resolving uploaded boundaries and final session state.")
                    _set_upload_overlay_status(
                        title="UPLOAD PROCESSING",
                        status="FINALIZING DATASET",
                        copy="Saving the restored calls dataset, resolving boundaries, and opening the stations workflow.",
                        progress=98,
                        logs=_upload_logs,
                    )
                    with st.spinner(get_jurisdiction_message()):
                        resolve_uploaded_boundaries(
                            st,
                            st.session_state,
                            df_c,
                            df_c_full,
                            STATE_FIPS,
                            find_jurisdictions_by_coordinates,
                            _select_best_boundary_for_calls,
                            save_boundary_gdf,
                        )

                    try:
                        _refresh_reference_population(st.session_state)
                    except Exception:
                        pass

                    st.session_state['data_source'] = 'cad_upload'
                    st.session_state['demo_mode_used'] = False
                    st.session_state['sim_mode_used'] = False
                    st.session_state['map_build_logged'] = False
                    st.session_state['csvs_ready'] = True
                    _push_upload_log("Upload workflow complete. Opening the stations page.")
                    _set_upload_overlay_status(
                        title="UPLOAD COMPLETE",
                        status="OPENING STATIONS PAGE",
                        copy="The corrected calls dataset is ready. Transitioning into the stations workflow now.",
                        progress=100,
                        logs=_upload_logs,
                    )
                    st.rerun()

    with path_demo_col:
        st.markdown(f"""
        <div class="path-card" style="--accent:#FFD700;">
            <span class="pc-icon">⚡</span>
            <div class="pc-tag">Path 03</div>
            <div class="pc-title">1-Click Demo<br>Large US City</div>
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

        city_chips = "  ·  ".join([f"{c}" for c, _ in DEMO_CITIES[:12]]) + "  · and more…"
        st.markdown(f"""
        <div class="demo-cities">
            <b>Available Cities</b><br>
            {city_chips}
        </div>
        <div class="demo-check">
            <span>✓</span>Real Census boundaries<br>
            <span>✓</span>Clustered 911 simulation<br>
            <span>✓</span>100 station candidates<br>
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
            all_gdfs, boundary_records, total_estimated_pop, boundary_messages, boundary_warnings, rerun_demo_target, all_populations_verified = build_demo_boundaries(
                st.session_state,
                active_targets,
                STATE_FIPS,
                KNOWN_POPULATIONS,
                DEMO_CITIES,
                fetch_county_boundary_local,
                fetch_place_boundary_local,
                fetch_tiger_state_shapefile,
                save_boundary_gdf,
                fetch_census_population,
                fetch_census_state_population,
            )
            for _msg in boundary_messages:
                st.toast(_msg)
            for _warn in boundary_warnings:
                st.warning(_warn)
            if rerun_demo_target is not None:
                rcity, rstate = rerun_demo_target
                st.session_state['_last_demo_city'] = rcity
                st.session_state['target_cities'] = [{"city": rcity, "state": rstate}]
                for j in range(10):
                    st.session_state.pop(f"c_{j}", None)
                    st.session_state.pop(f"s_{j}", None)
                st.rerun()

            if not all_gdfs:
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
                st.error("❌ Could not find Census boundaries for any of the entered locations. Check spelling.")
                st.stop()

            _selected_boundary_override = pd.concat(all_gdfs, ignore_index=True).copy()
            _selected_name_col = next(
                (column for column in ['NAME', 'DISTRICT', 'NAMELSAD'] if column in _selected_boundary_override.columns),
                None,
            )
            if _selected_name_col is None:
                _selected_boundary_override['DISPLAY_NAME'] = 'Selected Boundary'
            else:
                _selected_boundary_override['DISPLAY_NAME'] = _selected_boundary_override[_selected_name_col].astype(str)
            _selected_boundary_override['data_count'] = 1
            st.session_state['master_gdf_override'] = _selected_boundary_override[['DISPLAY_NAME', 'data_count', 'geometry']].copy()
            _demo_selected_names = [
                str(name).strip() for name in _selected_boundary_override['DISPLAY_NAME'].tolist()
                if str(name).strip()
            ]
            st.session_state['saved_jurisdiction_names'] = list(dict.fromkeys(_demo_selected_names))
            st.session_state['population_reference_targets'] = list(dict.fromkeys(_demo_selected_names))

            prog.progress(35, text="💙 Boundaries loaded — honoring the officers who know every street…")
            active_city_gdf = pd.concat(all_gdfs, ignore_index=True)
            city_poly = active_city_gdf.geometry.union_all()
            st.session_state['estimated_pop'] = total_estimated_pop
            st.session_state['_pop_resolved'] = all_populations_verified

            prog.progress(55, text="🚔 Modeling 911 calls — every one represents someone who needed help…")
            df_demo, annual_cfs, simulated_points_count = build_demo_calls(
                city_poly,
                total_estimated_pop,
                generate_clustered_calls,
                boundary_records=boundary_records,
            )
        st.session_state['total_original_calls'] = annual_cfs
        st.session_state['df_calls'] = df_demo
        st.session_state['df_calls_full'] = df_demo.copy()
        st.session_state['total_modeled_calls'] = len(df_demo)

        prog.progress(80, text="Loading simulation stations...")
        stations_df, stations_user_uploaded, station_notices, station_warnings = resolve_demo_stations(
            st.session_state['df_calls'],
            city_poly,
            _sim_station_file,
            active_targets,
            forward_geocode,
            search_public_facility_candidates,
            generate_stations_from_calls,
            generate_random_points_in_polygon,
        )
        for _notice in station_notices:
            st.toast(_notice)
        for _warning in station_warnings:
            st.warning(_warning)
        st.session_state['df_stations'] = stations_df
        st.session_state['stations_user_uploaded'] = stations_user_uploaded

        prog.progress(100, text="✅ Ready — built for the communities they protect and serve.")
        st.session_state['inferred_daily_calls_override'] = int(annual_cfs / 365)
        st.session_state['data_source'] = 'simulation'
        st.session_state['sim_mode_used'] = True
        st.session_state['map_build_logged'] = False
        st.session_state['csvs_ready'] = True
        st.rerun()

        # ============================================================
        # COMMUNITY IMPACT DASHBOARD
        # ============================================================

        # ============================================================
        # MAIN MAP INTERFACE
        # ============================================================
