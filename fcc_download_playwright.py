#!/usr/bin/env python3
"""
FCC BDC Coverage Downloader — Playwright Automation
=====================================================
Automates downloading AT&T, T-Mobile, and Verizon 4G LTE
shapefiles from broadbandmap.fcc.gov for all 50 states.

SETUP (one-time):
  pip install playwright
  playwright install chromium

USAGE:
  Step 1 — Discover page structure (opens browser, prints selectors):
    python fcc_download_playwright.py --discover

  Step 2 — Run full download (headless, ~45 min):
    python fcc_download_playwright.py

  Step 3 — Convert to GeoParquet:
    python download_fcc_coverage.py

Output: cell_coverage/raw/{STATE}_{CARRIER}.zip
"""

import sys, time, json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ─── CONFIG ───────────────────────────────────────────────────────────────────

BASE_URL   = "https://broadbandmap.fcc.gov/data-download/data-by-provider?version=jun2025&pubDataVer=jun2025"
OUTPUT_DIR = Path("cell_coverage/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CARRIERS = ["AT&T", "T-Mobile", "Verizon"]

US_STATES = [
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado",
    "Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho",
    "Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana",
    "Maine","Maryland","Massachusetts","Michigan","Minnesota",
    "Mississippi","Missouri","Montana","Nebraska","Nevada",
    "New Hampshire","New Jersey","New Mexico","New York",
    "North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
    "Pennsylvania","Rhode Island","South Carolina","South Dakota",
    "Tennessee","Texas","Utah","Vermont","Virginia","Washington",
    "West Virginia","Wisconsin","Wyoming","District of Columbia",
]

STATE_ABBR = {
    "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR",
    "California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE",
    "Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID",
    "Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS",
    "Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD",
    "Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS",
    "Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV",
    "New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
    "North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
    "Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI",
    "South Carolina":"SC","South Dakota":"SD","Tennessee":"TN",
    "Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA",
    "Washington":"WA","West Virginia":"WV","Wisconsin":"WI",
    "Wyoming":"WY","District of Columbia":"DC",
}

# ─── DISCOVERY MODE ───────────────────────────────────────────────────────────

def print_elements(page, label=""):
    """Print all interactive elements visible on the page right now."""
    print(f"\n── {label} ──")
    for sel_name, sel in [
        ("SELECT",  "select"),
        ("BUTTON",  "button"),
        ("INPUT",   "input"),
        ("LI/OPTION", "li, [role='option'], [role='listitem']"),
        ("LINKS",   "a[href]"),
    ]:
        els = page.query_selector_all(sel)
        if not els:
            continue
        print(f"  {sel_name} ({len(els)}):")
        for el in els[:8]:
            txt  = (el.inner_text() or "")[:60].replace("\n"," ").strip()
            cls  = (el.get_attribute("class") or "")[:50]
            name = el.get_attribute("name") or el.get_attribute("id") or ""
            href = el.get_attribute("href") or ""
            print(f"    name={name!r}  class={cls!r}  text={txt!r}  href={href!r}")


def discover(page):
    """Step through the page interaction and print elements at each stage."""
    print("\n" + "="*60)
    print("DISCOVERY MODE")
    print("="*60)

    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)
    print_elements(page, "INITIAL PAGE LOAD")

    # Type first carrier into provider search
    provider_input = page.query_selector('input[name="provider"]')
    if provider_input:
        print("\n  → Typing 'AT&T' into provider input …")
        provider_input.click()
        provider_input.fill("AT&T")
        time.sleep(2)
        print_elements(page, "AFTER TYPING 'AT&T'")

        # Autocomplete suggestions appear as button.dropdown-item
        suggestions = page.query_selector_all("button.dropdown-item")
        print(f"\n  Autocomplete suggestions ({len(suggestions)}):")
        for s in suggestions:
            print(f"    {(s.inner_text() or '').strip()!r}")

        if suggestions:
            # Click the first one that contains AT&T
            target = next(
                (s for s in suggestions if "at&t" in (s.inner_text() or "").lower()),
                suggestions[0]
            )
            print(f"\n  → Clicking: {(target.inner_text() or '').strip()!r}")
            target.click()
            time.sleep(3)
            print_elements(page, "AFTER SELECTING AT&T")

            # Print full page text to see what appeared
            body_text = page.inner_text("body")
            print("\n── PAGE TEXT (first 1500 chars) ──")
            print(body_text[:1500])
        else:
            print("\n  No button.dropdown-item suggestions found.")
    else:
        print("\n  provider input NOT found.")

    print("\n" + "="*60)
    print("Paste this output back so selectors can be confirmed.")
    print("="*60 + "\n")


