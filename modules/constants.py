"""
Magic number constants for the application.

Centralizes hard-coded values to improve maintainability and make configuration changes easier.
"""

# ── API & Network Timeouts (seconds) ──────────────────────────────────────────
API_TIMEOUT_DEFAULT = 8
API_TIMEOUT_QUICK = 2
API_TIMEOUT_STANDARD = 6
API_TIMEOUT_LONG = 10
API_TIMEOUT_EXTENDED = 15
API_TIMEOUT_VERY_LONG = 45

OVERPASS_TIMEOUT = 20  # Overpass API query timeout
CONCURRENT_REQUEST_TIMEOUT = 12  # Timeout for concurrent futures operations

# ── Geospatial Constants ──────────────────────────────────────────────────────
METERS_PER_DEGREE_LATITUDE = 111000.0  # Approximate meters per degree of latitude
LATITUDE_MIN = -90.0
LATITUDE_MAX = 90.0
LONGITUDE_MIN = -180.0
LONGITUDE_MAX = 180.0

# ── Radio Frequency & Path Loss ───────────────────────────────────────────────
FREQUENCY_HZ = 3.39e9  # Guardian/Responder frequency (3390 MHz)
FREQUENCY_MHZ = 3390  # Same as above, in MHz
FSPL_COEFFICIENT = 27.55  # Free-space path loss constant (20*log10(4π/c))
TX_ALTITUDE_M = 9.14  # Transmitter altitude (30 feet in meters)
RX_ALTITUDE_M = 61.0  # Receiver altitude (200 feet in meters)

# ── Terrain & Propagation Model ───────────────────────────────────────────────
FRESNEL_BLOCKAGE_THRESHOLD = 0.6  # Fresnel zone blockage threshold ratio
TERRAIN_BLOCKAGE_CRITICAL_RATIO = 0.1  # Ratio triggering terrain loss calculation
TERRAIN_BLOCKAGE_LOSS_COEFFICIENT = 6.0  # Knife-edge diffraction loss scaling
TERRAIN_BLOCKAGE_LOSS_MAX = 25.0  # Maximum terrain loss in dB

CLUTTER_LOSS = {
    "urban": {"base": 18.0, "var": 8.0},
    "suburban": {"base": 12.0, "var": 5.0},
    "rural": {"base": 6.0, "var": 3.0},
    "water": {"base": 2.0, "var": 1.0},
}

FADE_MARGIN_DB = 3.0  # Rayleigh/urban multipath fade margin

# ── Elevation & Distance ──────────────────────────────────────────────────────
ELEVATION_DEFAULT_FT = 100.0  # Default elevation in feet when unavailable
MIN_DISTANCE_FOR_TERRAIN_CALC = 100.0  # Minimum distance in meters for terrain blockage calculation
MIN_DISTANCE_FOR_PATH_LOSS = 10.0  # Minimum distance in meters to compute path loss

# ── Map & Visualization ───────────────────────────────────────────────────────
MARKER_SIZE = 5
MARKER_OPACITY = 0.6
MARKER_OPACITY_FILL = 0.15
MARKER_OPACITY_FILL_LIGHT = 0.16
MARKER_OPACITY_FILL_SHADOW = 0.18
MARKER_OPACITY_FILL_DARKEST = 0.25

SHADOW_BLUR_PIXELS = 10
SHADOW_SPREAD_PIXELS = 24

# ── OSM Station Search Radii ──────────────────────────────────────────────────
OSM_SEARCH_RADIUS_SMALL = 0.25  # ~25 km in degrees
OSM_SEARCH_RADIUS_LARGE = 0.45  # ~45 km in degrees
OSM_MAX_STATIONS = 200

# ── Geocoding & Address Matching ──────────────────────────────────────────────
ADDRESS_CANDIDATES_DEFAULT_LIMIT = 6
REVERSE_GEOCODING_SEARCH_DISTANCE = 2  # Miles

# ── Data Processing ──────────────────────────────────────────────────────────
COORDINATE_PRECISION = 6  # Decimal places for rounding coordinates
COORDINATE_ROUNDING_CACHE = 2  # Decimal places for cache keys

# ── Performance & Optimization ───────────────────────────────────────────────
SKLEARN_RANDOM_STATE = 42  # Fixed seed for reproducible clustering
SKLEARN_BATCH_SIZE = 1024  # MiniBatchKMeans batch size
SKLEARN_N_INIT = 3  # Number of initializations for KMeans
