import io
import os
from datetime import datetime, date
import pandas as pd
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

from sheets_handler import (
    get_all_visits,
    find_open_visit,
    create_in_visit,
    complete_out_visit,
)
from report_manager import dataframe_to_excel_bytes
from github_reports import (
    report_exists,
    upload_or_update_report,
    list_reports,
    download_report,
)

# -----------------------------
# Configuration
# -----------------------------
APP_TITLE = "Petrol Station Visit & Attendance"
GPS_TOLERANCE_METERS = 100
GPS_WARNING_METERS = 200
MAX_ACCEPTABLE_GPS_ACCURACY_METERS = 1000

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⛽",
    layout="centered",
)

# -----------------------------
# Session state
# -----------------------------
for key, default in {
    "employee_code": "",
    "employee_name": "",
    "outlet_code": "",
    "outlet_name": "",
    "in_location": None,
    "out_location": None,
    "admin_logged_in": False,
    "last_message": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def now_local():
    # Streamlit Cloud runs in UTC. We store Pakistan local time explicitly.
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Karachi"))


def location_ok(location):
    if not location:
        return False, "Please capture your current GPS location."

    if location.get("error"):
        return False, f"GPS error: {location['error']}"

    lat = location.get("latitude")
    lon = location.get("longitude")
    accuracy = location.get("accuracy")

    if lat is None or lon is None:
        return False, "GPS coordinates were not received."

    if accuracy is not None and float(accuracy) > MAX_ACCEPTABLE_GPS_ACCURACY_METERS:
        return (
            False,
            f"GPS accuracy is too low ({float(accuracy):.0f} m). "
            f"Please move to an open area and try again.",
        )

    return True, ""


def get_location():
    st.markdown("### 📍 Current GPS Location")
    st.caption(
        "Turn ON Location/GPS and allow location permission. "
        "The browser will request your current location."
    )

    loc = streamlit_geolocation(
        key="gps_location_button"
    )

    if loc and loc.get("latitude") is not None:
        normalized = {
            "latitude": float(loc["latitude"]),
            "longitude": float(loc["longitude"]),
            "accuracy": (
                float(loc["accuracy"])
                if loc.get("accuracy") is not None
                else None
            ),
        }
        st.success("GPS location captured.")
        st.write(f"Latitude: `{normalized['latitude']:.6f}`")
        st.write(f"Longitude: `{normalized['longitude']:.6f}`")
        if normalized["accuracy"] is not None:
            st.write(
                f"Accuracy: approximately "
                f"`{normalized['accuracy']:.0f} metres`"
            )
        return normalized

    if loc and loc.get("error"):
        st.error(
            "Location could not be obtained. "
            "Please turn ON GPS/Location and allow permission."
        )

    return None


def sync_today_report():
    """Build today's Excel from Google Sheets and save it to the reports repo."""
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
    return path


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.title("⛽ Visit System")
    menu = st.radio(
        "Menu",
        ["Employee Visit", "Admin / Reports"],
    )
    st.divider()
    st.caption("Daily Excel reports are generated from the live Google Sheet.")

# -----------------------------
# Employee Visit
# -----------------------------
if menu == "Employee Visit":
    st.title("⛽ Petrol Station Visit")
    st.caption("Employee IN / OUT Attendance")

    if st.session_state.get("last_message"):
        st.info(st.session_state["last_message"])

    # Employee details
    st.subheader("Employee & Outlet Details")

    employee_code = st.text_input(
        "Employee Code",
        value=st.session_state["employee_code"],
        max_chars=50,
    ).strip()

    employee_name = st.text_input(
        "Employee Name",
        value=st.session_state["employee_name"],
        max_chars=100,
    ).strip()

    outlet_code = st.text_input(
        "Outlet Code",
        value=st.session_state["outlet_code"],
        max_chars=50,
    ).strip()

    outlet_name = st.text_input(
        "Outlet Name",
        value=st.session_state["outlet_name"],
        max_chars=150,
    ).strip()

    if employee_code:
        try:
            open_visit = find_open_visit(employee_code)
        except Exception as exc:
            open_visit = None
            st.error(f"Unable to check current attendance: {exc}")

    else:
        open_visit = None

    st.divider()

    if open_visit is None:
        st.subheader("Step 1 — Capture GPS for IN")

        if st.button("📍 Get Current GPS for IN", use_container_width=True):
            loc = get_location()
            if loc:
                st.session_state["in_location"] = loc
                st.rerun()

        if st.session_state["in_location"]:
            loc = st.session_state["in_location"]
            st.success("IN GPS is ready.")

            st.divider()
            st.subheader("Step 2 — Mark IN")

            if st.button(
                "🟢 MARK IN",
                type="primary",
                use_container_width=True,
            ):
                if not all(
                    [employee_code, employee_name, outlet_code, outlet_name]
                ):
                    st.error(
                        "Please enter Employee Code, Employee Name, "
                        "Outlet Code and Outlet Name."
                    )
                else:
                    ok, msg = location_ok(loc)
                    if not ok:
                        st.error(msg)
                    else:
                        try:
                            # Recheck immediately before writing.
                            existing = find_open_visit(employee_code)
                            if existing is not None:
                                st.warning(
                                    "This employee already has an open IN visit today."
                                )
                            else:
                                visit_id = create_in_visit(
                                    employee_code=employee_code,
                                    employee_name=employee_name,
                                    outlet_code=outlet_code,
                                    outlet_name=outlet_name,
                                    location=loc,
                                )
                                st.session_state["employee_code"] = employee_code
                                st.session_state["employee_name"] = employee_name
                                st.session_state["outlet_code"] = outlet_code
                                st.session_state["outlet_name"] = outlet_name
                                st.session_state["last_message"] = (
                                    f"IN recorded successfully. Visit ID: {visit_id}"
                                )
                                st.session_state["in_location"] = None

                                # Best effort: keep today's GitHub Excel in sync.
                                try:
                                    sync_today_report()
                                except Exception as sync_exc:
                                    st.warning(
                                        "IN was saved in Google Sheets, but the "
                                        f"GitHub Excel could not be synced yet: {sync_exc}"
                                    )

                                st.success(
                                    f"✅ IN recorded.\n\nVisit ID: {visit_id}"
                                )
                                st.rerun()
                        except Exception as exc:
                            st.error("IN could not be recorded.")
                            st.exception(exc)

    else:
        # Lock the employee/outlet fields to the active visit.
        st.success("🟢 This employee currently has an open visit.")

        st.write(f"**Visit ID:** {open_visit['Visit ID']}")
        st.write(f"**Employee:** {open_visit['Employee Name']}")
        st.write(f"**Outlet:** {open_visit['Outlet Name']}")
        st.write(f"**IN Time:** {open_visit['IN Date/Time']}")

        st.divider()
        st.subheader("Capture GPS for OUT")

        if st.button("📍 Get Current GPS for OUT", use_container_width=True):
            loc = get_location()
            if loc:
                st.session_state["out_location"] = loc
                st.rerun()

        if st.session_state["out_location"]:
            loc = st.session_state["out_location"]
            st.success("OUT GPS is ready.")

            if st.button(
                "🔴 MARK OUT",
                type="primary",
                use_container_width=True,
            ):
                ok, msg = location_ok(loc)
                if not ok:
                    st.error(msg)
                else:
                    try:
                        # Require the same employee and outlet details at OUT.
                        if (
                            employee_name.strip().lower()
                            != str(open_visit["Employee Name"]).strip().lower()
                            or outlet_code.strip()
                            != str(open_visit["Outlet Code"]).strip()
                            or outlet_name.strip().lower()
                            != str(open_visit["Outlet Name"]).strip().lower()
                        ):
                            raise ValueError(
                                "Employee/Outlet details do not match the open IN visit. "
                                "Please enter exactly the same details used for IN."
                            )

                        result = complete_out_visit(
                            visit_id=open_visit["Visit ID"],
                            location=loc,
                            tolerance_meters=GPS_TOLERANCE_METERS,
                            warning_meters=GPS_WARNING_METERS,
                        )

                        # Best effort: update GitHub daily report.
                        # The live record is already safely in Google Sheets.
                        try:
                            report_path = sync_today_report()
                            st.caption(f"Daily report synced: {report_path}")
                        except Exception as sync_exc:
                            st.warning(
                                "Visit was saved, but the GitHub daily Excel "
                                f"could not be synced yet: {sync_exc}"
                            )

                        st.success("✅ OUT recorded successfully.")
                        st.subheader("Visit Summary")
                        st.write(f"**Visit ID:** {result['Visit ID']}")
                        st.write(f"**IN:** {result['IN Date/Time']}")
                        st.write(f"**OUT:** {result['OUT Date/Time']}")
                        st.write(
                            f"**Time Spent:** {result['Time Spent']} "
                            f"({result['Time Spent Hours']:.2f} hours)"
                        )
                        st.write(
                            f"**IN → OUT GPS Distance:** "
                            f"{result['IN-OUT GPS Distance (m)']:.1f} m"
                        )

                        status = result["GPS Status"]
                        if status == "Almost Same":
                            st.success("✅ GPS Status: Almost Same")
                        elif status == "Some Difference":
                            st.warning("⚠️ GPS Status: Some Difference")
                        else:
                            st.error("🔴 GPS Status: Big Difference")

                        st.session_state["out_location"] = None
                        st.session_state["in_location"] = None
                        st.session_state["last_message"] = (
                            "Visit completed. You can close the app."
                        )

                    except Exception as exc:
                        st.error("OUT could not be recorded.")
                        st.exception(exc)

# -----------------------------
# Admin / Reports
# -----------------------------
else:
    st.title("🔐 Admin / Reports")

    if not st.session_state["admin_logged_in"]:
        password = st.text_input(
            "Admin Password",
            type="password",
        )
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
                st.metric(
                    "Completed Visits",
                    int((all_visits["Status"] == "Completed").sum()),
                )
                st.metric(
                    "Pending IN",
                    int((all_visits["Status"] == "IN").sum()),
                )

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

                if st.button(
                    "Refresh Selected Report from Google Sheet",
                    use_container_width=True,
                ):
                    # Rebuild selected date directly from the live sheet.
                    selected_date = selected_label.replace(
                        "Visits_", ""
                    ).replace(".xlsx", "")
                    df = get_all_visits()
                    if not df.empty:
                        df["Date"] = df["Date"].astype(str)
                        day_df = df[df["Date"] == selected_date].copy()
                    else:
                        day_df = pd.DataFrame()
                    bytes_out = dataframe_to_excel_bytes(
                        day_df, selected_date
                    )
                    upload_or_update_report(
                        selected_path,
                        bytes_out,
                        f"Refresh report {selected_date}",
                    )
                    st.success("Report refreshed in GitHub.")
                    st.rerun()

                report_bytes = download_report(selected_path)

                st.download_button(
                    "⬇️ Download Excel",
                    data=report_bytes,
                    file_name=selected_label,
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                )

        except Exception as exc:
            st.error(f"Could not load GitHub reports: {exc}")
