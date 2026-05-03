"""Compatibility shim for code that expects ``streamlit_extras``.

The deployed environment for this app does not include the third-party
``streamlit_extras`` package, but the app only needs the components API.
Expose it locally by forwarding to Streamlit's built-in implementation.
"""

from . import components

__all__ = ["components"]
