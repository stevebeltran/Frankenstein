"""
Data export and report generation helper utilities.

Provides functions for preparing deployment data for export in various formats
(CSV, KML, Shapefile) and generating public reports.
"""

from typing import Optional

import pandas as pd


def _build_corrected_export_from_merged_fallback(
    merged_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """Clean and prepare a merged incident DataFrame for export.

    Removes temporary merge metadata columns and ensures coordinate columns
    are properly numeric.

    Args:
        merged_df: DataFrame with merged call and census data, or None

    Returns:
        Cleaned DataFrame ready for export
    """
    export_df = pd.DataFrame() if merged_df is None else merged_df.copy().reset_index(drop=True)
    export_df = export_df.drop(columns=['_census_merge_key', '_census_filled'], errors='ignore')
    if 'lat' in export_df.columns:
        export_df['lat'] = pd.to_numeric(export_df['lat'], errors='coerce')
    if 'lon' in export_df.columns:
        export_df['lon'] = pd.to_numeric(export_df['lon'], errors='coerce')
    return export_df
