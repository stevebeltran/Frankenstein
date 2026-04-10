"""
Build version management for BRINC app.
"""

import datetime
from pathlib import Path

import streamlit as st

_MONSTER_NAMES = ["prom", "behe", "quasi", "drac"]
_BUILD_META_PATH = Path(".build_meta")


def _read_iteration_hint():
    """Best-effort read of the legacy build counter without mutating files."""
    try:
        if _BUILD_META_PATH.exists():
            _raw_meta = _BUILD_META_PATH.read_text(encoding="utf-8").strip()
            if _raw_meta:
                _parts = _raw_meta.split("|", 1)
                if len(_parts) == 2:
                    return max(1, int(_parts[1]))
    except (ValueError, OSError):
        pass
    return 1


def _compute_build_version():
    """Compute a read-only version string from app.py mtime."""
    _app_path = Path(__file__).resolve().parent.parent / "app.py"
    _mtime = _app_path.stat().st_mtime
    _dt = datetime.datetime.fromtimestamp(_mtime)
    _iteration = _read_iteration_hint()
    _monster_idx = min(max(_iteration - 1, 0) // 50, len(_MONSTER_NAMES) - 1)
    _monster_name = _MONSTER_NAMES[_monster_idx]
    return f"{_dt:%y}{chr(ord('A') + _dt.month - 1)}{_dt:%d}-{_monster_name}-{_dt:%H%M}.{_iteration}"


__version__ = _compute_build_version()


def _render_version_badge(position="top-right"):
    """Render version badge in top-right or bottom-right corner."""
    _placement = "top: 12px; right: 160px;" if position == "top-right" else "bottom: 12px; right: 16px;"
    st.markdown(
        f"""
        <div style="position:fixed; {_placement} z-index:9999; font-family:'IBM Plex Mono',monospace; font-size:0.62rem; letter-spacing:0.08em; color:rgba(160,175,190,0.72); background:rgba(7,10,18,0.72); border:1px solid rgba(120,140,160,0.18); border-radius:999px; padding:4px 10px; backdrop-filter: blur(6px); pointer-events:none;">
            v {__version__}
        </div>
        """,
        unsafe_allow_html=True,
    )