# ─── CARRIER SEARCH TERMS ─────────────────────────────────────────────────────
# Maps our carrier label → search string → text to match in autocomplete

CARRIER_SEARCH = {
    "ATT":      {"search": "AT&T",    "match": "AT&T Inc."},
    "TMobile":  {"search": "T-Mobile","match": "T-Mobile USA"},
    "Verizon":  {"search": "Verizon", "match": "Cellco"},   # Cellco Partnership = Verizon
}

# ─── MAIN DOWNLOAD LOOP ───────────────────────────────────────────────────────

def already_downloaded(state_abbr: str, carrier_key: str) -> bool:
    return any(OUTPUT_DIR.glob(f"{state_abbr}_{carrier_key}*"))


def select_carrier(page, carrier_key: str) -> bool:
    """Type carrier name, wait for autocomplete, click matching suggestion."""
    info = CARRIER_SEARCH[carrier_key]

    inp = page.locator('input[name="provider"]')
    inp.wait_for(timeout=10000)
    inp.click()
    time.sleep(0.5)

    # Clear then type char-by-char to trigger Angular typeahead
    inp.fill("")
    inp.press_sequentially(info["search"], delay=120)
    time.sleep(2.5)   # Angular debounce needs time

    # Check if suggestions appeared
    suggestions = page.query_selector_all("button.dropdown-item")
    if not suggestions:
        # Fallback: dispatch input event manually
        page.evaluate(
            "el => { el.dispatchEvent(new Event('input', {bubbles:true})); }",
            page.query_selector('input[name="provider"]')
        )
        time.sleep(2)
        suggestions = page.query_selector_all("button.dropdown-item")

    if not suggestions:
        print(f"\n    No autocomplete suggestions appeared for '{info['search']}'")
        return False

    match_text = info["match"].lower()
    target = next(
        (s for s in suggestions if match_text in (s.inner_text() or "").lower()),
        suggestions[0]
    )

    print(f"\n    Selecting: {(target.inner_text() or '').strip()!r}")
    target.click()
    time.sleep(4)   # give Angular time to render the full download table

    # Angular sets 'name' as a bound property, not a plain HTML attribute,
    # so query_selector('select[name="selState"]') fails even when the element
    # is present. Instead validate by count: after carrier selection we expect
    # 4 selects (dataVersion + fbd-selState + selState + selState-mv).
    selects = page.query_selector_all("select")
    if len(selects) >= 3:
        # Index 2 = selState (Mobile Broadband), index 3 = selState-mv (Mobile Voice)
        print(f"\n    Page loaded — {len(selects)} selects found. Using index-based selection.")
        return True, 2   # return index of Mobile Broadband state select

    print(f"\n    Only {len(selects)} selects found — carrier page did not load.")
    return False, None


