"""
Page modules for DFR application.

Contains page-specific rendering logic separated from main routing.
"""

from .onboarding import render_onboarding_page
from .simulation import render_simulation_page

__all__ = [
    "render_onboarding_page",
    "render_simulation_page",
]
