# BRINC COS Drone Optimizer — Frequently Asked Questions

---

## Table of Contents

1. [General](#1-general)
2. [Getting Started & Input Paths](#2-getting-started--input-paths)
3. [CAD Data Upload](#3-cad-data-upload)
4. [Simulation Mode](#4-simulation-mode)
5. [Demo Cities](#5-demo-cities)
6. [Fleet Configuration](#6-fleet-configuration)
7. [Optimization Engine](#7-optimization-engine)
8. [Coverage & Performance Metrics](#8-coverage--performance-metrics)
9. [The Map](#9-the-map)
10. [Financial Analysis & ROI](#10-financial-analysis--roi)
11. [Exports (HTML, KML, .brinc)](#11-exports-html-kml-brinc)
12. [Saving & Restoring Deployments](#12-saving--restoring-deployments)
13. [FAA Airspace & LAANC](#13-faa-airspace--laanc)
14. [Stations & Custom Infrastructure](#14-stations--custom-infrastructure)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. General

**What is the BRINC COS Drone Optimizer?**
It is a web-based planning and sales tool that helps law enforcement agencies simulate, optimize, and justify Drone-as-First-Responder (DFR) deployments. It uses real Census geography, live 911 call data (or realistic simulated data), and an integer linear programming optimizer to recommend exactly how many drones to deploy, where to place them, and what coverage and cost savings to expect.

**Who is this tool for?**
Police chiefs, city managers, grant writers, and BRINC sales engineers preparing proposals, executive briefings, or budget justifications for DFR programs.

**Does the tool require an internet connection?**
Yes, for initial setup. It pulls jurisdiction boundaries, population figures, and station locations from the US Census API, OpenStreetMap, and the FAA LAANC database. Once a session is loaded, most calculations run locally.

**What technology does it run on?**
It is a Python application built on Streamlit. Run it locally with:
```
streamlit run app.py
```
or access it through any hosted deployment URL provided by BRINC.

---

## 2. Getting Started & Input Paths

**How do I start an analysis?**
On the home screen, choose one of three input paths:

| Path | Name | Best For |
|------|------|----------|
| **Path 01** | Simulate Any US Region | Early-stage prospect with no CAD data |
| **Path 02** | Upload CAD or .brinc Save | Agencies with real incident data or returning users |
| **Path 03** | 1-Click Demo City | Live demos and stakeholder presentations |

**Can I analyze more than one jurisdiction at once?**
Yes. Path 01 lets you stack multiple cities, counties, or ZIP codes into a single run. After loading, use the **Jurisdictions** multiselect in the left sidebar to toggle areas on and off.

**Can I switch between paths mid-session?**
Yes. Use the **Start Over** option or reload the page to return to the path selection screen.

---

## 3. CAD Data Upload

**What file formats are supported?**
CSV, Excel (`.xlsx`, `.xls`, `.xlsm`, `.xlsb`), and `.brinc` save files. You can upload multiple files at once; the tool will merge them automatically.

**Does my CAD export need specific column names?**
No. The parser (`aggressive_parse_calls`) auto-detects columns across more than 200 known CAD format variants. It looks for latitude, longitude, date, time, call type, priority, and response unit fields regardless of how they are named in your export.

**What is the minimum data required?**
At minimum, each row needs a **latitude and longitude** (or an address that can be geocoded). Date/time and call type are strongly recommended for meaningful analytics but are not strictly required.

**My file has 100,000+ rows. Will that slow things down?**
The optimizer automatically samples 25,000 representative calls for the coverage computation if your dataset is larger. The full dataset is still used for all analytics charts, date range labels, and the HTML export. You will see a notification when sampling is applied.

**Can I upload a stations file alongside my CAD data?**
Yes. Upload two files at once — the tool identifies which file contains station data by filename hints (e.g., "stations", "facilities", "dept"). If it cannot determine which is which, it picks the smaller file as stations. Your station file should have columns for name, type, latitude, and longitude (or a street address).

**What if my coordinates are in a projected CRS (e.g., State Plane feet)?**
The parser detects unusually large coordinate values and attempts automatic reprojection to WGS84 (decimal degrees). It tries common UTM zones and State Plane projections. If reprojection fails, it falls back to anchoring calls to the inferred city centroid.

---

## 4. Simulation Mode

**What does simulation mode do?**
When no CAD data is available, the tool generates a realistic synthetic 911 call distribution using:
- Real jurisdiction boundaries from US Census TIGER data
- Population-weighted clustering (75% of calls in high-density hotspots, 25% random scatter)
- Total call volume estimated from population (roughly 1 call per 10 residents per year as a default)

**How accurate is the simulated data?**
It is intentionally conservative and representative, not exact. It is suitable for prospect conversations, grant estimates, and concept demonstrations. For a final deployment plan, replace simulated data with the agency's actual CAD export.

**Can I simulate multiple ZIP codes or counties?**
Yes. In Path 01, enter any combination of US city names, ZIP codes, or county names. Each is loaded as a separate jurisdiction layer that you can include or exclude from the sidebar.

---

## 5. Demo Cities

**What are the demo cities?**
Over 80 pre-configured US cities ranging from Henderson, NV to New York, NY. Each loads with realistic simulated call data, real boundaries, and OSM-sourced station locations in one click.

**What is the difference between Fast Demo and Full Demo cities?**
Fast Demo cities are smaller jurisdictions (typically under 500,000 population) that load in under 10 seconds. Full Demo cities include major metros and take 15–30 seconds to process due to boundary complexity and station lookup.

**Can I use a demo city as a starting point and then upload real CAD data?**
Not directly within the same session. Start a new session with Path 02 and upload your CAD file to work with real data.

---

## 6. Fleet Configuration

**What is a Responder drone?**
A short-range tactical unit (default 2-mile radius) designed to arrive at a scene before a patrol car. Unit cost: **$80,000**. Travel speed: **42 mph**. Typical sortie time: 30 minutes.

**What is a Guardian drone?**
A long-range overwatch unit (default 8-mile radius) designed for wide-area surveillance, pursuit tracking, and perimeter control. Unit cost: **$160,000**. Travel speed: **60 mph**. Duty cycle: 60-minute flight / 3-minute charge, yielding approximately **23.5 hours of daily airtime**.

**How do I set fleet size?**
Use the **Responder Count** and **Guardian Count** sliders in the left sidebar (section ② Optimize Fleet). The tool enforces a minimum fleet recommendation of 1 Guardian plus enough Responders to reach 85% call coverage.

**What does the Responder Range slider do?**
It sets the coverage radius used in the optimization (2.0–3.0 miles). Increasing it covers more incidents per drone at the cost of slightly longer average response times.

**What is the Guardian Range slider?**
Sets the Guardian coverage radius (1–8 miles). At 5 miles, the tool also draws a **Rapid Response Focus Zone** inner ring on the map showing the tightest high-priority coverage area.

**What is DFR Dispatch Rate?**
The percentage of covered 911 calls that would actually be dispatched to a drone. Default: **25%**. This reflects that not every incident type benefits from a drone response (e.g., report-only calls may be excluded).

**What is Deflection Rate?**
The percentage of drone-dispatched calls where the drone response fully resolves the situation without requiring a patrol car. Default: **30%**. This drives overtime savings and cost-per-call calculations.

---

## 7. Optimization Engine

**How does the optimizer work?**
It uses the **Maximum Coverage Location Problem (MCLP)**, solved with integer linear programming (via the PuLP library and the CBC solver). The objective is to select station locations that maximize the number of weighted incidents covered within the configured radius, subject to the fleet size budget.

**What does "Phased Rollout" mean?**
When enabled (default), the optimizer solves Guardians first, then places Responders to complement them — filling gaps the Guardians leave. When disabled, both fleets are solved simultaneously in a single pass, which can yield a slightly different (sometimes better) joint result.

**Can I force a drone to be placed at a specific station?**
Yes. Use the **Pin** button on any station in the map or the station list. Pinned stations are locked into the solution and the optimizer places remaining drones around them.

**What does "Allow Overlap" do?**
By default, Responders and Guardians cannot be assigned to the same physical station. Enabling overlap allows co-location, which is useful for small jurisdictions with limited infrastructure.

**The optimizer says "Solver timed out." What does that mean?**
The CBC solver has a 10-second time limit. For very large instances (many stations, large call sets), it may return the best solution found so far rather than the proven optimum. The result is still a high-quality coverage plan.

**What is the Deployment Strategy option?**
Controls how Guardians are positioned relative to Responders:
- **Complement — push apart**: Guardians fill geographic gaps left by Responders
- **Independent — each maximises own area**: Each fleet is optimized for its own coverage independently

---

## 8. Coverage & Performance Metrics

**What is Call Coverage %?**
The percentage of all modeled 911 incidents that fall within the coverage radius of at least one drone. This is the primary metric for deployment quality.

**What is Area Coverage %?**
The percentage of the total jurisdiction area covered by at least one drone's radius. A high area coverage with lower call coverage indicates that incidents are concentrated in uncovered zones — a cue to adjust station placement.

**What is Average Response Time?**
The estimated average flight time (in minutes) from the nearest assigned drone to each covered incident, using straight-line distance at the drone's configured airspeed.

**What is Time Saved vs. Patrol?**
The difference between estimated patrol car response time (ground speed adjusted for traffic congestion) and drone flight time. A routing factor of 1.4× is applied to ground distance to account for road geometry.

**What is the Elbow Curve chart?**
A chart showing call and area coverage versus fleet size (1 to 100 drones). The "elbow" — where the curve flattens — indicates the point of diminishing returns. This helps justify the recommended fleet size to budget-conscious stakeholders.

---

## 9. The Map

**What does the map show?**
- **Incident heatmap** or individual call points (toggle via Display Options)
- **Coverage circles** for each deployed drone (colored by drone type)
- **Station markers** with hover cards showing drone type, response time, FAA ceiling, and cost
- **Jurisdiction boundary** outline
- **FAA LAANC airspace** zones (if loaded)
- **5-mile Rapid Response Focus Zone** rings for Guardian units
- **Traffic simulation** overlay (optional, shows estimated ground-speed impact)

**Can I toggle layers on and off?**
Yes. The **Display Options** expander in the sidebar controls boundaries, heatmap vs. points, satellite imagery, traffic, and FAA airspace.

**How do I use Satellite view?**
Enable **Satellite Imagery** in Display Options. This overlays Esri World Imagery on the carto-positron basemap.

**The map is blank or not loading. What should I check?**
1. Confirm that jurisdiction boundaries loaded successfully (check for error banners)
2. Try a different browser — the map requires WebGL support
3. Check that at least one jurisdiction is selected in the sidebar multiselect

---

## 10. Financial Analysis & ROI

**How is CapEx calculated?**
`CapEx = (Responder Count × $80,000) + (Guardian Count × $160,000)`

**How is Annual Savings calculated?**
Based on the number of calls deflected from patrol (calls covered × DFR dispatch rate × deflection rate), multiplied by the cost difference between an officer response ($82/call) and a drone response ($6/call).

**What is the Break-Even timeline?**
`CapEx ÷ Annual Savings`. This is the number of years for the fleet to pay for itself through avoided patrol costs alone, not counting officer overtime relief, specialty response savings, or grant funding.

**How are overtime savings estimated?**
The tool analyzes peak-hour call density from CAD data (or simulated data) to identify high-activity periods. It estimates the reduction in overtime cost when drone deflection removes calls from those surge periods. Officer hourly wage is set to a configurable baseline (default: $37/hour × 1.5 OT multiplier).

**How are Thermal and K9 savings calculated?**
A portion of calls are flagged as applicable for thermal imaging or K9 support. Savings per applicable call are based on configured rates in the system:
- Thermal: ~12% applicable rate, ~$38 saved per call
- K9: ~3% applicable rate, ~$155 saved per call

**Are the financial figures guaranteed?**
No. All financial outputs are modeled estimates based on industry benchmarks and the parameters you configure. They are intended for planning and grant-writing purposes. Actual results will vary by jurisdiction, deployment practices, and agency operations.

---

## 11. Exports (HTML, KML, .brinc)

**What does the HTML export contain?**
A standalone, print-ready executive summary document with:
1. Deployment overview (fleet, coverage, response times)
2. Incident analysis with CAD charts
3. Infrastructure map with coverage circles
4. Staffing pressure and overtime analysis
5. Financial ROI and break-even analysis
6. Grant funding sources and estimated amounts
7. Peer agency comparisons
8. Full analytics dashboard
9. Drone deployment details table

**What does the KML export contain?**
A Google Earth briefing file with:
- Coverage radius circles for each deployed drone
- Incident heatmap layer
- Station placemarks with detailed pop-up cards
- FAA airspace proximity markers
- Jurisdiction boundary polygon

Open the `.kml` file in Google Earth Pro or import it into Google Maps for stakeholder briefings.

**What is a .brinc file?**
A JSON save file containing the complete deployment state — call data, station locations, fleet configuration, city/state, and all slider settings. Share it with a colleague or reload it later to pick up exactly where you left off.

**How do I generate the HTML export?**
After the map and metrics are loaded, scroll to the export section and click **Download Executive Summary (HTML)**. The file is generated on demand and includes all current slider values and optimization results.

---

## 12. Saving & Restoring Deployments

**How do I save my deployment?**
Click **Download .brinc Save File** in the export section. This saves the current session as a `.brinc` file to your computer.

**How do I restore a saved deployment?**
On the home screen, choose **Path 02 — Upload CAD or .brinc Save** and upload your `.brinc` file. The tool restores the city, fleet settings, call data, and station positions exactly as saved.

**Can I share a .brinc file with a colleague?**
Yes. Send them the `.brinc` file and they can load it via Path 02. Note that the tool validates the file on load — if it is corrupted or missing coordinate data, a clear error message will be shown.

**Does a .brinc file include sensitive call data?**
Yes — it contains the latitude/longitude of all modeled 911 incidents. Handle it with the same care as any law enforcement operational data. Do not share externally without approval from the agency.

---

## 13. FAA Airspace & LAANC

**Does the tool show FAA airspace restrictions?**
Yes. FAA LAANC facility map data is bundled with the app (updated periodically). Drone stations are automatically checked against LAANC zones and each drone's hover card shows its applicable **FAA ceiling** (e.g., "400 ft AGL", "200 ft AGL", "0 ft — Waiver Required").

**What do the LAANC ceiling colors mean?**

| Ceiling | Color | Meaning |
|---------|-------|---------|
| 400 ft AGL | Green | Standard LAANC authorization available |
| 200 ft AGL | Yellow | Reduced ceiling — check local NOTAMs |
| 100 ft AGL | Orange | Significantly restricted — waiver likely required |
| 0 ft | Red | Authorization required before any flight |

**What is the nearest airfield indicator?**
Each drone station card shows the bearing and distance to the nearest airfield (airport, helipad, or airstrip) within range. This is informational — actual flight authorization must be obtained through LAANC or FAA DroneZone regardless of distance.

**Is the FAA data real-time?**
No. The bundled FAA LAANC data is a static snapshot. Always verify current airspace status through the official FAA B4UFLY app or DroneZone before any actual flight operations.

---

## 14. Stations & Custom Infrastructure

**Where do station locations come from?**
By default, the tool queries **OpenStreetMap** for police stations, fire stations, and schools within the jurisdiction. These serve as candidate placement sites for the optimizer.

**What if OSM returns no stations?**
The tool automatically falls back to generating up to 100 randomly distributed candidate sites across the jurisdiction. A notice is shown when this fallback is used. You can override with a custom stations file.

**How do I use my own station list?**
Upload a CSV or Excel file alongside your CAD file in Path 02. The file should have columns for name, type, and either lat/lon coordinates or a street address. If addresses are provided, the tool geocodes them via Nominatim (allow extra time for large lists).

**Can I add a station manually on the map?**
Yes. Use the **Add Custom Station** control in the sidebar. Click the map to place a new candidate site, give it a name and type, and it will be included as an optimizer candidate.

**Can I remove a station from the analysis?**
Yes. Select the station and use the **Remove** option. Removed stations are excluded from the current session's optimization.

---

## 15. Troubleshooting

**"Could not parse valid coordinates" error on CAD upload.**
- Confirm your file has latitude and longitude columns (or address columns)
- Check that numeric columns are not formatted as text (remove commas, degree symbols, etc.)
- Try exporting as CSV from your CAD system instead of Excel
- Ensure the file is not password-protected

**The optimizer runs but coverage is very low (under 30%).**
- Increase fleet size using the Responder/Guardian sliders
- Increase the Responder Range radius
- Check that the correct jurisdiction is selected — an unusually large boundary will dilute coverage
- Verify station locations are within the jurisdiction (check the map)

**The map loads but shows no coverage circles.**
- Confirm at least 1 Responder or 1 Guardian is assigned (sliders above 0)
- Ensure the optimization has completed (spinner should be gone)
- Try toggling the jurisdiction boundary off and back on to trigger a re-render

**The HTML export is blank or missing sections.**
- Ensure you have scrolled through the full dashboard before exporting — some sections initialize on first render
- Check the browser console for JavaScript errors
- Try a different browser (Chrome or Edge recommended)

**Geocoding is slow when loading custom stations.**
- The tool respects Nominatim's rate limit of ~1 request per second
- For large station lists (50+ rows), allow 1–2 minutes for geocoding to complete
- Pre-geocoding your station list (adding lat/lon columns) will skip this step entirely

**The .brinc file fails to restore.**
- Confirm the file has not been edited manually — it must be valid JSON
- Ensure it was exported from a compatible version of the tool
- If the file reports missing lat/lon, the original session may have had a data parsing issue — re-upload the original CAD file instead

**Session data disappears after a few minutes of inactivity.**
Streamlit sessions are stateful but not persistent across page refreshes or server timeouts. Save your work as a `.brinc` file before stepping away from an active session.

---

*For additional support, contact your BRINC sales engineer or technical team.*