def download_state(page, state_name: str, state_abbr: str, carrier_key: str, state_sel_idx: int = 2) -> bool:
    """Select state, open Mobile Broadband download dropdown, download shapefile."""
    # Use nth-select (index 2 = Mobile Broadband state selector)
    selects = page.query_selector_all("select")
    if len(selects) <= state_sel_idx:
        raise RuntimeError(f"Expected {state_sel_idx+1}+ selects, found {len(selects)}")

    mobile_state_sel = selects[state_sel_idx]
    mobile_state_sel.select_option(label=state_name)
    time.sleep(0.6)

    # Find the Mobile Broadband Download toggle
    # Page order: Fixed CSV btn | Mobile LTE dropdown | Mobile Voice dropdown...
    dl_toggles = page.query_selector_all("button.dropdown-toggle.btn-outline-primary")
    if not dl_toggles:
        raise RuntimeError("No download dropdown toggles found")

    # Click via JavaScript to bypass any Angular event interception issues
    page.evaluate("btn => btn.click()", dl_toggles[0])
    time.sleep(1.0)   # wait for ng-bootstrap to add 'show' class

    # Find the now-visible Hexagon Coverage ESRI Shapefile item using nth (first one)
    # Use locator with visible filter to avoid stale/hidden items
    shp_locator = page.locator('[ngbdropdownitem]:has-text("Hexagon Coverage - ESRI Shapefile")').first
    try:
        shp_locator.wait_for(state="visible", timeout=4000)
        shp_btn = shp_locator.element_handle()
    except PWTimeout:
        # Fallback: try clicking the toggle again then get all dropdown items
        page.evaluate("btn => btn.click()", dl_toggles[0])
        time.sleep(1.0)
        items = page.query_selector_all('[ngbdropdownitem]')
        shp_btn = next(
            (i for i in items if "Hexagon Coverage - ESRI Shapefile" in (i.inner_text() or "")),
            None
        )
        if not shp_btn:
            raise RuntimeError("Shapefile dropdown item not visible after two attempts")

    out_path = OUTPUT_DIR / f"{state_abbr}_{carrier_key}.zip"
    with page.expect_download(timeout=120000) as dl_info:
        page.evaluate("btn => btn.click()", shp_btn)

    dl = dl_info.value
    if dl.failure():
        raise RuntimeError(f"Download failed: {dl.failure()}")

    dl.save_as(out_path)
    return out_path.stat().st_size > 1000   # must be > 1KB to be valid


def run_downloads(page, context):
    total  = len(US_STATES) * len(CARRIER_SEARCH)
    done   = 0
    failed = []

    for carrier_key in CARRIER_SEARCH:
        print(f"\n{'─'*50}")
        print(f"Carrier: {carrier_key}")
        print(f"{'─'*50}")

        # Load page fresh for each carrier
        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        ok, state_sel = select_carrier(page, carrier_key)
        if not ok:
            print(f"  ERROR: Could not select carrier {carrier_key} — skipping all states.")
            failed.extend([f"{STATE_ABBR[s]}/{carrier_key}" for s in US_STATES])
            done += len(US_STATES)
            continue

        print(f"  Carrier selected. Starting state downloads …\n")

        for state_name in US_STATES:
            abbr = STATE_ABBR[state_name]
            done += 1
            label = f"[{done}/{total}] {abbr} / {carrier_key}"

            if already_downloaded(abbr, carrier_key):
                print(f"  {label}: skipped (exists)")
                continue

            print(f"  {label} …", end=" ", flush=True)
            try:
                ok = download_state(page, state_name, abbr, carrier_key, state_sel_idx=state_sel)
                if ok:
                    size = (OUTPUT_DIR / f"{abbr}_{carrier_key}.zip").stat().st_size / 1_048_576
                    print(f"✓  ({size:.1f} MB)")
                else:
                    raise RuntimeError("File too small — likely an error page")
            except Exception as e:
                print(f"FAILED — {e}")
                failed.append(f"{abbr}/{carrier_key}")

            time.sleep(0.8)   # polite pause

    print(f"\n{'='*60}")
    print(f"Done. {done - len(failed)}/{total} files downloaded.")
    if failed:
        print(f"\nFailed ({len(failed)}): {', '.join(failed)}")
        print("Re-run the script to retry — it skips already downloaded files.")
    print(f"\nFiles saved to: {OUTPUT_DIR.resolve()}")
    print("Next step:  python download_fcc_coverage.py")


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    discover_mode = "--discover" in sys.argv
    headless = "--headless" in sys.argv   # headless only if explicitly requested

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            downloads_path=str(OUTPUT_DIR),
        )
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        if discover_mode:
            discover(page)
        else:
            run_downloads(page, context)

        browser.close()


if __name__ == "__main__":
    main()
