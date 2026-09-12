from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re
import json
import base64
import pandas as pd
import streamlit as st

from sheets_handler import (
    get_all_visits,
    find_open_visit,
    create_in_visit,
    complete_out_visit,
)
from report_manager import dataframe_to_excel_bytes
from github_reports import upload_or_update_report, list_reports, download_report, report_sync_due, mark_report_synced

APP_TITLE = "Customer Care Day"
GPS_TOLERANCE_METERS = 100
GPS_WARNING_METERS = 200
MAX_ACCEPTABLE_GPS_ACCURACY_METERS = 1000

st.set_page_config(page_title=APP_TITLE, page_icon="💚", layout="centered")

# Mobile/PWA-style metadata. Streamlit is still the hosted web application,
# but supported mobile browsers can add it to the home screen as
# "Customer Care Day" with a standalone app-like appearance.
PWA_ICON = os.path.join(os.path.dirname(__file__), "assets", "customer_care_day_icon.png")
if os.path.exists(PWA_ICON):
    try:
        with open(PWA_ICON, "rb") as _icon_file:
            _icon_b64 = base64.b64encode(_icon_file.read()).decode("ascii")
        _icon_data = f"data:image/png;base64,{_icon_b64}"
        _manifest = {
            "name": "Customer Care Day",
            "short_name": "Customer Care Day",
            "start_url": "https://csdattendance.streamlit.app/",
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#063b91",
            "theme_color": "#063b91",
            "icons": [
                {"src": _icon_data, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
            ],
        }
        _manifest_b64 = base64.b64encode(json.dumps(_manifest).encode()).decode("ascii")
        st.html(
            f"""
            <script>
            (() => {{
                // App-style metadata. This is intentionally injected at runtime because
                // Streamlit serves the application shell itself. Supported browsers can
                // use these settings for Add to Home Screen / installed-app display.
                const manifest = document.createElement('link');
                manifest.rel = 'manifest';
                manifest.href = 'data:application/manifest+json;base64,{_manifest_b64}';
                document.head.appendChild(manifest);

                const metas = [
                    ['mobile-web-app-capable', 'yes'],
                    ['apple-mobile-web-app-capable', 'yes'],
                    ['apple-mobile-web-app-status-bar-style', 'black-translucent'],
                    ['apple-mobile-web-app-title', 'Customer Care Day'],
                    ['theme-color', '#063b91']
                ];
                metas.forEach(([name, content]) => {{
                    if (!document.head.querySelector(`meta[name=\"${{name}}\"]`)) {{
                        const m = document.createElement('meta');
                        m.name = name;
                        m.content = content;
                        document.head.appendChild(m);
                    }}
                }});

                // Hide the browser-style Streamlit chrome as much as possible when the
                // site is launched in standalone/installed mode.
                const style = document.createElement('style');
                style.textContent = `
                    @media (display-mode: standalone) {{
                        [data-testid=\"stHeader\"] {{ min-height: 0 !important; }}
                        [data-testid=\"stToolbar\"] {{ display: none !important; }}
                    }}
                `;
                document.head.appendChild(style);
            }})();
            </script>
            """,
            unsafe_allow_javascript=True,
        )
    except Exception:
        pass

# PSO / We Care. You Drive campaign theme
st.markdown("""
<style>
    :root {
        --ccd-blue: #063b91;
        --ccd-blue-2: #0758bd;
        --ccd-green: #12a84a;
        --ccd-green-dark: #087b3b;
        --ccd-yellow: #ffd21c;
        --ccd-light: #f3f8ff;
        --ccd-border: #c9def8;
        --ccd-text: #083b83;
    }
    .stApp {
        background: linear-gradient(180deg, #eef6ff 0%, #ffffff 52%, #eef7ff 100%);
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 760px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    .ccd-hero {
        border-radius: 0 0 22px 22px;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(6,59,145,.16);
        margin-bottom: 12px;
    }
    .ccd-title {
        background: linear-gradient(135deg, var(--ccd-blue), #064aa5);
        color: white;
        border-radius: 16px;
        padding: 16px 18px;
        margin: 8px 0 14px;
        box-shadow: 0 6px 18px rgba(6,59,145,.14);
    }
    .ccd-title h1 {
        margin: 0;
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: .2px;
    }
    .ccd-title p {
        margin: 5px 0 0;
        opacity: .95;
        font-size: .94rem;
    }
    .ccd-section {
        color: var(--ccd-text);
        font-weight: 800;
        font-size: 1.2rem;
        margin: 12px 0 8px;
    }
    .ccd-info {
        background: linear-gradient(135deg, #eef8ff, #ffffff);
        border: 1px solid var(--ccd-border);
        border-left: 5px solid var(--ccd-green);
        border-radius: 12px;
        padding: 11px 13px;
        color: #174d91;
        margin: 8px 0 12px;
    }
    .ccd-step {
        background: white;
        border: 1px solid var(--ccd-border);
        border-radius: 18px;
        padding: 16px 15px 12px;
        margin: 12px 0;
        box-shadow: 0 5px 18px rgba(6,59,145,.09);
    }
    .ccd-step h3 {
        color: var(--ccd-text);
        margin: 0 0 6px;
        font-size: 1.18rem;
    }
    .ccd-step p {
        color: #315a91;
        margin: 3px 0;
    }
    .ccd-summary {
        background: white;
        border: 1px solid var(--ccd-border);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 6px 20px rgba(6,59,145,.10);
    }
    .ccd-summary-head {
        background: linear-gradient(90deg, var(--ccd-blue), var(--ccd-blue-2));
        color: white;
        padding: 11px 14px;
        font-weight: 800;
        font-size: 1.05rem;
    }
    .ccd-progress {
        display:flex;
        align-items:center;
        gap:0;
        margin: 8px 2px 15px;
    }
    .ccd-dot {
        width:30px; height:30px; border-radius:50%;
        display:flex; align-items:center; justify-content:center;
        font-weight:800; font-size:.82rem;
        background:#e8f1fc; color:var(--ccd-text);
        border:2px solid #c6ddf7;
        flex:0 0 30px;
    }
    .ccd-dot.active, .ccd-dot.done {
        background:var(--ccd-green); color:white; border-color:var(--ccd-green);
    }
    .ccd-line { height:4px; background:#dce9f8; flex:1; }
    .ccd-line.done { background:var(--ccd-green); }
    div[data-testid="stForm"] {
        background: white;
        border: 1px solid var(--ccd-border);
        border-radius: 18px;
        padding: 18px 16px 8px;
        box-shadow: 0 5px 18px rgba(6,59,145,.08);
    }
    div[data-testid="stTextInput"] label {
        color: var(--ccd-text);
        font-weight: 700;
    }
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        border-radius: 11px;
        min-height: 48px;
        font-weight: 800;
        border: 0;
    }
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, var(--ccd-green), var(--ccd-green-dark));
        color: white;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--ccd-green), var(--ccd-green-dark));
        color: white;
    }
    .ccd-footer {
        text-align:center;
        color:#42648f;
        font-size:.78rem;
        margin-top:18px;
        padding:10px;
    }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] { padding-left: .75rem; padding-right: .75rem; }
        .ccd-title h1 { font-size: 1.35rem; }
        .ccd-hero { border-radius: 0 0 18px 18px; }
    }
</style>
""", unsafe_allow_html=True)

HERO_IMAGE = os.path.join(os.path.dirname(__file__), "assets", "customer_care_day_banner.jpg")


def show_brand_header(show_title=True):
    if os.path.exists(HERO_IMAGE):
        st.markdown('<div class="ccd-hero">', unsafe_allow_html=True)
        st.image(HERO_IMAGE, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    if show_title:
        st.markdown('<div class="ccd-title"><h1>Customer Care Day</h1><p>WE CARE. YOU DRIVE.</p></div>', unsafe_allow_html=True)


def show_install_help():
    # Compact installation instructions. The actual install prompt is browser-controlled.
    st.html(
        """
        <div class="ccd-info" id="ccd-install-card">
          <strong>📱 Install Customer Care Day</strong><br>
          <span id="ccd-install-text">Use your browser menu and choose <b>Add to Home Screen</b> or <b>Install app</b>.</span>
          <button id="ccd-install-btn" style="display:none;margin-top:10px;width:100%;padding:11px;border:0;border-radius:10px;background:#12a84a;color:#fff;font-weight:800;font-size:15px;">Install Customer Care Day</button>
          <div id="ccd-ios-help" style="display:none;margin-top:8px;font-size:13px;">On iPhone/iPad: open this page in Safari → <b>Share</b> → <b>Add to Home Screen</b> → <b>Add</b>.</div>
          <div id="ccd-android-help" style="display:none;margin-top:8px;font-size:13px;">On Android: open in Chrome → <b>⋮</b> → <b>Install app</b> or <b>Add to Home screen</b>.</div>
        </div>
        <script>
        (() => {
          let deferredPrompt = null;
          const btn = document.getElementById('ccd-install-btn');
          const text = document.getElementById('ccd-install-text');
          const ios = document.getElementById('ccd-ios-help');
          const android = document.getElementById('ccd-android-help');
          const standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
          const ua = navigator.userAgent || '';
          const isiOS = /iPhone|iPad|iPod/i.test(ua);
          const isAndroid = /Android/i.test(ua);
          if (standalone) {
            text.innerHTML = '<b>Customer Care Day is installed.</b> Open it from your home screen.';
          } else if (isiOS) {
            ios.style.display = 'block';
            text.textContent = 'Install it once so you can open Customer Care Day from your home screen.';
          } else if (isAndroid) {
            android.style.display = 'block';
          }
          window.addEventListener('beforeinstallprompt', (event) => {
            event.preventDefault();
            deferredPrompt = event;
            btn.style.display = 'block';
          });
          btn.addEventListener('click', async () => {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            await deferredPrompt.userChoice;
            deferredPrompt = null;
            btn.style.display = 'none';
          });
          window.addEventListener('appinstalled', () => {
            btn.style.display = 'none';
            text.innerHTML = '<b>Customer Care Day is installed.</b> Open it from your home screen.';
          });
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def show_progress(active_step):
    parts = []
    for i in range(1, 5):
        cls = "done" if i < active_step else ("active" if i == active_step else "")
        parts.append(f'<div class="ccd-dot {cls}">{i}</div>')
        if i < 4:
            line_cls = "done" if i < active_step else ""
            parts.append(f'<div class="ccd-line {line_cls}"></div>')
    st.markdown('<div class="ccd-progress">' + ''.join(parts) + '</div>', unsafe_allow_html=True)


for key, default in {
    "employee_code": "",
    "employee_name": "",
    "outlet_code": "",
    "outlet_name": "",
    "in_location": None,
    "out_location": None,
    "admin_logged_in": False,
    "last_message": "",
    "open_visit": None,
    "details_loaded": False,
    "scroll_target": None,
    "completed_visit": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def now_local():
    return datetime.now(ZoneInfo("Asia/Karachi"))


def auto_scroll_if_needed(anchor_id, delay_ms=180):
    """Scroll once to an anchor requested by the previous user action."""
    if st.session_state.get("scroll_target") != anchor_id:
        return
    safe_id = str(anchor_id).replace("\\", "").replace("'", "\\'")
    st.session_state["scroll_target"] = None
    st.html(
        f"""
        <div id=\"{safe_id}\" style=\"height:1px;margin:0;padding:0;\"></div>
        <script>
        (() => {{
            const id = {safe_id!r};
            setTimeout(() => {{
                const el = document.getElementById(id);
                if (el) el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
            }}, {int(delay_ms)});
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


# Streamlit 1.52+ Components V2 lets the browser geolocation API run directly
# in the app page instead of inside the old iframe-based component.
GPS_COMPONENT = st.components.v2.component(
    name="petrol_station_gps",
    html="""
        <div class="gps-box">
            <button id="gps-button" type="button">📍 Get Current GPS</button>
            <div id="gps-status" class="gps-status">Ready to capture location.</div>
        </div>
    """,
    css="""
        .gps-box { width: 100%; font-family: var(--st-font); }
        #gps-button {
            width: 100%;
            border: 1px solid var(--st-primary-color);
            border-radius: 0.5rem;
            padding: 0.65rem 0.75rem;
            background: linear-gradient(135deg, var(--ccd-blue), var(--ccd-blue-2));
            color: white;
            font-size: 1rem;
            cursor: pointer;
        }
        #gps-button:disabled { opacity: 0.65; cursor: wait; }
        .gps-status { margin-top: 0.4rem; font-size: 0.9rem; color: var(--st-text-color); }
    """,
    js="""
        export default function({ parentElement, setStateValue }) {
            const button = parentElement.querySelector('#gps-button');
            const status = parentElement.querySelector('#gps-status');

            if (!button || button.dataset.bound === '1') return;
            button.dataset.bound = '1';

            // Keep the browser watch attached to the DOM element so Streamlit
            // reruns do not accidentally start multiple GPS watches.
            parentElement._gpsWatchId = null;
            parentElement._gpsTimer = null;
            parentElement._bestAccuracy = Infinity;
            parentElement._bestLocation = null;

            const stopWatch = () => {
                if (parentElement._gpsWatchId !== null) {
                    navigator.geolocation.clearWatch(parentElement._gpsWatchId);
                    parentElement._gpsWatchId = null;
                }
                if (parentElement._gpsTimer !== null) {
                    clearTimeout(parentElement._gpsTimer);
                    parentElement._gpsTimer = null;
                }
                button.disabled = false;
            };

            const publish = (position, final = false) => {
                const c = position.coords;
                const accuracy = Number(c.accuracy);
                if (!Number.isFinite(c.latitude) || !Number.isFinite(c.longitude)) return;

                // Keep the most accurate reading received during the watch.
                if (Number.isFinite(accuracy) && accuracy < parentElement._bestAccuracy) {
                    parentElement._bestAccuracy = accuracy;
                    parentElement._bestLocation = {
                        latitude: c.latitude,
                        longitude: c.longitude,
                        accuracy: accuracy,
                        altitude: c.altitude,
                        altitudeAccuracy: c.altitudeAccuracy,
                        heading: c.heading,
                        speed: c.speed,
                        timestamp: position.timestamp
                    };
                    setStateValue('location', parentElement._bestLocation);
                    setStateValue('error', null);
                    setStateValue('requesting', true);
                    status.textContent = `Best GPS accuracy so far: ${Math.round(accuracy)} m. Waiting for a better fix...`;

                    // A very good fix has been obtained; no need to wait longer.
                    if (accuracy <= 50) {
                        status.textContent = `GPS captured — accuracy about ${Math.round(accuracy)} m.`;
                        setStateValue('requesting', false);
                        stopWatch();
                    }
                }

                if (final) {
                    const best = parentElement._bestLocation;
                    if (best) {
                        status.textContent = `GPS captured — best accuracy about ${Math.round(best.accuracy)} m.`;
                        setStateValue('location', best);
                        setStateValue('requesting', false);
                    }
                    stopWatch();
                }
            };

            button.onclick = () => {
                if (!window.isSecureContext) {
                    const message = 'Location requires a secure HTTPS connection.';
                    status.textContent = message;
                    setStateValue('error', message);
                    return;
                }

                if (!navigator.geolocation) {
                    const message = 'This browser does not provide geolocation.';
                    status.textContent = message;
                    setStateValue('error', message);
                    return;
                }

                stopWatch();
                parentElement._bestAccuracy = Infinity;
                parentElement._bestLocation = null;
                button.disabled = true;
                status.textContent = 'Searching for the best GPS fix... Keep the phone still and wait up to 30 seconds.';
                setStateValue('location', null);
                setStateValue('error', null);
                setStateValue('requesting', true);

                const options = {
                    enableHighAccuracy: true,
                    maximumAge: 0,
                    timeout: 30000
                };

                parentElement._gpsWatchId = navigator.geolocation.watchPosition(
                    (position) => publish(position, false),
                    (error) => {
                        const best = parentElement._bestLocation;
                        if (best) {
                            status.textContent = `GPS captured — best accuracy about ${Math.round(best.accuracy)} m.`;
                            setStateValue('location', best);
                            setStateValue('error', null);
                            setStateValue('requesting', false);
                            stopWatch();
                            return;
                        }
                        let message = error.message || 'Unable to obtain location.';
                        if (error.code === 1) message = 'Location permission was denied by the browser.';
                        if (error.code === 2) message = 'Location is currently unavailable. Please ensure phone Location/GPS is ON.';
                        if (error.code === 3) message = 'Location request timed out. Please try again.';
                        status.textContent = message;
                        setStateValue('error', `GPS error ${error.code}: ${message}`);
                        setStateValue('requesting', false);
                        stopWatch();
                    },
                    options
                );

                // Do not reject a valid coordinate merely because Android reports
                // a large accuracy radius. Some devices initially report 1000–3000m
                // and improve after several seconds. If it does not improve, the
                // best available coordinate is still returned to the app.
                parentElement._gpsTimer = setTimeout(() => {
                    if (parentElement._bestLocation) {
                        publish({coords: parentElement._bestLocation, timestamp: parentElement._bestLocation.timestamp}, true);
                    } else {
                        status.textContent = 'No GPS coordinate received. Please try again with Location/GPS ON.';
                        setStateValue('error', 'No GPS coordinate was received.');
                        setStateValue('requesting', false);
                        stopWatch();
                    }
                }, 30000);
            };
        }
    """,
)


def get_location(component_key, label):
    """Capture GPS using the browser's native Geolocation API."""
    st.caption("Turn ON phone Location/GPS and allow location permission.")

    result = GPS_COMPONENT(
        key=component_key,
        default={"location": None, "error": None, "requesting": False},
        on_location_change=lambda: None,
        on_error_change=lambda: None,
        on_requesting_change=lambda: None,
    )

    location = getattr(result, "location", None)
    error = getattr(result, "error", None)

    if error:
        st.error(error)
        return None

    if location and location.get("latitude") is not None:
        captured = {
            "latitude": float(location["latitude"]),
            "longitude": float(location["longitude"]),
            "accuracy": float(location["accuracy"]) if location.get("accuracy") is not None else None,
        }
        st.success(f"{label} GPS location captured.")
        st.write(f"Latitude: `{captured['latitude']:.6f}`")
        st.write(f"Longitude: `{captured['longitude']:.6f}`")
        if captured["accuracy"] is not None:
            st.write(f"Accuracy: approximately `{captured['accuracy']:.0f} metres`")
        return captured

    return None


def location_ok(location):
    if not location:
        return False, "Please capture your current GPS location."
    lat = location.get("latitude")
    lon = location.get("longitude")
    accuracy = location.get("accuracy")
    if lat is None or lon is None:
        return False, "GPS coordinates were not received."
    # Do not block attendance because the browser reports a large accuracy radius.
    # Android/browser location may initially report a coarse fix (e.g. 1000–3000 m)
    # even when the coordinate itself is usable. The actual reported accuracy is
    # stored in the sheet for audit purposes.
    return True, ""


def validate_details(employee_code, employee_name, outlet_code, outlet_name):
    """Validate required fields and the requested character types."""
    errors = []
    if not employee_code:
        errors.append("Employee Code is mandatory.")
    elif not re.fullmatch(r"\d+", employee_code):
        errors.append("Employee Code must contain numbers only.")

    if not employee_name:
        errors.append("Employee Name is mandatory.")
    elif not re.fullmatch(r"[A-Za-z ]+", employee_name):
        errors.append("Employee Name must contain alphabets and spaces only.")

    if not outlet_code:
        errors.append("Outlet Code is mandatory.")
    elif not re.fullmatch(r"\d+", outlet_code):
        errors.append("Outlet Code must contain numbers only.")

    if not outlet_name:
        errors.append("Outlet Name is mandatory.")
    elif not re.fullmatch(r"[A-Za-z0-9 ]+", outlet_name):
        errors.append("Outlet Name must contain alphabets, numbers and spaces only.")

    return errors


def sync_today_report(force=False):
    """Sync the current day to GitHub only when the 5-minute gate allows it.

    Google Sheets remains the live database. Employee actions write to Sheets immediately;
    GitHub receives a batched daily Excel snapshot at most once every 5 minutes while
    there is activity. Admin can force an immediate refresh.
    """
    if not report_sync_due(force=force):
        return None
    today_str = now_local().strftime("%Y-%m-%d")
    df = get_all_visits()
    if not df.empty:
        df["Date"] = df["Date"].astype(str)
        day_df = df[df["Date"] == today_str].copy()
    else:
        day_df = pd.DataFrame()
    excel_bytes = dataframe_to_excel_bytes(day_df, today_str)
    path = f"data/visits/Visits_{today_str}.xlsx"
    upload_or_update_report(path, excel_bytes, f"Sync daily report {today_str}")
    mark_report_synced()
    return path


with st.sidebar:
    st.title("Customer Care Day")
    menu = st.radio("Menu", ["Employee Visit", "Admin / Reports"])
    st.divider()
    st.caption("Live records are stored in Google Sheets. Daily Excel reports are archived in GitHub.")


if menu == "Employee Visit":
    show_brand_header(show_title=True)
    show_install_help()
    st.caption("Employee IN / OUT Attendance")

    if st.session_state["last_message"]:
        st.info(st.session_state["last_message"])

    st.markdown('<div class="ccd-section">Employee & Outlet Details</div>', unsafe_allow_html=True)
    with st.form("visit_details_form"):
        employee_code_input = st.text_input("Employee Code", value=st.session_state["employee_code"], max_chars=50)
        employee_name_input = st.text_input("Employee Name", value=st.session_state["employee_name"], max_chars=100)
        outlet_code_input = st.text_input("Outlet Code", value=st.session_state["outlet_code"], max_chars=50)
        outlet_name_input = st.text_input("Outlet Name", value=st.session_state["outlet_name"], max_chars=150)
        details_submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)

    if details_submitted:
        employee_code_input = employee_code_input.strip()
        employee_name_input = employee_name_input.strip()
        outlet_code_input = outlet_code_input.strip()
        outlet_name_input = outlet_name_input.strip()
        validation_errors = validate_details(
            employee_code_input, employee_name_input, outlet_code_input, outlet_name_input
        )
        if validation_errors:
            st.error("Please correct the following:")
            for _error in validation_errors:
                st.write(f"• {_error}")
        else:
            st.session_state["employee_code"] = employee_code_input
            st.session_state["employee_name"] = employee_name_input
            st.session_state["outlet_code"] = outlet_code_input
            st.session_state["outlet_name"] = outlet_name_input
            st.session_state["in_location"] = None
            st.session_state["out_location"] = None
            st.session_state["completed_visit"] = None
            st.session_state["last_message"] = "Details accepted. Checking today's attendance..."
            try:
                st.session_state["open_visit"] = find_open_visit(employee_code_input)
                st.session_state["details_loaded"] = True
                if st.session_state["open_visit"] is None:
                    st.session_state["scroll_target"] = "step1_in"
                else:
                    st.session_state["scroll_target"] = "step3_out"
            except Exception as exc:
                st.session_state["open_visit"] = None
                st.session_state["details_loaded"] = False
                st.error(f"Unable to check current attendance: {exc}")
            else:
                st.rerun()

    employee_code = st.session_state["employee_code"].strip()
    employee_name = st.session_state["employee_name"].strip()
    outlet_code = st.session_state["outlet_code"].strip()
    outlet_name = st.session_state["outlet_name"].strip()

    # Keep the completed visit visible across Streamlit reruns and scroll to the
    # final summary instead of restarting the employee workflow at Step 1.
    completed_visit = st.session_state.get("completed_visit")
    if completed_visit is not None:
        st.divider()
        st.markdown('<div id="visit_summary_anchor"></div>', unsafe_allow_html=True)
        auto_scroll_if_needed("visit_summary_anchor", 250)
        st.success("Visit completed. You can close the app.")
        st.markdown('<div class="ccd-summary"><div class="ccd-summary-head">✓ Visit Summary</div></div>', unsafe_allow_html=True)
        st.write(f"**Visit ID:** {completed_visit['Visit ID']}")
        st.write(f"**Employee:** {completed_visit['Employee Name']}")
        st.write(f"**Outlet:** {completed_visit['Outlet Name']} ({completed_visit['Outlet Code']})")
        st.write(f"**IN:** {completed_visit['IN Date/Time']}")
        st.write(f"**OUT:** {completed_visit['OUT Date/Time']}")
        st.write(f"**Time Spent:** {completed_visit['Time Spent']} ({completed_visit['Time Spent Hours']:.2f} hours)")
        st.write(f"**IN → OUT GPS Distance:** {completed_visit['IN-OUT GPS Distance (m)']:.1f} m")
        status = completed_visit["GPS Status"]
        if status == "Almost Same":
            st.success("✓ GPS Status: Almost Same")
        elif status == "Some Difference":
            st.warning("⚠ GPS Status: Some Difference")
        else:
            st.error("GPS Status: Big Difference")
        st.markdown('<div class="ccd-info"><strong>✓ Visit completed.</strong><br>You can close the app.</div>', unsafe_allow_html=True)
        st.stop()

    if not employee_code or not employee_name or not outlet_code or not outlet_name:
        st.info("Enter the employee and outlet details, then press Continue.")
        st.stop()

    # Do NOT query Google Sheets on every Streamlit rerun. The shared visit store
    # refreshes periodically and the selected employee's open visit is kept in session state.
    if not st.session_state.get("details_loaded"):
        try:
            st.session_state["open_visit"] = find_open_visit(employee_code)
            st.session_state["details_loaded"] = True
        except Exception as exc:
            st.error(f"Unable to check current attendance: {exc}")
            st.stop()

    open_visit = st.session_state.get("open_visit")

    st.divider()
    st.caption(f"Employee: {employee_name} | Outlet: {outlet_name} ({outlet_code})")

    if open_visit is None:
        show_progress(1)
        st.subheader("Step 1 — Capture GPS for IN")
        # After Continue, bring the employee directly to the IN GPS step.
        auto_scroll_if_needed("step1_in", 220)
        loc = get_location("gps_in", "IN")
        if loc:
            st.session_state["in_location"] = loc
            st.session_state["scroll_target"] = "step2_mark_in"

        if st.session_state["in_location"]:
            st.success("IN GPS is ready.")
            show_progress(2)
            st.subheader("Step 2 — Mark IN")
            # Once GPS has been captured, bring the Mark IN button into view.
            auto_scroll_if_needed("step2_mark_in", 220)
            if st.button("🟢 MARK IN", type="primary", use_container_width=True):
                ok, msg = location_ok(st.session_state["in_location"])
                if not ok:
                    st.error(msg)
                else:
                    try:
                        # A second Sheets read is intentionally avoided here. The shared
                        # store is updated atomically after the successful append.
                        if st.session_state.get("open_visit") is not None:
                            st.warning("This employee already has an open IN visit today.")
                        else:
                            visit_id = create_in_visit(employee_code, employee_name, outlet_code, outlet_name, st.session_state["in_location"])
                            st.session_state["open_visit"] = find_open_visit(employee_code)
                            st.session_state["in_location"] = None
                            st.session_state["scroll_target"] = "step3_out"
                            st.session_state["last_message"] = f"IN recorded successfully. Visit ID: {visit_id}"
                            try:
                                sync_today_report()
                            except Exception as sync_exc:
                                st.warning(f"IN was saved, but the GitHub Excel could not be synced yet: {sync_exc}")
                            st.success(f"✅ IN recorded. Visit ID: {visit_id}")
                            st.rerun()
                    except Exception as exc:
                        st.error("IN could not be recorded.")
                        st.exception(exc)
    else:
        st.success("🟢 This employee currently has an open visit.")
        st.write(f"**Visit ID:** {open_visit['Visit ID']}")
        st.write(f"**Employee:** {open_visit['Employee Name']}")
        st.write(f"**Outlet:** {open_visit['Outlet Name']}")
        st.write(f"**Outlet Code:** {open_visit['Outlet Code']}")
        st.write(f"**IN Time:** {open_visit['IN Date/Time']}")

        st.divider()
        show_progress(3)
        st.subheader("Step 3 — Capture GPS for OUT")
        # After a successful IN, automatically bring the employee to the OUT GPS step.
        auto_scroll_if_needed("step3_out", 220)
        loc = get_location("gps_out", "OUT")
        if loc:
            st.session_state["out_location"] = loc
            st.session_state["scroll_target"] = "step4_mark_out"

        if st.session_state["out_location"]:
            st.success("OUT GPS is ready.")
            show_progress(4)
            # Once OUT GPS is captured, bring the Mark OUT button into view.
            auto_scroll_if_needed("step4_mark_out", 220)
            if st.button("🔴 MARK OUT", type="primary", use_container_width=True):
                ok, msg = location_ok(st.session_state["out_location"])
                if not ok:
                    st.error(msg)
                else:
                    try:
                        if (employee_name.lower() != str(open_visit["Employee Name"]).strip().lower()
                                or outlet_code != str(open_visit["Outlet Code"]).strip()
                                or outlet_name.lower() != str(open_visit["Outlet Name"]).strip().lower()):
                            raise ValueError("Employee/Outlet details do not match the open IN visit. Please enter exactly the same details used for IN.")

                        result = complete_out_visit(open_visit["Visit ID"], st.session_state["out_location"], GPS_TOLERANCE_METERS, GPS_WARNING_METERS)
                        try:
                            sync_today_report()
                        except Exception as sync_exc:
                            st.warning(f"Visit was saved, but the GitHub daily Excel could not be synced yet: {sync_exc}")

                        st.success("✓ OUT recorded successfully.")
                        # Persist the result, then rerun so the final summary has a
                        # stable page position and automatic scrolling can target it.
                        st.session_state["completed_visit"] = result
                        st.session_state["out_location"] = None
                        st.session_state["in_location"] = None
                        st.session_state["open_visit"] = None
                        st.session_state["details_loaded"] = True
                        st.session_state["last_message"] = "Visit completed. You can close the app."
                        st.session_state["scroll_target"] = "visit_summary_anchor"
                        st.rerun()
                    except Exception as exc:
                        st.error("OUT could not be recorded.")
                        st.exception(exc)

else:
    show_brand_header(show_title=True)
    st.markdown('<div class="ccd-section">🔐 Admin / Reports</div>', unsafe_allow_html=True)
    if not st.session_state["admin_logged_in"]:
        password = st.text_input("Admin Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            if password == st.secrets["ADMIN_PASSWORD"]:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    if st.session_state["admin_logged_in"]:
        st.success("Admin access granted.")
        try:
            all_visits = get_all_visits()
            if all_visits.empty:
                st.info("No visits have been recorded yet.")
            else:
                all_visits["Date"] = all_visits["Date"].astype(str)
                all_visits["Status"] = all_visits["Status"].astype(str)
                st.metric("Total Records", len(all_visits))
                st.metric("Completed Visits", int((all_visits["Status"] == "Completed").sum()))
                st.metric("Pending IN", int((all_visits["Status"] == "IN").sum()))
        except Exception as exc:
            st.error(f"Could not read Google Sheet: {exc}")

        st.divider()
        st.subheader("Daily Excel Reports")
        try:
            reports = list_reports()
            if not reports:
                st.info("No Excel reports have been synced yet.")
            else:
                labels = [os.path.basename(x) for x in reports]
                selected_label = st.selectbox("Select report", labels)
                selected_path = reports[labels.index(selected_label)]
                if st.button("Refresh Selected Report from Google Sheet", use_container_width=True):
                    selected_date = selected_label.replace("Visits_", "").replace(".xlsx", "")
                    df = get_all_visits(force_refresh=True)
                    if not df.empty:
                        df["Date"] = df["Date"].astype(str)
                        day_df = df[df["Date"] == selected_date].copy()
                    else:
                        day_df = pd.DataFrame()
                    upload_or_update_report(selected_path, dataframe_to_excel_bytes(day_df, selected_date), f"Refresh report {selected_date}")
                    st.success("Report refreshed in GitHub.")
                    st.rerun()
                report_bytes = download_report(selected_path)
                st.download_button(
                    "⬇️ Download Excel",
                    data=report_bytes,
                    file_name=selected_label,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        except Exception as exc:
            st.error(f"Could not load GitHub reports: {exc}")


st.markdown('<div class="ccd-footer">WE CARE. YOU DRIVE. &nbsp;•&nbsp; Customer Care Day</div>', unsafe_allow_html=True)
