"""Shared UI helpers for the BRINC app.

This module keeps the FAQ launcher and public-report route logic in one place so
app.py can import them without depending on optional third-party packages.
"""

from __future__ import annotations

import html
import hmac
import json
import urllib.parse

import streamlit as st

from modules.notifications import _log_qr_scan_to_sheets
from modules.public_reports import (
    _get_query_params_dict,
    _public_report_html_path,
    _public_report_metadata_path,
    _sign_public_report_id,
)
from modules.versioning import __build_datetime__, __version__


FAQ_CHANGELOG = [
    {
        "version": __version__,
        "timestamp": __build_datetime__,
        "summary": "Added an in-app FAQ launcher in the upper-left with a compact versioned release-notes footer.",
    },
]


def _render_public_report_route():
    _params = _get_query_params_dict()
    _report_id = str(_params.get("public_report", "")).strip()
    _sig = str(_params.get("sig", "")).strip()
    if not _report_id:
        return False

    try:
        _expected_sig = _sign_public_report_id(_report_id)
        _html_path = _public_report_html_path(_report_id)
        _meta_path = _public_report_metadata_path(_report_id)
    except ValueError:
        st.error("Invalid public report link.")
        st.stop()

    if not _sig or not hmac.compare_digest(_sig, _expected_sig):
        st.error("Invalid public report link.")
        st.stop()

    if not _html_path.exists():
        st.warning("This public report is not available yet.")
        st.stop()

    _scan_meta = {}
    if _meta_path.exists():
        try:
            _scan_meta = json.loads(_meta_path.read_text(encoding="utf-8"))
        except Exception:
            _scan_meta = {}

    _qr_city = str(_scan_meta.get("city", "") or "").strip()
    _qr_state = str(_scan_meta.get("state", "") or "").strip()
    _qr_rep_name = str(_scan_meta.get("rep_name", "") or "").strip() or "BRINC Representative"
    _qr_rep_email = str(_scan_meta.get("rep_email", "") or "").strip() or "sales@brincdrones.com"
    _qr_loc = ", ".join([x for x in [_qr_city, _qr_state] if x]).strip() or "your jurisdiction"
    _qr_lead_subject = urllib.parse.quote(f"DFR demo request - {_qr_loc}")
    _qr_lead_body = urllib.parse.quote(
        f"Hi {_qr_rep_name},\n\nI would like a custom DFR coverage analysis for {_qr_loc}.\n\nAgency:\nBest callback number:\n\nThanks,"
    )
    _qr_mailto = f"mailto:{_qr_rep_email}?subject={_qr_lead_subject}&body={_qr_lead_body}"

    try:
        _headers = dict(st.context.headers)
    except Exception:
        _headers = {}
    _ua = _headers.get("User-Agent", _headers.get("user-agent", ""))
    _lang = _headers.get("Accept-Language", _headers.get("accept-language", ""))
    _ip = (
        _headers.get("X-Forwarded-For", "")
        or _headers.get("x-forwarded-for", "")
        or _headers.get("Remote-Addr", "")
    ).split(",")[0].strip()

    _ua_lower = _ua.lower()
    if "iphone" in _ua_lower or "ipad" in _ua_lower:
        _device = "iOS"
    elif "android" in _ua_lower:
        _device = "Android"
    elif "mobile" in _ua_lower:
        _device = "Mobile"
    elif _ua:
        _device = "Desktop"
    else:
        _device = ""

    _log_qr_scan_to_sheets(
        report_id=_report_id,
        city=_scan_meta.get("city", ""),
        state=_scan_meta.get("state", ""),
        rep_name=_scan_meta.get("rep_name", ""),
        rep_email=_scan_meta.get("rep_email", ""),
        device=_device,
        user_agent=_ua,
        language=_lang,
        ip=_ip,
    )

    st.set_page_config(layout="wide", page_title="BRINC DFR", page_icon="https://brincdrones.com/favicon.ico")
    st.markdown(
        """
        <style>
            header, footer, #MainMenu,
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            [data-testid="stStatusWidget"],
            [data-testid="stSidebar"],
            [data-testid="stGithubButton"],
            [data-testid="stActionButton"],
            [data-testid="stBaseButton-header"],
            [data-testid="stHeaderActionElements"],
            [data-testid="stHeaderActions"],
            [data-testid="stHeader"],
            [data-testid="collapsedControl"] {display:none !important;}
            .block-container {padding-top: 0.8rem; max-width: 100%;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if _qr_mailto:
        st.markdown(f'<meta http-equiv="refresh" content="0; url={_qr_mailto}">', unsafe_allow_html=True)

    st.stop()


def _render_in_app_faq():
    _faq_items = [
        (
            "What does this software do?",
            "It helps plan BRINC Drone as First Responder deployments using incident data, jurisdiction boundaries, station modeling, and optimization.",
        ),
        (
            "What file should I upload?",
            "The most common input is a CAD or incident export in CSV or Excel format with usable location data.",
        ),
        (
            "How is the jurisdiction selected?",
            "The app matches uploaded incident coordinates to local jurisdiction boundary data, then lets you confirm or refine the selected area in the sidebar.",
        ),
        (
            "What is the difference between Responder and Guardian?",
            "Responder is modeled for shorter-range tactical response, while Guardian is modeled for broader long-range coverage and overwatch.",
        ),
        (
            "Can I choose my own stations?",
            "Yes. The app can recommend stations automatically, and you can also add or lock custom stations into the plan.",
        ),
        (
            "What outputs can I export?",
            "You can export a saved deployment plan, an executive-summary HTML report, and a Google Earth KML briefing file.",
        ),
        (
            "Why are map layers or FAA overlays missing?",
            "The regulatory cache may be missing or outdated. Re-run download_regulatory_layers.py and restart the app.",
        ),
    ]

    _faq_html_parts = []
    for _question, _answer in _faq_items:
        _faq_html_parts.append(
            f"""
            <div class="faq-item">
                <div class="faq-q">{html.escape(_question)}</div>
                <div class="faq-a">{html.escape(_answer)}</div>
            </div>
            """
        )

    _changelog_lines = "".join(
        f'<div class="faq-changelog-line">v{html.escape(str(_entry["version"]))} | '
        f'{html.escape(str(_entry["timestamp"]))} | '
        f'{html.escape(str(_entry["summary"]))}</div>'
        for _entry in FAQ_CHANGELOG
    )

    st.markdown(
        f"""
        <style>
        .faq-float {{
            position: fixed;
            top: 12px;
            left: 14px;
            z-index: 9998;
            width: min(420px, calc(100vw - 28px));
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .faq-float summary {{
            list-style: none;
        }}
        .faq-float summary::-webkit-details-marker {{
            display: none;
        }}
        .faq-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            border-radius: 999px;
            background: rgba(8, 12, 20, 0.88);
            border: 1px solid rgba(116, 224, 255, 0.22);
            color: rgba(226, 238, 246, 0.92);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            cursor: pointer;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
            backdrop-filter: blur(8px);
        }}
        .faq-pill:hover {{
            border-color: rgba(116, 224, 255, 0.42);
            background: rgba(10, 16, 28, 0.96);
        }}
        .faq-panel {{
            margin-top: 8px;
            background: rgba(7, 11, 18, 0.97);
            border: 1px solid rgba(116, 224, 255, 0.18);
            border-radius: 16px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.34);
            overflow: hidden;
        }}
        .faq-panel-inner {{
            max-height: min(78vh, 760px);
            overflow-y: auto;
            padding: 14px 14px 12px;
        }}
        .faq-title {{
            color: #f4fbff;
            font-size: 0.92rem;
            font-weight: 800;
            margin: 0 0 4px 0;
        }}
        .faq-subtitle {{
            color: rgba(193, 209, 221, 0.78);
            font-size: 0.76rem;
            line-height: 1.5;
            margin-bottom: 12px;
        }}
        .faq-item {{
            padding: 10px 0;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
        }}
        .faq-item:first-of-type {{
            border-top: none;
            padding-top: 0;
        }}
        .faq-q {{
            color: #f6fbff;
            font-size: 0.79rem;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .faq-a {{
            color: rgba(209, 220, 230, 0.84);
            font-size: 0.75rem;
            line-height: 1.52;
        }}
        .faq-footer {{
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid rgba(116, 224, 255, 0.14);
        }}
        .faq-footer-label {{
            color: #7edfff;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        .faq-version-line {{
            color: rgba(245, 250, 255, 0.92);
            font-size: 0.72rem;
            font-family: "IBM Plex Mono", Consolas, monospace;
            margin-bottom: 8px;
        }}
        .faq-changelog-line {{
            color: rgba(201, 214, 225, 0.82);
            font-size: 0.70rem;
            line-height: 1.45;
            font-family: "IBM Plex Mono", Consolas, monospace;
            word-break: break-word;
        }}
        </style>
        <details class="faq-float">
            <summary class="faq-pill">Help / FAQ</summary>
            <div class="faq-panel">
                <div class="faq-panel-inner">
                    <div class="faq-title">BRINC DFR Planning FAQ</div>
                    <div class="faq-subtitle">
                        Quick answers for upload, jurisdiction setup, fleet planning, exports, and map-layer troubleshooting.
                    </div>
                    {''.join(_faq_html_parts)}
                    <div class="faq-footer">
                        <div class="faq-footer-label">Version &amp; Changelog</div>
                        <div class="faq-version-line">Current version: v{html.escape(__version__)} | Build time: {html.escape(__build_datetime__)}</div>
                        {_changelog_lines}
                    </div>
                </div>
            </div>
        </details>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["FAQ_CHANGELOG", "_render_in_app_faq", "_render_public_report_route"]
